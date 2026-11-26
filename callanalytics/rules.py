"""Deterministic rules applied after the model: derived fields, consistency checks, priority.

These are done in code on purpose: a 3B model is good at reading, but not reliable at
bookkeeping, and supervisors need the same rule applied to every call.
"""

import re
from typing import List

from .schema import SENTIMENT_SCALE, Flags, ModelOutput

NON_CUSTOMER = {"test_call", "wrong_number", "abandoned"}
# 7+ digits in a row (phone / card numbers) should never appear in free text fields.
_LONG_NUMBER_RE = re.compile(r"(?:\d[\s-]?){7,}")


def trajectory(start: str, end: str) -> str:
    delta = SENTIMENT_SCALE.index(end) - SENTIMENT_SCALE.index(start)
    return "improved" if delta > 0 else "worsened" if delta < 0 else "stable"


def derive_flags(out: ModelOutput) -> Flags:
    cats = {i.category for i in out.insights}
    return Flags(
        compliance_risk="compliance_risk" in cats,
        churn_risk="churn_risk" in cats,
        repeat_contact="repeat_contact" in cats,
        escalation_requested=out.customer_requested_escalation,
    )


def priority(out: ModelOutput, flags: Flags) -> str:
    """Which calls a supervisor should listen to first. Rules are fixed and documented in the README."""
    if out.call_type in NON_CUSTOMER:
        return "low"
    bad_end = out.sentiment.end in ("negative", "very_negative")
    open_case = out.outcome.status in ("unresolved", "escalated")
    if flags.compliance_risk or (open_case and bad_end):
        return "high"
    if flags.churn_risk or flags.repeat_contact or open_case or bad_end:
        return "medium"
    return "low"


def consistency_problems(out: ModelOutput) -> List[str]:
    """Contradictions inside the model's answer. Each one is reported as a review reason."""
    problems = []
    non_customer = out.call_type in NON_CUSTOMER
    if non_customer and out.outcome.status != "not_applicable":
        problems.append(f"call_type is {out.call_type} but outcome is {out.outcome.status}")
    if non_customer and out.intent.primary != "non_customer_call":
        problems.append(f"call_type is {out.call_type} but intent is {out.intent.primary}")
    if not non_customer and out.outcome.status == "not_applicable":
        problems.append("customer call marked outcome not_applicable")
    if not non_customer and out.intent.primary == "non_customer_call":
        problems.append("customer call marked intent non_customer_call")
    if out.outcome.status in ("escalated", "resolved_pending_action") and not out.action_items:
        problems.append(f"outcome is {out.outcome.status} but there are no action items")
    if not out.summary.strip():
        problems.append("empty summary")
    if not non_customer and not any(e.supports == "outcome" for e in out.evidence):
        problems.append("no evidence quote given for the outcome")
    texts = [out.summary, out.outcome.detail, out.intent.detail]
    texts += [a.task for a in out.action_items] + [i.text for i in out.insights]
    if any(_LONG_NUMBER_RE.search(t) for t in texts):
        problems.append("free text may contain a phone or card number")
    return problems
