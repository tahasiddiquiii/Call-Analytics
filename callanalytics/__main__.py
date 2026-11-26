"""Command line entry point.

    python -m callanalytics data/calls                 # writes outputs/records.json
    python -m callanalytics data/calls -o out.json --model qwen2.5:3b
"""

import argparse
import json
import logging
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .config import REPO_ROOT, Settings
from .llm import OllamaClient, SetupError
from .pipeline import run

EXIT_OK, EXIT_TOO_MANY_FAILURES, EXIT_SETUP = 0, 1, 2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="callanalytics", description="Analyse a folder of call transcripts.")
    p.add_argument("input_dir", type=Path, help="folder containing call_*.txt transcript files")
    p.add_argument("-o", "--output", type=Path, default=Path("outputs/records.json"), help="output JSON file")
    p.add_argument("--model", help="Ollama model name (default qwen2.5:3b)")
    p.add_argument("--ollama-url", help="local Ollama server URL (default http://localhost:11434)")
    p.add_argument("--max-failure-ratio", type=float, help="exit 1 if more than this share of calls fail")
    p.add_argument("-q", "--quiet", action="store_true", help="only print warnings and errors")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    log = logging.getLogger("callanalytics")

    settings = Settings()
    overrides = {k: v for k, v in {"model": args.model, "ollama_url": args.ollama_url,
                                   "max_failure_ratio": args.max_failure_ratio}.items() if v is not None}
    settings = replace(settings, **overrides)

    if not args.input_dir.is_dir():
        log.error("Input folder not found: %s", args.input_dir)
        return EXIT_SETUP
    if not any(args.input_dir.glob("*.txt")):
        log.error("No .txt call files in %s", args.input_dir)
        return EXIT_SETUP
    try:
        client = OllamaClient(settings)
        runtime = client.check_ready()
    except (SetupError, ValueError) as exc:
        log.error("%s", exc)
        return EXIT_SETUP

    log.info("Model %s on CPU via %s", settings.model, runtime)
    result = run(args.input_dir, args.output, client, settings, runtime)
    info = result.run
    log.info("Wrote %s: %d ok, %d failed, %d need review, %.0fs total",
             args.output, info.calls_ok, info.calls_failed, info.calls_needing_review, info.total_seconds)
    _append_run_log(info.model_dump())

    if info.calls_total and info.calls_failed / info.calls_total > settings.max_failure_ratio:
        log.error("Too many failed calls (%d of %d)", info.calls_failed, info.calls_total)
        return EXIT_TOO_MANY_FAILURES
    return EXIT_OK


def _append_run_log(info: dict) -> None:
    """One line per run in reports/run_log.jsonl, for monitoring nightly runs. Never fails the run."""
    try:
        path = REPO_ROOT / "reports" / "run_log.jsonl"
        path.parent.mkdir(exist_ok=True)
        info = {"finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **info}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(info) + "\n")
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main())
