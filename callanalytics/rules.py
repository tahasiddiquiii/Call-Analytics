"""Deterministic rules applied after the model: derived fields, consistency checks, priority.

These are done in code on purpose: a 3B model is good at reading, but not reliable at applying
multi-step rules (v2 showed it ignoring a 5-step outcome rule), and supervisors need the same
rule applied to every call.
"""

from typing import List

from .schema import SENTIMENT_SCALE, ActionsOut, ClassifyOut, Flags, JudgeOut

NON_CUSTOMER = {"test_call", "wrong_number", "abandoned"}


def outcome_status(call_type: str, j: JudgeOut) -> str:
    """The outcome rule, in order; the first match wins."""
    if call_type in NON_CUSTOMER:
        return "not_applicable"
    if j.handed_over:
        return "escalated"
    if not j.solution_agreed:
        return "unresolved"
    if j.needs_future_step:
        return "resolved_pending_action"
    return "resolved"


def trajectory(start: str, end: str) -> str:
    delta = SENTIMENT_SCALE.index(end) - SENTIMENT_SCALE.index(start)
    return "improved" if delta > 0 else "worsened" if delta < 0 else "stable"


def derive_flags(c: ClassifyOut, j: JudgeOut) -> Flags:
    """Flags come from direct yes/no answers: v3 showed the model labels insight categories unreliably."""
    if c.call_type in NON_CUSTOMER:
        return Flags(compliance_risk=False, churn_risk=False, repeat_contact=False, escalation_requested=False)
    return Flags(
        compliance_risk=j.agent_overpromised,
        churn_risk=j.customer_may_leave,
        repeat_contact=j.contacted_before,
        escalation_requested=c.customer_requested_escalation,
    )


_FLAG_OF_CATEGORY = {"compliance_risk": "compliance_risk", "churn_risk": "churn_risk", "repeat_contact": "repeat_contact"}


def drop_contradicted_insights(a: ActionsOut, flags: Flags) -> List[str]:
    """Remove insights whose category the yes/no answer contradicts. Returns the corrections made."""
    kept, corrections = [], []
    for ins in a.insights:
        flag = _FLAG_OF_CATEGORY.get(ins.category)
        if flag and not getattr(flags, flag):
            corrections.append(f"dropped {ins.category} insight: the yes/no answer says no")
        else:
            kept.append(ins)
    a.insights = kept
    return corrections


def normalise_due(due):
    """The model sometimes writes the text 'null' or 'none' instead of a JSON null."""
    if due is None or due.strip().lower() in ("", "null", "none", "n/a", "not specified", "unknown"):
        return None
    return due.strip()


def priority(call_type: str, status: str, sentiment_end: str, flags: Flags) -> str:
    """Which calls a supervisor should listen to first. Rules are fixed and documented in the README."""
    if call_type in NON_CUSTOMER:
        return "low"
    bad_end = sentiment_end in ("negative", "very_negative")
    open_case = status in ("unresolved", "escalated")
    if flags.compliance_risk or (open_case and bad_end):
        return "high"
    if flags.churn_risk or flags.repeat_contact or open_case or bad_end:
        return "medium"
    return "low"


def normalise_non_customer(c: ClassifyOut) -> List[str]:
    """Non-customer calls have a fixed intent by definition. Returns the corrections made."""
    if c.call_type in NON_CUSTOMER and c.intent.primary != "non_customer_call":
        old = c.intent.primary
        c.intent.primary, c.intent.secondary = "non_customer_call", []
        return [f"intent {old} -> non_customer_call because call_type is {c.call_type}"]
    return []


def consistency_problems(c: ClassifyOut, status: str, a: ActionsOut) -> List[str]:
    """Contradictions that code cannot fix safely. Each one becomes a review reason."""
    problems = []
    non_customer = c.call_type in NON_CUSTOMER
    if not non_customer and c.intent.primary == "non_customer_call":
        problems.append("customer call marked intent non_customer_call")
    if status in ("escalated", "resolved_pending_action") and not a.action_items:
        problems.append(f"outcome is {status} but there are no action items")
    if not c.summary.strip():
        problems.append("empty summary")
    return problems
