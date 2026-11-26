"""Data shapes.

`ClassifyOut`, `JudgeOut` and `ActionsOut` are what the language model must return for its three
small tasks (each JSON Schema is sent to Ollama, so the model can only produce valid JSON in that
shape). `CallRecord` is the final record written to outputs/records.json: the model's answers plus
fields that code computes and checks.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CallType = Literal["customer_service", "test_call", "wrong_number", "abandoned"]
Intent = Literal[
    "appointment_change",
    "account_update",
    "cancellation_request",
    "billing_dispute",
    "refund_request",
    "order_issue",
    "claim_appeal",
    "claim_status",
    "plan_change_inquiry",
    "technical_support",
    "general_inquiry",
    "non_customer_call",
    "other",
]
OutcomeStatus = Literal["resolved", "resolved_pending_action", "escalated", "unresolved", "not_applicable"]
Sentiment = Literal["very_negative", "negative", "neutral", "positive", "very_positive"]
SENTIMENT_SCALE = ["very_negative", "negative", "neutral", "positive", "very_positive"]
Owner = Literal["agent", "company", "customer", "supervisor"]
InsightCategory = Literal[
    "agent_conduct",
    "compliance_risk",
    "process_gap",
    "product_feedback",
    "churn_risk",
    "repeat_contact",
    "data_quality",
]
ReferenceType = Literal["order", "claim", "ticket", "refund", "escalation", "policy", "other"]
EvidenceSupports = Literal["intent", "outcome", "sentiment", "insight"]
Priority = Literal["high", "medium", "low"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- What the model returns (three small tasks per call) ----------


class IntentOut(_Strict):
    primary: Intent
    secondary: List[Intent]
    detail: str


class ClassifyOut(_Strict):
    """Task 1: what kind of call, and what the customer wanted."""

    call_type: CallType
    agent_name: Optional[str]
    customer_name: Optional[str]  # used only so code can remove it from the record; never stored
    summary: str
    intent: IntentOut
    customer_requested_escalation: bool


class OutcomeBasis(_Strict):
    """Simple yes/no facts. Code turns them into outcome.status with a fixed rule (rules.outcome_status)."""

    handed_over: bool
    solution_agreed: bool
    needs_future_step: bool


class JudgeOut(_Strict):
    """Task 2: sentiment, outcome facts and flag facts, all as simple labels or yes/no answers.

    Code shows the model the customer's first and last turns, so it rates the actual words.
    """

    sentiment_start: Sentiment
    sentiment_end: Sentiment
    sentiment_overall: Sentiment
    handed_over: bool
    solution_agreed: bool
    needs_future_step: bool
    agent_overpromised: bool
    customer_may_leave: bool
    contacted_before: bool
    outcome_detail: str
    outcome_quote: str


class ActionItem(_Strict):
    owner: Owner
    task: str
    due: Optional[str]


class Insight(_Strict):
    category: InsightCategory
    text: str
    quote: str  # words from the transcript that prove the insight; checked by code


class ActionsOut(_Strict):
    """Task 3: follow-up work and supervisor insights."""

    action_items: List[ActionItem]
    insights: List[Insight]


# ---------- The final record ----------


class OutcomeRecord(_Strict):
    status: OutcomeStatus
    detail: str
    basis: Optional[OutcomeBasis]  # the model's yes/no answers behind the status (null for non-customer calls)


class SentimentRecord(_Strict):
    start: Sentiment
    end: Sentiment
    overall: Sentiment
    trajectory: Literal["improved", "stable", "worsened"]


class InsightRecord(Insight):
    verified: bool = Field(description="True if code found the quote word for word in the transcript")


class Flags(_Strict):
    """From the model's yes/no answers (judge task); always false for non-customer calls."""

    compliance_risk: bool
    churn_risk: bool
    repeat_contact: bool
    escalation_requested: bool


class Reference(_Strict):
    type: ReferenceType
    value: str
    verified: bool = Field(description="True if found in the transcript (always true: extracted by code)")


class Evidence(_Strict):
    supports: EvidenceSupports
    turn: int
    quote: str
    verified: bool = Field(description="True if code found this quote word for word in the transcript")


class Quality(_Strict):
    turns: int
    customer_turns: int
    unparsed_lines: int
    truncated: bool
    model_requests: int
    processing_seconds: float
    prompt_tokens: Optional[int]
    output_tokens: Optional[int]
    redactions: int
    rule_corrections: List[str]


class CallRecord(_Strict):
    """One record per call file. Every key is always present; analysis fields are null when status='failed'."""

    call_id: str
    status: Literal["ok", "failed"]
    error: Optional[str]
    call_type: Optional[CallType]
    client_brand: Optional[str]
    agent_name: Optional[str]
    summary: Optional[str]
    intent: Optional[IntentOut]
    outcome: Optional[OutcomeRecord]
    sentiment: Optional[SentimentRecord]
    action_items: List[ActionItem]
    insights: List[InsightRecord]
    flags: Optional[Flags]
    supervisor_priority: Optional[Priority]
    references: List[Reference]
    evidence: List[Evidence]
    needs_review: bool
    review_reasons: List[str]
    quality: Quality


class RunInfo(_Strict):
    model: str
    runtime: str
    device: Literal["cpu"]
    prompt_version: str
    input_dir: str
    calls_total: int
    calls_ok: int
    calls_failed: int
    calls_needing_review: int
    total_seconds: float


class OutputFile(_Strict):
    schema_version: str
    generated_at: str
    run: RunInfo
    records: List[CallRecord]


if __name__ == "__main__":  # python -m callanalytics.schema  -> regenerates schema/record.schema.json
    import json
    from pathlib import Path

    target = Path(__file__).resolve().parent.parent / "schema" / "record.schema.json"
    target.write_text(json.dumps(OutputFile.model_json_schema(), indent=2) + "\n")
    print(f"wrote {target}")
