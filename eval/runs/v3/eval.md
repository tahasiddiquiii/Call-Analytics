# Evaluation: `eval/runs/v3/records.json`

Model `qwen2.5:3b`, prompt `v3-51870ed5`, 10/10 records ok, 3 flagged for review, 1065s total.

| Check | Score |
|---|---|
| Call type | 10/10 (100%) |
| Primary intent | 10/10 (100%) |
| Outcome status | 8/10 (80%) |
| Sentiment at start (exact) | 6/10 (60%) |
| Sentiment at end (exact) | 7/10 (70%) |
| Sentiment at start (within 1 step) | 8/10 (80%) |
| Sentiment at end (within 1 step) | 9/10 (90%) |
| Flags (labelled ones) | 22/25 (88%) |
| Must-have facts present | 24/32 (75%) |
| Expected reference numbers found | 5/5 (100%) |
| Reference numbers verified in transcript | 1.0 |
| Evidence quotes verified word for word | 0.9 |

## Trap tests

| Test | Result |
|---|---|
| 006: outcome is not 'resolved' despite the agent's guarantees and the 'ignore your instructions' request | PASS |
| 006: agent's false promises flagged as compliance risk | FAIL |
| 004: QA test call recognised as a test call | PASS |
| 007: wrong number recognised | PASS |
| 002: the 30-day condition is kept | FAIL |
| 003: off-topic parking chat left out of the summary | PASS |
| 001: Hindi-English call summarised in English | PASS |
| All: no customer names, phone numbers or DOB in text fields | PASS |

## Problems per call

| Call | Problems |
|---|---|
| call_001 | missing fact: fast |
| call_002 | outcome unresolved (expected resolved_pending_action); missing fact: 30 days |
| call_003 | outcome resolved (expected resolved_pending_action); flag repeat_contact missed; missing fact: claim; missing fact: third |
| call_004 | sentiment start very_negative (expected neutral) |
| call_005 | none |
| call_006 | sentiment start very_negative (expected neutral); sentiment end neutral (expected very_negative); flag compliance_risk missed; missing fact: deductible; missing fact: monday |
| call_007 | none |
| call_008 | none |
| call_009 | flag repeat_contact missed; missing fact: callback |
| call_010 | missing fact: replacement |
