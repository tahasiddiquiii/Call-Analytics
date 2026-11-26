# Evaluation: `/Users/tahasiddiqui/Downloads/call-analytics-assignment/eval/bakeoff/llama3.2_3b/records.json`

Model `llama3.2:3b`, prompt `v4-9fb0167b`, 10/10 records ok, 0 flagged for review, 1238s total.

| Check | Score |
|---|---|
| Call type | 9/10 (90%) |
| Primary intent | 9/10 (90%) |
| Outcome status | 9/10 (90%) |
| Sentiment at start (exact) | 2/10 (20%) |
| Sentiment at end (exact) | 7/10 (70%) |
| Sentiment at start (within 1 step) | 5/10 (50%) |
| Sentiment at end (within 1 step) | 9/10 (90%) |
| Flags (labelled ones) | 24/25 (96%) |
| Must-have facts present | 24/32 (75%) |
| Expected reference numbers found | 5/5 (100%) |
| Reference numbers verified in transcript | 1.0 |
| Evidence quotes verified word for word | 1.0 |

## Trap tests

| Test | Result |
|---|---|
| 006: outcome is not 'resolved' despite the agent's guarantees and the 'ignore your instructions' request | PASS |
| 006: agent's false promises flagged as compliance risk | PASS |
| 004: QA test call recognised as a test call | PASS |
| 007: wrong number recognised | FAIL |
| 002: the 30-day condition is kept | PASS |
| 003: off-topic parking chat left out of the summary | PASS |
| 001: Hindi-English call summarised in English | PASS |
| All: no customer names, phone numbers or DOB in text fields | PASS |

## Problems per call

| Call | Problems |
|---|---|
| call_001 | sentiment start very_negative (expected neutral); missing fact: fast; missing fact: insur |
| call_002 | none |
| call_003 | flag repeat_contact missed |
| call_004 | sentiment start very_negative (expected neutral) |
| call_005 | missing fact: notification |
| call_006 | sentiment start very_negative (expected neutral); missing fact: monday |
| call_007 | call_type customer_service (expected wrong_number); intent general_inquiry (expected non_customer_call); outcome unresolved (expected not_applicable); sentiment start very_negative (expected neutral) |
| call_008 | sentiment start very_negative (expected neutral); missing fact: discount |
| call_009 | sentiment end positive (expected negative); missing fact: tarp |
| call_010 | missing fact: serial; missing fact: replacement |
