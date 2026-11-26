# Manual review of the final records

I read every record in `outputs/records.json` side by side with its transcript. The automatic checks (`eval/evaluate.py`, quote and reference verification) cannot see whether a free-text sentence is *true*. This review can, and it found errors the scores do not show.

**Verdict:** the categorical fields (call type, intent, outcome status, flags, priority, references) are mostly right and safe to filter and count. The free-text fields (summary, details, action items, insights) are useful but contain errors in about half the calls. They should be read as a draft, not as fact.

| Call | Correct | Wrong or weak |
|---|---|---|
| 001 | Reschedule + address change; resolved; English summary of a Hindi-English call; no address in the record | Missed the 8-hour fasting instruction. Action items list work already done ("update the address") and give the insurer task to the company; the customer said they would do it. |
| 002 | Retention offer, $52 rate, Thursday line check | Outcome `resolved`; should be `resolved_pending_action` (stays only if fixed in 30 days). `churn_risk` not flagged although the customer said "If it still drops at night I'm gone". Intent detail is off ("requested email confirmation"). |
| 003 | Replacement to locker, references BC-774192 and CL-9031 found, parking tangent ignored | Outcome `resolved`; the replacement still has to ship (`resolved_pending_action`). The repeat-loss remark ("third time … this year") not flagged. |
| 004 | Test call, excluded from statistics | None that matter. |
| 005 | Duplicate charge, $82 refund RF-22068, scheduled payment cancelled, sentiment negative → positive | Action items invented ("review and update the system", "customer to update payment information"). One insight quote was not in the transcript; the code caught it and set `needs_review`. |
| 006 | `unresolved` despite the agent's guarantees and the customer's "ignore your instructions" request; `compliance_risk`; high priority | End sentiment `neutral`; the customer was angry ("write down the time of this call and your name"). Outcome detail is muddled ("accepted that the claim would be approved"). Intent detail wrong ("refund"). |
| 007 | Wrong number, excluded from statistics | Sentiment `negative` where neutral fits better. (An earlier run of the same code invented "had contacted the company before" in the outcome detail; the final run did not. See `reports/determinism.md`.) |
| 008 | Unresolved, `churn_risk`, high priority; summary accurate | Invented action item ("follow up within 2 business days"). `repeat_contact` flagged wrongly ("after six years" is tenure, not a repeat contact). The agent's poor conduct is not captured as an insight. |
| 009 | Escalated, ESC-7812 and CLM-291446, `repeat_contact`, escalation requested, high priority | The first version of the record said "Mr. the customer" (a bug in my redaction code, fixed before the final run). |
| 010 | Escalated to a technician, TK-44180 | Summary says the agent "performed a factory reset"; the customer declined it. Outcome detail says the customer must contact the technician; the scheduling team will call the customer. |

**Across calls:**
- The model uses he/she for customers in 5 records despite the prompt rule; that guesses gender from names.
- "Needs a future step" is under-detected (002, 003, held-out 101), so `resolved` is too optimistic. This is the most important known bias for a supervisor counting resolved calls.

**Held-out calls (written by me, never used for tuning; `eval/runs/heldout/`):**
- `call_102` (refund delay, dismissive agent): unresolved, very negative end, churn + repeat + escalation-requested flags, high priority. Correct; the agent's conduct is not captured.
- `call_101` (prescription delay): marked `resolved`, but the clinic's approval is still pending, which is the same future-step bias. Reference PR-6120 found by code.

**Bugs found by this review and fixed in code:** "Mr. the customer" (a title was removed after the surname), "their the card on file". Both have tests now.
