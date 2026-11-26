"""Orchestration: file -> parse -> model -> validate -> ground -> rules -> record -> JSON file."""

import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import ValidationError

from . import grounding, rules
from .config import PROMPTS_DIR, SCHEMA_VERSION, Settings
from .llm import ChatResult, ModelError
from .parser import Transcript, Turn, parse_file
from .schema import (
    CallRecord,
    Evidence,
    InsightRecord,
    ModelOutput,
    OutputFile,
    Quality,
    Reference,
    RunInfo,
    SentimentRecord,
    model_output_json_schema,
)

log = logging.getLogger("callanalytics")

_OUTPUT_TOKEN_RESERVE = 1800  # room kept free in the context window for the answer
_CHARS_PER_TOKEN = 3.2  # conservative estimate for English/Hinglish text


@dataclass
class Prompts:
    system: str
    user_template: str
    repair: str
    version: str

    @classmethod
    def load(cls, folder: Path = PROMPTS_DIR) -> "Prompts":
        system = (folder / "system.md").read_text(encoding="utf-8")
        user = (folder / "user_template.md").read_text(encoding="utf-8")
        repair = (folder / "repair.md").read_text(encoding="utf-8")
        label = (folder / "VERSION").read_text(encoding="utf-8").strip()
        digest = hashlib.sha256((system + user + repair).encode()).hexdigest()[:8]
        # The hash makes the version honest: any prompt edit changes it, even if the label is not bumped.
        return cls(system, user, repair, f"{label}-{digest}")


def _fit_to_context(t: Transcript, prompts: Prompts, settings: Settings) -> Tuple[List[Turn], bool]:
    """Keep the transcript inside the context window. Very long calls keep their start and end."""
    budget_chars = int((settings.num_ctx - _OUTPUT_TOKEN_RESERVE) * _CHARS_PER_TOKEN) - len(prompts.system)
    if len(t.render()) <= budget_chars:
        return t.turns, False
    head, tail, used = [], [], 0
    turns = list(t.turns)
    while turns:  # alternate: take from the start, then from the end
        for side, pick in ((head, 0), (tail, -1)):
            if not turns:
                break
            turn = turns[pick]
            size = len(turn.text) + 20
            if used + size > budget_chars:
                turns = []
                break
            side.append(turns.pop(pick))
            used += size
    marker = Turn(index=0, speaker="System", text="[... middle of the call removed because it is too long ...]")
    return head + [marker] + list(reversed(tail)), True


def _validation_errors(exc: ValidationError) -> str:
    lines = []
    for e in exc.errors()[:8]:
        where = ".".join(str(p) for p in e["loc"])
        lines.append(f"- {where}: {e['msg']}")
    return "\n".join(lines)


def _ask_model(client, prompts: Prompts, t: Transcript, turns: List[Turn], settings: Settings):
    """Ask the model, validate, and repair once if needed. Returns (output, attempts, last ChatResult, error)."""
    user = prompts.user_template.format(call_id=t.call_id, brand=t.brand or "unknown", transcript=t.render(turns))
    messages = [{"role": "system", "content": prompts.system}, {"role": "user", "content": user}]
    schema = model_output_json_schema()
    error: Optional[str] = None
    result: Optional[ChatResult] = None
    for attempt in range(1, settings.max_attempts + 1):
        try:
            result = client.chat(messages, schema)
        except ModelError as exc:
            error = str(exc)
            log.warning("%s attempt %d: %s", t.call_id, attempt, error)
            continue
        if result.hit_length_limit:
            error = "answer was cut off at the output length limit"
            problems = "- the answer was too long and got cut off; keep every text field short"
        else:
            try:
                return ModelOutput.model_validate_json(result.content), attempt, result, None
            except ValidationError as exc:
                problems = _validation_errors(exc)
                error = "model answer did not match the schema: " + problems.replace("\n", "; ")
        log.warning("%s attempt %d invalid, asking for a repair", t.call_id, attempt)
        messages = messages[:2] + [
            {"role": "assistant", "content": result.content},
            {"role": "user", "content": prompts.repair.format(errors=problems)},
        ]
    return None, settings.max_attempts, result, error


