"""Supervisor view: filter, count and compare records, as the brief says supervisors will.

    python scripts/summarise.py                      # reads outputs/records.json, writes reports/summary.md

Shows that the records work for their intended use: everything here is computed from the JSON
fields alone, with no reading of transcripts.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs" / "records.json"
    recs = [r for r in json.loads(src.read_text())["records"] if r["status"] == "ok"]
    customer = [r for r in recs if r["call_type"] == "customer_service"]
    out = [f"# Supervisor summary of `{src.name}`", "",
           f"{len(recs)} analysed calls, {len(customer)} real customer calls "
           f"({len(recs) - len(customer)} excluded: "
           + ", ".join(f"{r['call_id']} {r['call_type']}" for r in recs if r not in customer) + ")", ""]

    def table(title, counter, ids):
        out.extend([f"## {title}", "", "| Value | Calls | Call IDs |", "|---|---|---|"])
        for value, n in counter.most_common():
            out.append(f"| {value} | {n} | {', '.join(sorted(ids[value]))} |")
        out.append("")

    for title, key in (("Outcome", lambda r: r["outcome"]["status"]),
                       ("Priority for supervisor review", lambda r: r["supervisor_priority"]),
                       ("Customer sentiment at end of call", lambda r: r["sentiment"]["end"]),
                       ("Sentiment change during call", lambda r: r["sentiment"]["trajectory"]),
                       ("Client brand", lambda r: r["client_brand"] or "unknown")):
        counter, ids = Counter(), defaultdict(list)
        for r in customer:
            counter[key(r)] += 1
            ids[key(r)].append(r["call_id"])
        table(title, counter, ids)

    counter, ids = Counter(), defaultdict(list)
    for r in customer:
        for flag, on in r["flags"].items():
            if on:
                counter[flag] += 1
                ids[flag].append(r["call_id"])
    table("Flags", counter, ids)

    out += ["## High-priority calls", "", "| Call | Brand | Agent | Outcome | Why |", "|---|---|---|---|---|"]
    for r in customer:
        if r["supervisor_priority"] == "high":
            why = "; ".join(i["text"] for i in r["insights"] if i["category"] in ("compliance_risk", "agent_conduct"))
            out.append(f"| {r['call_id']} | {r['client_brand']} | {r['agent_name'] or '-'} | "
                       f"{r['outcome']['status']} | {why or r['outcome']['detail']} |")
    out.append("")
    open_actions = [(r["call_id"], a) for r in customer for a in r["action_items"] if a["owner"] in ("company", "supervisor")]
    out += ["## Open follow-ups owned by the company or a supervisor", "", "| Call | Owner | Task | Due |", "|---|---|---|---|"]
    out += [f"| {cid} | {a['owner']} | {a['task']} | {a['due'] or '-'} |" for cid, a in open_actions]

    text = "\n".join(out) + "\n"
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "summary.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
