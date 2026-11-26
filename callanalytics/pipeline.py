"""Orchestration: file -> parse -> 3 small model tasks -> validate -> check -> rules -> record -> JSON file.

Why three tasks: v2 showed that a 3B model given one long prompt with ten fields ignores many of
the rules. Each task now asks for a few fields only. The transcript sits in the system message,
which is identical for all three requests, so Ollama reuses its cached reading of the call.
"""

import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, ValidationError

from . import grounding, rules
from .config import PROMPTS_DIR, SCHEMA_VERSION, Settings
from .llm import ModelError
from .parser import Transcript, Turn, parse_file
from .privacy import redact
from .references import extract_references
from .schema import (
    ActionItem,
    ActionsOut,
    CallRecord,
    ClassifyOut,
    Evidence,
    InsightRecord,
    IntentOut,
    JudgeOut,
    OutcomeBasis,
    OutcomeRecord,
    OutputFile,
    Quality,
    Reference,
    RunInfo,
    SentimentRecord,
)

log = logging.getLogger("callanalytics")

_OUTPUT_TOKEN_RESERVE = 1800  # room kept free in the context window for the answer
_CHARS_PER_TOKEN = 3.2  # conservative estimate for English/Hinglish text
TASKS: List[Tuple[str, Type[BaseModel]]] = [
    ("classify", ClassifyOut),
    ("judge", JudgeOut),
    ("actions", ActionsOut),
]


@dataclass
class Prompts:
    system: str
    tasks: Dict[str, str]
    repair: str
    version: str

    @classmethod
    def load(cls, folder: Path = PROMPTS_DIR) -> "Prompts":
        read = lambda name: (folder / name).read_text(encoding="utf-8")  # noqa: E731
        system, repair = read("system.md"), read("repair.md")
        tasks = {name: read(f"task_{name}.md") for name, _ in TASKS}
        label = read("VERSION").strip()
        digest = hashlib.sha256("".join([system, repair, *tasks.values()]).encode()).hexdigest()[:8]
        # The hash makes the version honest: any prompt edit changes it, even if the label is not bumped.
        return cls(system, tasks, repair, f"{label}-{digest}")


@dataclass
class Usage:
    requests: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    errors: List[str] = field(default_factory=list)


class TaskFailed(Exception):
    pass


def _fit_to_context(t: Transcript, prompts: Prompts, settings: Settings) -> Tuple[List[Turn], bool]:
    """Keep the transcript inside the context window. Very long calls keep their start and end."""
    fixed = len(prompts.system) + max(len(p) for p in prompts.tasks.values())
    budget_chars = int((settings.num_ctx - _OUTPUT_TOKEN_RESERVE) * _CHARS_PER_TOKEN) - fixed
    if len(t.render()) <= budget_chars:
        return t.turns, False
    head, tail, used = [], [], 0
    turns = list(t.turns)
    while turns:  # alternate: take from the start, then from the end
        for side, pick in ((head, 0), (tail, -1)):
            if not turns:
                break
            size = len(turns[pick].text) + 20
            if used + size > budget_chars:
                turns = []
                break
            side.append(turns.pop(pick))
            used += size
    marker = Turn(index=0, speaker="System", text="[... middle of the call removed because it is too long ...]")
    return head + [marker] + list(reversed(tail)), True


