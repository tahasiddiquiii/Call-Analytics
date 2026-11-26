"""Data shapes.

`ModelOutput` is what the language model must return (its JSON Schema is sent to Ollama so the
model can only produce valid JSON in this shape). `CallRecord` is the final record written to
outputs/records.json: the model's answer plus fields that code computes and checks.
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


# ---------- What the model returns ----------


class IntentOut(_Strict):
    primary: Intent
    secondary: List[Intent]
    detail: str


class OutcomeOut(_Strict):
    status: OutcomeStatus
    detail: str


class SentimentOut(_Strict):
    start: Sentiment
    end: Sentiment
    overall: Sentiment


class ActionItem(_Strict):
    owner: Owner
    task: str
    due: Optional[str]


class Insight(_Strict):
    category: InsightCategory
    text: str
    quote: str  # words from the transcript that prove the insight; checked by code


class InsightRecord(Insight):
    verified: bool = Field(description="True if code found the quote word for word in the transcript")


class ReferenceOut(_Strict):
    type: ReferenceType
    value: str


class EvidenceOut(_Strict):
    supports: EvidenceSupports
    turn: int
    quote: str


class ModelOutput(_Strict):
    call_type: CallType
    summary: str
    intent: IntentOut
    outcome: OutcomeOut
    sentiment: SentimentOut
    action_items: List[ActionItem]
    insights: List[Insight]
    customer_requested_escalation: bool
    references: List[ReferenceOut]
    evidence: List[EvidenceOut]


# ---------- The final record ----------


class SentimentRecord(SentimentOut):
    trajectory: Literal["improved", "stable", "worsened"]


class Flags(_Strict):
    compliance_risk: bool
    churn_risk: bool
    repeat_contact: bool
    escalation_requested: bool


class Reference(ReferenceOut):
    verified: bool = Field(description="True if code found this ID in the transcript")


class Evidence(EvidenceOut):
    verified: bool = Field(description="True if code found this quote word for word in the transcript")


class Quality(_Strict):
    turns: int
    customer_turns: int
    unparsed_lines: int
    truncated: bool
    attempts: int
    processing_seconds: float
    prompt_tokens: Optional[int]
    output_tokens: Optional[int]


class CallRecord(_Strict):
    """One record per call file. Every key is always present; analysis fields are null when status='failed'."""

    call_id: str
    status: Literal["ok", "failed"]
    error: Optional[str]
    call_type: Optional[CallType]
    client_brand: Optional[str]
    summary: Optional[str]
    intent: Optional[IntentOut]
    outcome: Optional[OutcomeOut]
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


def model_output_json_schema() -> dict:
    return ModelOutput.model_json_schema()


if __name__ == "__main__":  # python -m callanalytics.schema  -> regenerates schema/record.schema.json
    import json
    from pathlib import Path

    target = Path(__file__).resolve().parent.parent / "schema" / "record.schema.json"
    target.write_text(json.dumps(OutputFile.model_json_schema(), indent=2) + "\n")
    print(f"wrote {target}")
