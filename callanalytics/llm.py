"""Minimal client for a local Ollama server. Talks to localhost only."""

from dataclasses import dataclass
from typing import List, Optional

import requests

from .config import Settings


class ModelError(Exception):
    """The model server failed or returned something unusable."""


class SetupError(Exception):
    """The model server is not running or the model is not downloaded."""


@dataclass
class ChatResult:
    content: str
    prompt_tokens: Optional[int]
    output_tokens: Optional[int]
    hit_length_limit: bool


class OllamaClient:
    def __init__(self, settings: Settings):
        settings.validate()
        self.s = settings
        self.base = settings.ollama_url.rstrip("/")

    def check_ready(self) -> str:
        """Fail early with a clear fix if Ollama is not running or the model is missing."""
        try:
            version = requests.get(f"{self.base}/api/version", timeout=5).json().get("version", "?")
            tags = requests.get(f"{self.base}/api/tags", timeout=5).json().get("models", [])
        except requests.RequestException:
            raise SetupError(f"Cannot reach Ollama at {self.base}. Start it with:  ollama serve")
        names = {m.get("name") for m in tags} | {m.get("model") for m in tags}
        wanted = self.s.model if ":" in self.s.model else f"{self.s.model}:latest"
        if wanted not in names:
            raise SetupError(f"Model '{self.s.model}' is not downloaded. Run:  ollama pull {self.s.model}")
        return f"ollama {version}"

    def chat(self, messages: List[dict], json_schema: dict) -> ChatResult:
        body = {
            "model": self.s.model,
            "messages": messages,
            "format": json_schema,  # constrained decoding: output must match this JSON Schema
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": self.s.temperature,
                "seed": self.s.seed,
                "num_ctx": self.s.num_ctx,
                "num_predict": self.s.num_predict,
                "num_gpu": self.s.num_gpu,
                **({"num_thread": self.s.num_thread} if self.s.num_thread else {}),
            },
        }
        try:
            resp = requests.post(f"{self.base}/api/chat", json=body, timeout=self.s.timeout_s)
        except requests.Timeout:
            raise ModelError(f"model did not answer within {self.s.timeout_s:.0f}s")
        except requests.RequestException as exc:
            raise ModelError(f"could not reach model server: {exc.__class__.__name__}")
        if resp.status_code != 200:
            raise ModelError(f"model server returned HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return ChatResult(
            content=data.get("message", {}).get("content", ""),
            prompt_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            hit_length_limit=data.get("done_reason") == "length",
        )
