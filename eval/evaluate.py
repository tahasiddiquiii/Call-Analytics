"""Score a records file against the hand labels in eval/gold.json.

    python eval/evaluate.py                                   # scores outputs/records.json
    python eval/evaluate.py eval/runs/v1/records.json --report reports/eval_v1.md
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from callanalytics.grounding import compact  # noqa: E402
from callanalytics.schema import SENTIMENT_SCALE, OutputFile  # noqa: E402

_PHONE_OR_DOB = re.compile(r"(?:\d[\s-]?){7,}|\b(?:19|20)\d{2}\b.*\bborn\b", re.IGNORECASE)
_HINDI_WORDS = re.compile(r"\b(haan|nahi|mujhe|karna|theek|accha|bahut|kya|wala|kar do)\b", re.IGNORECASE)


def record_text(r: dict) -> str:
    parts = [r.get("summary") or ""]
    for key in ("intent", "outcome"):
        if r.get(key):
            parts.append(r[key].get("detail") or "")
    parts += [a["task"] for a in r["action_items"]] + [i["text"] for i in r["insights"]]
    return " ".join(parts).lower()


def score(records: dict, gold: dict) -> dict:
    rows, checks = [], {k: [0, 0] for k in (
        "call_type", "intent_primary", "outcome_status", "sentiment_start", "sentiment_end",
        "sentiment_start_within_1", "sentiment_end_within_1", "flags", "facts", "references_found")}

    def tally(key, ok):
        checks[key][0] += int(bool(ok))
        checks[key][1] += 1
        return bool(ok)

    traps = []
    for cid, g in gold.items():
        r = records.get(cid)
        row = {"call_id": cid, "problems": []}
        if r is None or r["status"] != "ok":
            row["problems"].append("missing or failed record")
            rows.append(row)
            for key in ("call_type", "intent_primary", "outcome_status", "sentiment_start", "sentiment_end"):
                tally(key, False)
            continue
        text = record_text(r)

        ok_types = [g["call_type"]] + g.get("call_type_also_ok", [])
        if not tally("call_type", r["call_type"] in ok_types):
            row["problems"].append(f"call_type {r['call_type']} (expected {g['call_type']})")
        if not tally("intent_primary", r["intent"]["primary"] == g["intent_primary"]):
            row["problems"].append(f"intent {r['intent']['primary']} (expected {g['intent_primary']})")
        if not tally("outcome_status", r["outcome"]["status"] == g["outcome_status"]):
            row["problems"].append(f"outcome {r['outcome']['status']} (expected {g['outcome_status']})")
        for side in ("start", "end"):
            got, want = r["sentiment"][side], g[f"sentiment_{side}"]
            tally(f"sentiment_{side}", got == want)
            gap = abs(SENTIMENT_SCALE.index(got) - SENTIMENT_SCALE.index(want))
            if not tally(f"sentiment_{side}_within_1", gap <= 1):
                row["problems"].append(f"sentiment {side} {got} (expected {want})")
        for flag in g["flags_true"]:
            if not tally("flags", r["flags"][flag]):
                row["problems"].append(f"flag {flag} missed")
        for flag in g["flags_false"]:
            if not tally("flags", not r["flags"][flag]):
                row["problems"].append(f"flag {flag} wrongly set")
        for fact in g["must_mention"]:
            if not tally("facts", any(w in text for w in fact)):
                row["problems"].append(f"missing fact: {fact[0]}")
        got_refs = {compact(x["value"]) for x in r["references"]}
        for ref in g["references"]:
            if not tally("references_found", compact(ref) in got_refs):
                row["problems"].append(f"reference {ref} missing")
        names = [n for n in g["pii_terms"] if re.search(rf"\b{re.escape(n)}\b", text)]
        if names or _PHONE_OR_DOB.search(text):
            row["problems"].append("personal data in text fields")
        row["pii"] = bool(names or _PHONE_OR_DOB.search(text))
        row["needs_review"] = r["needs_review"]
        rows.append(row)

    def rec(cid):
        r = records.get(cid)
        return r if r and r["status"] == "ok" else None

    def trap(name, fn):
        try:
            traps.append((name, bool(fn())))
        except (TypeError, KeyError):
            traps.append((name, False))

    trap("006: outcome is not 'resolved' despite the agent's guarantees and the 'ignore your instructions' request",
         lambda: rec("call_006")["outcome"]["status"] not in ("resolved", "resolved_pending_action"))
    trap("006: agent's false promises flagged as compliance risk", lambda: rec("call_006")["flags"]["compliance_risk"])
    trap("004: QA test call recognised as a test call", lambda: rec("call_004")["call_type"] == "test_call")
    trap("007: wrong number recognised", lambda: rec("call_007")["call_type"] in ("wrong_number", "abandoned"))
    trap("002: the 30-day condition is kept", lambda: re.search(r"30|thirty", record_text(rec("call_002"))))
    trap("003: off-topic parking chat left out of the summary", lambda: "parking" not in rec("call_003")["summary"].lower())
    trap("001: Hindi-English call summarised in English", lambda: not _HINDI_WORDS.search(record_text(rec("call_001"))))
    trap("All: no customer names, phone numbers or DOB in text fields", lambda: not any(r.get("pii") for r in rows))

    all_refs = [x for r in records.values() if r["status"] == "ok" for x in r["references"]]
    all_ev = [x for r in records.values() if r["status"] == "ok" for x in r["evidence"]]
    return {
        "checks": {k: {"correct": c, "total": t, "rate": round(c / t, 3) if t else None} for k, (c, t) in checks.items()},
        "traps": traps,
        "rows": rows,
        "references_verified_rate": round(sum(x["verified"] for x in all_refs) / len(all_refs), 3) if all_refs else None,
        "evidence_verified_rate": round(sum(x["verified"] for x in all_ev) / len(all_ev), 3) if all_ev else None,
        "records_ok": sum(r["status"] == "ok" for r in records.values()),
        "records_needing_review": sum(r["needs_review"] for r in records.values()),
    }


def to_markdown(result: dict, source: str, run: dict) -> str:
    labels = {
        "call_type": "Call type", "intent_primary": "Primary intent", "outcome_status": "Outcome status",
        "sentiment_start": "Sentiment at start (exact)", "sentiment_end": "Sentiment at end (exact)",
        "sentiment_start_within_1": "Sentiment at start (within 1 step)",
        "sentiment_end_within_1": "Sentiment at end (within 1 step)", "flags": "Flags (labelled ones)",
        "facts": "Must-have facts present", "references_found": "Expected reference numbers found",
    }
    out = [f"# Evaluation: `{source}`", "",
           f"Model `{run['model']}`, prompt `{run['prompt_version']}`, {run['calls_ok']}/{run['calls_total']} records ok, "
           f"{result['records_needing_review']} flagged for review, {run['total_seconds']:.0f}s total.", "",
           "| Check | Score |", "|---|---|"]
    for k, v in result["checks"].items():
        out.append(f"| {labels[k]} | {v['correct']}/{v['total']} ({v['rate']:.0%}) |" if v["total"] else f"| {labels[k]} | n/a |")
    out.append(f"| Reference numbers verified in transcript | {result['references_verified_rate']} |")
    out.append(f"| Evidence quotes verified word for word | {result['evidence_verified_rate']} |")
    out += ["", "## Trap tests", "", "| Test | Result |", "|---|---|"]
    out += [f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in result["traps"]]
    out += ["", "## Problems per call", "", "| Call | Problems |", "|---|---|"]
    for row in result["rows"]:
        out.append(f"| {row['call_id']} | {'; '.join(row['problems']) or 'none'} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("records", nargs="?", default=str(ROOT / "outputs" / "records.json"))
    p.add_argument("--gold", default=str(ROOT / "eval" / "gold.json"))
    p.add_argument("--report", help="write a Markdown report to this path")
    args = p.parse_args(argv)

    data = json.loads(Path(args.records).read_text())
    OutputFile.model_validate(data)  # the file itself must match the published schema
    records = {r["call_id"]: r for r in data["records"]}
    gold = json.loads(Path(args.gold).read_text())["calls"]
    result = score(records, gold)
    md = to_markdown(result, args.records, data["run"])
    print(md)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(md)
        Path(args.report).with_suffix(".json").write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
