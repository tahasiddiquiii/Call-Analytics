# Evaluation: `eval/runs/v1/records.json`

Model `qwen2.5:3b`, prompt `v1-9c0c3a40`, 10/10 records ok, 3 flagged for review, 1057s total.

| Check | Score |
|---|---|
| Call type | 10/10 (100%) |
| Primary intent | 8/10 (80%) |
| Outcome status | 5/10 (50%) |
| Sentiment at start (exact) | 4/10 (40%) |
| Sentiment at end (exact) | 6/10 (60%) |
| Sentiment at start (within 1 step) | 10/10 (100%) |
| Sentiment at end (within 1 step) | 9/10 (90%) |
| Flags (labelled ones) | 20/25 (80%) |
| Must-have facts present | 23/32 (72%) |
| Expected reference numbers found | 4/5 (80%) |
| Reference numbers verified in transcript | 0.833 |
| Evidence quotes verified word for word | 1.0 |

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
| call_001 | flag repeat_contact wrongly set; missing fact: fast; personal data in text fields |
| call_002 | outcome resolved (expected resolved_pending_action); missing fact: 30 days; missing fact: thursday |
| call_003 | missing fact: claim |
| call_004 | intent general_inquiry (expected non_customer_call); outcome resolved (expected not_applicable); flag repeat_contact wrongly set |
| call_005 | missing fact: 82; personal data in text fields |
| call_006 | outcome resolved_pending_action (expected unresolved); sentiment end neutral (expected very_negative); flag repeat_contact wrongly set; missing fact: deductible; missing fact: monday |
| call_007 | intent general_inquiry (expected non_customer_call); flag repeat_contact wrongly set |
| call_008 | flag repeat_contact wrongly set; missing fact: discount |
| call_009 | outcome resolved_pending_action (expected escalated); reference CLM-291-446 missing; personal data in text fields |
| call_010 | outcome resolved_pending_action (expected escalated); missing fact: replacement |
