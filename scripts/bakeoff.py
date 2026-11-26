"""Compare local models on the same pipeline, prompts and hand labels.

    python scripts/bakeoff.py qwen2.5:3b=eval/runs/v4 llama3.2:3b qwen2.5:1.5b

A model given as name=folder reuses an existing run in that folder; otherwise it is run now into
eval/bakeoff/<name>/. Writes reports/bakeoff.json (read by the slide builder). `loaded_gb` (model +
8k context as reported by `ollama ps` while loaded: 2.7 / 3.5 / 1.5 GB) was added by hand after the run.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(args) -> int:
    rows = []
    for arg in args:
        model, _, folder = arg.partition("=")
        out_dir = ROOT / (folder or f"eval/bakeoff/{model.replace(':', '_')}")
        records = out_dir / "records.json"
        if not folder:
            out_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "callanalytics", "data/calls", "-o", str(records),
                            "--model", model, "-q"], cwd=ROOT, check=False)
        subprocess.run([sys.executable, "eval/evaluate.py", str(records), "--report", str(out_dir / "eval.md")],
                       cwd=ROOT, check=True, capture_output=True)
        ev = json.loads((out_dir / "eval.json").read_text())
        run = json.loads(records.read_text())["run"]
        c = ev["checks"]
        rows.append({
            "model": model,
            "outcome": f"{c['outcome_status']['correct']}/{c['outcome_status']['total']}",
            "intent": f"{c['intent_primary']['correct']}/{c['intent_primary']['total']}",
            "facts": f"{c['facts']['correct']}/{c['facts']['total']}",
            "traps": f"{sum(ok for _, ok in ev['traps'])}/{len(ev['traps'])}",
            "failed": run["calls_failed"],
            "minutes": round(run["total_seconds"] / 60, 1),
        })
        print(rows[-1])
    (ROOT / "reports" / "bakeoff.json").write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
