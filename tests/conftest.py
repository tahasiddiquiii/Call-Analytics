import json
from pathlib import Path

import pytest

from callanalytics.llm import ChatResult, ModelError

FIXTURES = Path(__file__).parent / "fixtures"
DATA = Path(__file__).resolve().parent.parent / "data" / "calls"


def classify(**overrides) -> dict:
    answer = {
        "call_type": "customer_service",
        "agent_name": "Aaron",
        "customer_name": "Carla Mendes",
        "summary": "The customer disputed a duplicate charge and the agent refunded it.",
        "intent": {"primary": "billing_dispute", "secondary": [], "detail": "Charged twice."},
        "customer_requested_escalation": False,
    }
    answer.update(overrides)
    return answer


def judge(**overrides) -> dict:
    answer = {
        "sentiment_start": "very_negative",
        "sentiment_end": "positive",
        "sentiment_overall": "neutral",
        "handed_over": False,
        "solution_agreed": True,
        "needs_future_step": False,
        "agent_overpromised": False,
        "customer_may_leave": False,
        "contacted_before": False,
        "outcome_detail": "Refund RF-22068 submitted.",
        "outcome_quote": "I'm submitting the refund now.",
    }
    answer.update(overrides)
    return answer


def actions(**overrides) -> dict:
    answer = {"action_items": [], "insights": []}
    answer.update(overrides)
    return answer


TASK_BY_SCHEMA = {"ClassifyOut": "classify", "JudgeOut": "judge", "ActionsOut": "actions"}


class FakeClient:
    """Stands in for Ollama. Answers per task; a list is a queue (last item repeats); an Exception is raised."""

    def __init__(self, classify=None, judge=None, actions=None):
        self.answers = {"classify": classify, "judge": judge, "actions": actions}
        self.calls = []

    def chat(self, messages, json_schema):
        task = TASK_BY_SCHEMA[json_schema["title"]]
        self.calls.append((task, messages))
        queue = self.answers[task]
        if queue is None:
            queue = {"classify": classify, "judge": judge, "actions": actions}[task]()
        item = queue.pop(0) if isinstance(queue, list) and len(queue) > 1 else (queue[0] if isinstance(queue, list) else queue)
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
