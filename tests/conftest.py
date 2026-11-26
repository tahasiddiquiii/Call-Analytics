import json
from pathlib import Path

import pytest

from callanalytics.llm import ChatResult, ModelError

FIXTURES = Path(__file__).parent / "fixtures"
DATA = Path(__file__).resolve().parent.parent / "data" / "calls"


def valid_answer(**overrides) -> dict:
    answer = {
        "call_type": "customer_service",
        "summary": "The customer disputed a bill and the agent refunded it.",
        "intent": {"primary": "billing_dispute", "secondary": [], "detail": "Bill too high."},
        "outcome": {"status": "resolved", "detail": "Refund RF-22068 submitted."},
        "sentiment": {"start": "negative", "end": "positive", "overall": "neutral"},
        "action_items": [],
        "insights": [],
        "customer_requested_escalation": False,
        "references": [{"type": "refund", "value": "RF-22068"}],
        "evidence": [{"supports": "outcome", "turn": 2, "quote": "Let me check."}],
    }
    answer.update(overrides)
    return answer


class FakeClient:
    """Returns queued answers instead of calling a model. A queued Exception is raised."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def chat(self, messages, json_schema):
        self.calls.append(messages)
        item = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(item, Exception):
            raise item
        content = item if isinstance(item, str) else json.dumps(item)
        return ChatResult(content=content, prompt_tokens=100, output_tokens=50, hit_length_limit=False)


@pytest.fixture
def fake():
    return FakeClient


@pytest.fixture
def model_error():
    return ModelError("model did not answer within 600s")
