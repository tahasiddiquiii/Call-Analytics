# Iteration log

Every meaningful change, with the real output before and after. Each run is kept in `eval/runs/<version>/`: the records, the exact prompts used, the run log and the evaluation report, so every "before" below can be checked. Scores are against the hand labels in `eval/gold.json` (all versions scored with the same key).

## Scores by version

| Check | v1 | v2 | v3 | v4 |
|---|---|---|---|---|
| Outcome status | 5/10 | 3/10 | 8/10 | 8/10 |
| Primary intent | 8/10 | 8/10 | 10/10 | 10/10 |
| Sentiment at end (within 1 step) | 9/10 | 10/10 | 9/10 | 9/10 |
| Labelled flags | 20/25 | 21/25 | 22/25 | 22/25 |
| Must-have facts | 23/32 | 22/32 | 24/32 | 28/32 |
| Reference numbers found | 4/5 | 0/5 | 5/5 | 5/5 |
| Trap tests passed | 5/8 | 5/8 | 6/8 | 7/8 |
| `repeat_contact` flags raised (true answer: 2 calls) | 10 | 2 | 0 | 2 |

## v1: one prompt, one invented example

Single request per call with all fields, field definitions, and one invented example call.

## v1 → v2: remove the copied example, tighten rules

**Call 001 (and 9 others), insights copied from the prompt's example.**
- *Before (v1):* `repeat_contact: "Customer mentions this is the second time they have called about an appointment."` Nothing like this is said in the call. v1 raised `repeat_contact` in **10 of 10** calls and added `technical_support` as a secondary intent in **7 of 10**.
- *What was wrong:* the invented example in the prompt contained "This is the second time I've called" and a secondary intent of `technical_support`. The 3B model copied both into almost every record.
- *Change:* removed the example; added "only add an insight if you can quote words that prove it", and each insight now carries a quote that code checks word for word.
- *After (v2):* `repeat_contact` in 2 calls, `technical_support` secondary in 0.

**But v2 got worse elsewhere:** outcome status fell from 5/10 to 3/10 and reference numbers from 4/5 to 0/5. The model ignored a 5-step outcome rule written in the prompt (call 006 again said "Claim will be approved"), and without an example it could not turn spoken IDs into codes: call 009 gave `ESCSEVENEIGHTONETWO`. **Lesson:** a 3B model does not follow a long list of rules while filling ten fields at once. Adding more instructions made it worse.

## v2 → v3: split the work; code does what must be exact

**Call 006, the agent's false guarantee and the "ignore your instructions" request.**
- *Before (v1):* outcome `resolved_pending_action`: "Claim will be approved on appeal, but customer must wait for written decision from the adjuster. **Agent noted the claim was approved in the notes.**"
- *What was wrong:* the model believed the agent's guarantee, which the agent later took back, and stated the opposite of what happened. The agent *refused* to note the claim as approved.
- *Change:* three small questions instead of one big one. For the outcome, the model now answers three yes/no facts (`handed_over`, `solution_agreed`, `needs_future_step`), and **code** applies the outcome rule. The facts are stored in `outcome.basis`, so each status can be explained.
- *After (v3):* outcome `unresolved`, basis `{handed_over: false, solution_agreed: false, needs_future_step: false}`.

**Call 009, reference numbers.**
- *Before:* v1 found only `E-S-C-7812` and missed the claim number; v2 wrote `ESCSEVENEIGHTONETWO`.
- *Change:* reference numbers are extracted from the transcript by code (spoken letters + digits next to a word like "claim", "ticket" or "order"), in one format.
- *After (v3):* `CLM-291446` (claim) and `ESC-7812` (escalation). 5 of 5 expected references found in all calls, with none invented.

**Call 001, personal data.**
- *Before (v1):* outcome detail "Address updated to Flat 402, Palm Residency, Greenfield Road, Pincode 50014". It also contained a false fact, "Old address kept on file for billing", when the customer said "Replace everywhere".
- *Change:* privacy rule in the shared prompt, and code removes the customer's name, titles with surnames, emails, card digits and long numbers.
- *After (v3):* "The customer's appointment was rescheduled for Tuesday at 11 AM with Dr. Iyer, and the address was updated on their patient profile." The personal-data trap test passes.

## v3 → v4: show the right turns; flags as yes/no questions

- *Before (v3):* the model echoed the instruction instead of quoting (call 004's "first words" were *"copy, word for word, the customer's first sentence about their reason for calling."*; the quote check caught it). The 006 false guarantee was labelled `process_gap`, not `compliance_risk`. `churn_risk` insights were attached to quotes that do not say anything about leaving. 002 was `unresolved` although the customer accepted the offer on a condition; 003 was `resolved` although the replacement still had to ship.
- *Change:* code finds the customer's first and last turns and shows them in the judge question (sentiment evidence is exact by construction). The three flags are now direct yes/no questions, and code drops insights that contradict them (logged in `quality.rule_corrections`). The prompt says a conditional acceptance counts as accepted and a shipment is a future step. Text `"null"` due dates become real nulls.
- *After (v4):* facts 28/32 (from 24), traps 7/8 (from 6): the 006 compliance flag now passes and call 004's sentiment evidence is exact. Not fixed: 002 and 003 are still `resolved` rather than `resolved_pending_action` (the model answers `needs_future_step = false`), and 006's angry ending is still read as neutral. The same weakness shows on a held-out call (101). These are reported as known limits rather than tuned further against 10 calls.

## Model bake-off (same pipeline and prompts, v4)

| Model | Outcome | Intent | Facts | Traps | RAM loaded | Time |
|---|---|---|---|---|---|---|
| qwen2.5:3b (chosen) | 8/10 | 10/10 | 28/32 | 7/8 | 2.7 GB | 20 min |
| llama3.2:3b | 9/10 | 9/10 | 24/32 | 7/8 | 3.5 GB | 21 min |
| qwen2.5:1.5b | 5/10 | 10/10 | 25/32 | 5/8 | 1.5 GB | 12 min |

Llama 3.2 got one more outcome right, but it typed the wrong-number call as a customer call (which would pollute statistics), rated 6 call openings "very negative", called 009's exasperated ending "positive", and needs 3.5 GB of the 4 GB budget. Qwen2.5-1.5B is faster but believed the agent's false guarantee in 006 (fails both safety traps). Results: `eval/bakeoff/`, `reports/bakeoff.json`.

## Final run

`outputs/records.json` was produced by the final code (v4 prompts plus the redaction fix from the manual review), under a macOS sandbox that blocks all network except localhost. A second run of the same v4 code was identical in every field except timing (`reports/determinism.md`).

## Bugs found by checking, not by the model

- **Parser:** a `Supervisor:` line was being glued onto the customer's turn (caught by a unit test; unknown speakers now get their own turn).
- **Reference format:** `canonical_reference` did not convert number words, which is how `ESCSEVENEIGHTONETWO` was stored even though the raw value had been verified (fixed and tested).
- **Python 3.9:** the pinned `pydantic==2.14.4` does not install on Python 3.9, so the README's claim was false. Switched to version ranges tested on 3.9 and 3.15.
- **Redaction:** the manual review found "Mr. the customer" and "their the card on file" in final records. Fixed the pattern order and added tests.
- **RAM:** Ollama's runner keeps a prompt cache in RAM of up to 8 GB by default, which would break the 4 GB limit over a long nightly run. The server is now started with `LLAMA_ARG_CACHE_RAM=1024`, confirmed in the server log (`limits: 1024.000 MiB`).
