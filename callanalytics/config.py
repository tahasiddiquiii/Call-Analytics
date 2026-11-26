"""Run settings. Every value can be overridden by an environment variable or a CLI flag."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
SCHEMA_VERSION = "1.0"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class Settings:
    model: str = os.environ.get("CALLANALYTICS_MODEL", "qwen2.5:3b")
    ollama_url: str = os.environ.get("CALLANALYTICS_OLLAMA_URL", "http://localhost:11434")
    temperature: float = 0.0  # deterministic: same call in, same record out
    seed: int = 42
    num_ctx: int = 8192  # context window; longest provided call uses ~3.5k tokens with the prompt
    num_predict: int = 1800  # hard cap on output tokens so a runaway generation cannot hang a run
    num_gpu: int = 0  # 0 layers on GPU = CPU only (the brief requires CPU; Macs use the GPU by default)
    num_thread: int = 0  # 0 = let Ollama choose
    timeout_s: float = float(os.environ.get("CALLANALYTICS_TIMEOUT", "600"))
    max_attempts: int = 2  # first try + one repair try
    max_failure_ratio: float = 0.2  # exit code 1 if more than this share of calls fail

    def validate(self) -> None:
        """Refuse anything that is not a local model server (the brief forbids hosted models)."""
        host = urlparse(self.ollama_url).hostname
        if host not in _LOCAL_HOSTS:
            raise ValueError(
                f"Model server must run on this computer (localhost), got '{self.ollama_url}'."
            )