def _failed_record(call_id: str, error: str, quality: Quality, brand: Optional[str] = None) -> CallRecord:
    return CallRecord(
        call_id=call_id, status="failed", error=error, call_type=None, client_brand=brand, summary=None,
        intent=None, outcome=None, sentiment=None, action_items=[], insights=[], flags=None,
        supervisor_priority=None, references=[], evidence=[], needs_review=True,
        review_reasons=[f"analysis failed: {error}"], quality=quality,
    )


def analyse_call(path: Path, client, prompts: Prompts, settings: Settings) -> CallRecord:
    started = time.monotonic()
    empty_quality = Quality(turns=0, customer_turns=0, unparsed_lines=0, truncated=False, attempts=0,
                            processing_seconds=0.0, prompt_tokens=None, output_tokens=None)
    try:
        t = parse_file(path)
    except OSError as exc:
        return _failed_record(path.stem, f"could not read file: {exc}", empty_quality)

    def quality(attempts: int, truncated: bool, result: Optional[ChatResult]) -> Quality:
        return Quality(
            turns=len(t.turns), customer_turns=t.count("Customer"), unparsed_lines=t.unparsed_lines,
            truncated=truncated, attempts=attempts, processing_seconds=round(time.monotonic() - started, 1),
            prompt_tokens=result.prompt_tokens if result else None,
            output_tokens=result.output_tokens if result else None,
        )

    if not t.turns:
        return _failed_record(t.call_id, "file has no transcript lines", quality(0, False, None), t.brand)

    turns, truncated = _fit_to_context(t, prompts, settings)
    out, attempts, result, error = _ask_model(client, prompts, t, turns, settings)
    if out is None:
        return _failed_record(t.call_id, error or "unknown error", quality(attempts, truncated, result), t.brand)

    # --- checks done by code, not by the model ---
    reasons = list(t.warnings)
    if truncated:
        reasons.append("transcript was too long; the middle was not analysed")
    texts = [x.text for x in t.turns]
    references, seen = [], set()
    for ref in out.references:
        value = grounding.canonical_reference(ref.value)
        if value in seen:
            continue
        seen.add(value)
        ok = grounding.reference_in_transcript(ref.value, texts)
        references.append(Reference(type=ref.type, value=value, verified=ok))
        if not ok:
            reasons.append(f"reference '{ref.value}' not found in transcript")
    insights = []
    for ins in out.insights:
        insights.append(InsightRecord(**ins.model_dump(), verified=grounding.quote_in_transcript(ins.quote, texts)))
    unproven = [i.category for i in insights if not i.verified]
    if unproven:
        reasons.append(f"insight quote not found word for word: {', '.join(unproven)}")
    evidence = []
    for ev in out.evidence:
        turn = grounding.find_quote_turn(ev.quote, t.turns)
        evidence.append(Evidence(supports=ev.supports, turn=turn or ev.turn, quote=ev.quote, verified=bool(turn)))
    unverified = sum(1 for e in evidence if not e.verified)
    if unverified:
        reasons.append(f"{unverified} of {len(evidence)} evidence quote(s) not found word for word")
    reasons += rules.consistency_problems(out)

    flags = rules.derive_flags(out)
    return CallRecord(
        call_id=t.call_id,
        status="ok",
        error=None,
        call_type=out.call_type,
        client_brand=t.brand,
        summary=out.summary.strip(),
        intent=out.intent,
        outcome=out.outcome,
        sentiment=SentimentRecord(**out.sentiment.model_dump(),
                                  trajectory=rules.trajectory(out.sentiment.start, out.sentiment.end)),
        action_items=out.action_items,
        insights=insights,
        flags=flags,
        supervisor_priority=rules.priority(out, flags),
        references=references,
        evidence=evidence,
        needs_review=bool(reasons),
        review_reasons=reasons,
        quality=quality(attempts, truncated, result),
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
            q = Quality(turns=0, customer_turns=0, unparsed_lines=0, truncated=False, attempts=0,
                        processing_seconds=0.0, prompt_tokens=None, output_tokens=None)
            record = _failed_record(path.stem, f"unexpected error: {exc.__class__.__name__}: {exc}", q)
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
