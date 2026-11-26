"""Measure run time and peak RAM of the model process while the system runs.

    python scripts/benchmark.py data/calls            # writes reports/benchmark.json

Peak RAM is sampled every 0.5 s from the Ollama model runner process (the process that holds the
model). It is the number that has to stay under the 4 GB limit.
"""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent


def runner_processes():
    procs = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or [])
            if "ollama" in (p.info["name"] or "").lower() or "ollama" in cmd:
                procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs


def main() -> int:
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "data/calls"
    out_json = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "outputs" / "records.json")
    peak = {"rss": 0, "proc": ""}
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            for p in runner_processes():
                try:
                    rss = p.memory_info().rss
                    if rss > peak["rss"]:
                        peak.update(rss=rss, proc=" ".join(p.cmdline()[:2]))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(0.5)

    t = threading.Thread(target=sample, daemon=True)
    t.start()
    started = time.monotonic()
    code = subprocess.call([sys.executable, "-m", "callanalytics", input_dir, "-o", out_json], cwd=ROOT)
    elapsed = time.monotonic() - started
    stop.set()
    t.join()

    run = json.loads(Path(out_json).read_text())["run"]
    per_call = [r["quality"]["processing_seconds"] for r in json.loads(Path(out_json).read_text())["records"]]
    report = {
        "machine": f"{psutil.cpu_count(logical=False)} physical cores, "
                   f"{psutil.virtual_memory().total / 2**30:.0f} GB RAM",
        "model": run["model"],
        "prompt_version": run["prompt_version"],
        "calls": run["calls_total"],
        "wall_seconds": round(elapsed, 1),
        "seconds_per_call_avg": round(sum(per_call) / len(per_call), 1) if per_call else None,
        "seconds_per_call_max": max(per_call) if per_call else None,
        "peak_model_process_ram_gb": round(peak["rss"] / 2**30, 2),
        "peak_process": peak["proc"],
        "exit_code": code,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
