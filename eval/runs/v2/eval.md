# Evaluation: `eval/runs/v2/records.json`

Model `qwen2.5:3b`, prompt `v2-93ef0ddf`, 10/10 records ok, 4 flagged for review, 1012s total.

| Check | Score |
|---|---|
| Call type | 10/10 (100%) |
| Primary intent | 8/10 (80%) |
| Outcome status | 3/10 (30%) |
| Sentiment at start (exact) | 5/10 (50%) |
| Sentiment at end (exact) | 7/10 (70%) |
| Sentiment at start (within 1 step) | 8/10 (80%) |
| Sentiment at end (within 1 step) | 10/10 (100%) |
| Flags (labelled ones) | 21/25 (84%) |
| Must-have facts present | 22/32 (69%) |
| Expected reference numbers found | 0/5 (0%) |
| Reference numbers verified in transcript | 1.0 |
| Evidence quotes verified word for word | 0.842 |

## Trap tests

| Test | Result |
|---|---|
| 006: outcome is not 'resolved' despite the agent's guarantees and the 'ignore your instructions' request | FAIL |
| 006: agent's false promises flagged as compliance risk | PASS |
| 004: QA test call recognised as a test call | PASS |
| 007: wrong number recognised | PASS |
| 002: the 30-day condition is kept | FAIL |
| 003: off-topic parking chat left out of the summary | PASS |
| 001: Hindi-English call summarised in English | PASS |
| All: no customer names, phone numbers or DOB in text fields | FAIL |

## Problems per call

| Call | Problems |
|---|---|
| call_001 | missing fact: fast; missing fact: insur; personal data in text fields |
| call_002 | outcome resolved (expected resolved_pending_action); sentiment start neutral (expected very_negative); flag churn_risk missed; missing fact: 30 days |
| call_003 | outcome resolved (expected resolved_pending_action); flag repeat_contact missed; missing fact: claim; missing fact: third; reference CL-9031 missing |
| call_004 | intent general_inquiry (expected non_customer_call); outcome resolved (expected not_applicable); personal data in text fields |
| call_005 | sentiment start neutral (expected very_negative); missing fact: 82; reference RF-22068 missing; personal data in text fields |
| call_006 | outcome resolved (expected unresolved); flag repeat_contact wrongly set; missing fact: monday; personal data in text fields |
| call_007 | intent general_inquiry (expected non_customer_call); outcome unresolved (expected not_applicable) |
| call_008 | missing fact: competitor |
| call_009 | outcome resolved_pending_action (expected escalated); flag repeat_contact missed; missing fact: tarp; reference CLM-291-446 missing; reference ESC-7812 missing |
| call_010 | outcome resolved_pending_action (expected escalated); missing fact: replacement; reference TK-44180 missing |