def _validation_errors(exc: ValidationError) -> str:
    return "\n".join(f"- {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:8])


def _ask(client, system_msg: str, task_prompt: str, model_cls: Type[BaseModel], settings: Settings,
         usage: Usage, repair_prompt: str):
    """One task: ask, validate, repair once if needed. Raises TaskFailed."""
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": task_prompt}]
    schema = model_cls.model_json_schema()
    error = "no answer"
    for _ in range(settings.max_attempts):
        usage.requests += 1
        try:
            result = client.chat(messages, schema)
        except ModelError as exc:
            error = str(exc)
            continue
        usage.prompt_tokens += result.prompt_tokens or 0
        usage.output_tokens += result.output_tokens or 0
        if result.hit_length_limit:
            error, problems = "answer was cut off at the output length limit", "- the answer was too long; keep text short"
        else:
            try:
                return model_cls.model_validate_json(result.content)
            except ValidationError as exc:
                problems = _validation_errors(exc)
                error = "answer did not match the schema: " + problems.replace("\n", "; ")
        messages = messages[:2] + [
            {"role": "assistant", "content": result.content},
            {"role": "user", "content": repair_prompt.format(errors=problems)},
        ]
    raise TaskFailed(error)


def _empty_quality() -> Quality:
    return Quality(turns=0, customer_turns=0, unparsed_lines=0, truncated=False, model_requests=0,
                   processing_seconds=0.0, prompt_tokens=None, output_tokens=None, redactions=0, rule_corrections=[])


def _failed_record(call_id: str, error: str, quality: Quality, brand: Optional[str] = None) -> CallRecord:
    return CallRecord(
        call_id=call_id, status="failed", error=error, call_type=None, client_brand=brand, agent_name=None,
        summary=None, intent=None, outcome=None, sentiment=None, action_items=[], insights=[], flags=None,
        supervisor_priority=None, references=[], evidence=[], needs_review=True,
        review_reasons=[f"analysis failed: {error}"], quality=quality,
    )


def _customer_turns(t: Transcript, n: int = 2) -> Tuple[List[Turn], List[Turn]]:
    """The customer's first and last n turns (they may overlap in short calls)."""
    own = [x for x in t.turns if x.speaker == "Customer" and x.text.strip(" .")]
    return own[:n], own[-n:]


def analyse_call(path: Path, client, prompts: Prompts, settings: Settings) -> CallRecord:
    started = time.monotonic()
    try:
        t = parse_file(path)
    except OSError as exc:
        return _failed_record(path.stem, f"could not read file: {exc}", _empty_quality())

    usage = Usage()
    corrections: List[str] = []
    redactions = 0

    def quality(truncated: bool) -> Quality:
        return Quality(
            turns=len(t.turns), customer_turns=t.count("Customer"), unparsed_lines=t.unparsed_lines,
            truncated=truncated, model_requests=usage.requests,
            processing_seconds=round(time.monotonic() - started, 1),
            prompt_tokens=usage.prompt_tokens or None, output_tokens=usage.output_tokens or None,
            redactions=redactions, rule_corrections=corrections,
        )

    if not t.turns:
        return _failed_record(t.call_id, "file has no transcript lines", quality(False), t.brand)

    turns, truncated = _fit_to_context(t, prompts, settings)
    system_msg = prompts.system.format(brand=t.brand or "unknown", transcript=t.render(turns))
    first, last = _customer_turns(t)
    judge_prompt = prompts.tasks["judge"].format(
        first_turns="\n".join(f"[{x.index}] {x.text}" for x in first) or "(the customer said nothing)",
        last_turns="\n".join(f"[{x.index}] {x.text}" for x in last) or "(the customer said nothing)",
    )
    ask = lambda prompt, cls: _ask(client, system_msg, prompt, cls, settings, usage, prompts.repair)  # noqa: E731
    try:
        c: ClassifyOut = ask(prompts.tasks["classify"], ClassifyOut)
        corrections += rules.normalise_non_customer(c)
        j: JudgeOut = ask(judge_prompt, JudgeOut)
        non_customer = c.call_type in rules.NON_CUSTOMER
        a: ActionsOut = ActionsOut(action_items=[], insights=[]) if non_customer else ask(prompts.tasks["actions"], ActionsOut)
    except TaskFailed as exc:
        return _failed_record(t.call_id, str(exc), quality(truncated), t.brand)

    # --- everything below is code: checks, rules and privacy ---
    texts = [x.text for x in t.turns]
    name = c.customer_name

    def clean(s: str) -> str:
        nonlocal redactions
        s, n = redact(s.strip(), name)
        redactions += n
        return s

    reasons = list(t.warnings)
    if truncated:
        reasons.append("transcript was too long; the middle was not analysed")

    # sentiment evidence = the exact customer turns the model was shown; outcome evidence = the model's quote
    evidence = [Evidence(supports="sentiment", turn=x.index, quote=clean(x.text), verified=True)
                for x in (first[:1] + last[-1:])]
    turn = grounding.find_quote_turn(j.outcome_quote, t.turns)
    evidence.append(Evidence(supports="outcome", turn=turn, quote=clean(j.outcome_quote), verified=bool(turn)))
    if not turn:
        reasons.append("outcome evidence quote not found word for word")

    flags = rules.derive_flags(c, j)
    corrections += rules.drop_contradicted_insights(a, flags)
    insights = [InsightRecord(category=i.category, text=clean(i.text), quote=clean(i.quote),
                              verified=grounding.quote_in_transcript(i.quote, texts)) for i in a.insights]
    unproven = [i.category for i in insights if not i.verified]
    if unproven:
        reasons.append(f"insight quote not found word for word: {', '.join(unproven)}")

    status = rules.outcome_status(c.call_type, j)
    reasons += rules.consistency_problems(c, status, a)
    return CallRecord(
        call_id=t.call_id,
        status="ok",
        error=None,
        call_type=c.call_type,
        client_brand=t.brand,
        agent_name=c.agent_name,
        summary=clean(c.summary),
        intent=IntentOut(primary=c.intent.primary, secondary=c.intent.secondary, detail=clean(c.intent.detail)),
        outcome=OutcomeRecord(
            status=status, detail=clean(j.outcome_detail),
            basis=None if c.call_type in rules.NON_CUSTOMER else OutcomeBasis(
                handed_over=j.handed_over, solution_agreed=j.solution_agreed, needs_future_step=j.needs_future_step),
        ),
        sentiment=SentimentRecord(start=j.sentiment_start, end=j.sentiment_end, overall=j.sentiment_overall,
                                  trajectory=rules.trajectory(j.sentiment_start, j.sentiment_end)),
        action_items=[ActionItem(owner=x.owner, task=clean(x.task), due=rules.normalise_due(x.due))
                      for x in a.action_items],
        insights=insights,
        flags=flags,
        supervisor_priority=rules.priority(c.call_type, status, j.sentiment_end, flags),
        references=[Reference(type=k, value=v, verified=True) for k, v in extract_references(t.turns)],
        evidence=evidence,
        needs_review=bool(reasons),
        review_reasons=reasons,
        quality=quality(truncated),
    )


def write_atomic(path: Path, payload: dict) -> None:
    """Write to a temp file then rename, so a crash never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run(input_dir: Path, output_path: Path, client, settings: Settings, runtime: str,
        prompts: Optional[Prompts] = None) -> OutputFile:
    prompts = prompts or Prompts.load()
    files = sorted(p for p in input_dir.glob("*.txt") if p.is_file())
    started = time.monotonic()
    records = []
    for n, path in enumerate(files, 1):
        try:
            record = analyse_call(path, client, prompts, settings)
        except Exception as exc:  # last line of defence: one bad call must never stop the run
            log.exception("%s: unexpected error", path.stem)
            record = _failed_record(path.stem, f"unexpected error: {exc.__class__.__name__}: {exc}", _empty_quality())
        records.append(record)
        note = record.status if record.status == "failed" else ("needs review" if record.needs_review else "ok")
        log.info("[%d/%d] %s  %s  %.1fs", n, len(files), record.call_id, note, record.quality.processing_seconds)

    output = OutputFile(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        run=RunInfo(
            model=settings.model, runtime=runtime, device="cpu", prompt_version=prompts.version,
            input_dir=str(input_dir), calls_total=len(records),
            calls_ok=sum(r.status == "ok" for r in records),
            calls_failed=sum(r.status == "failed" for r in records),
            calls_needing_review=sum(r.needs_review for r in records),
            total_seconds=round(time.monotonic() - started, 1),
        ),
        records=records,
    )
    write_atomic(output_path, output.model_dump(mode="json"))
    return output
