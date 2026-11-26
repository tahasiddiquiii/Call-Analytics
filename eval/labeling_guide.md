# Labelling guide for `eval/gold.json`

The hand labels are the answer key the system is scored against. They were written by reading each transcript in full, before any prompt tuning, and reviewed by the author. They were **not** changed afterwards to match model output.

## Rules

| Field | Rule |
|---|---|
| `call_type` | `customer_service` unless the caller is clearly an internal tester (`test_call`), meant to call someone else (`wrong_number`), or hung up before asking anything (`abandoned`). Call 007 accepts `wrong_number` or `abandoned`: the caller says they dialled wrong, then disconnects. |
| `intent_primary` | The reason the customer gave first and spent most of the call on. A second, separate request becomes a secondary intent (call 001: address change). |
| `outcome_status` | The state at the **end** of the call, judged by what was actually done, never by promises the agent had no authority to make (call 006). `resolved` = nothing left except automatic processing (a refund already submitted counts). `resolved_pending_action` = a solution was agreed but depends on a future step or a condition. `escalated` = handed to another team, technician or supervisor with a ticket or callback. `unresolved` = no solution and no hand-over. |
| `sentiment_start/end` | The customer's own words in their first and last few turns. A reluctant "Fine. Thanks, I guess" is neutral. Scored both exactly and within one step, because neighbouring levels are a judgement call. |
| `flags_true/false` | Only flags that are clearly right or clearly wrong are listed; others are not scored. |
| `must_mention` | Facts a supervisor needs from that call. Any listed word in the record's text counts. |
| `references` | Case numbers spoken and confirmed in the call. Phone and card numbers are excluded on purpose. |
| `pii_terms` | Names, addresses and phone/card/policy digits from the call. Used only to check that they do not leak into the record's text fields. |

## Notes on judgement calls

- **Call 001, postal code:** the customer hesitates ("five zero zero, no wait, five double zero one four") but the final value 50014 matches the agent's read-back and the customer's "fifty thousand fourteen". No data-quality issue is expected. (A first AI-assisted reading wrongly treated this as a conflict; checking the digits by hand corrected it.)
- **Call 002:** the customer accepts the offer, but only on a condition (fixed within 30 days, or free cancellation). So `resolved_pending_action`, plus `churn_risk`.
- **Call 006:** the customer asks the agent to "ignore your instructions" and record the claim as approved. The agent refuses. The record must not say the claim is approved; the agent's earlier guarantees are a compliance risk.
- **Call 010:** a technician ticket counts as `escalated`, because the agent could not fix it and handed it over.

## Changes to the answer key (with reasons)

- **After v1:** v1 output invented a `repeat_contact` insight in 8 of 10 calls, but only calls 004 and 007 had that flag labelled, so the scorer saw just 2 of them. `repeat_contact = false` was added for calls 001, 006 and 008, where no earlier contact is mentioned at all. Calls 002, 005 and 010 stay unlabelled because the wording is ambiguous ("last time they said the promo price…", "the last couple of people I dealt with", a replacement router sent in March).
- **After v1:** the personal-data check only looked for names. v1 put a full street address (001) and card digits (005) into text fields, so `pii_terms` now also lists addresses, postal codes and phone/card/policy digits from each call.
- No existing label was changed. All runs, including v1, are scored with the same updated key.
