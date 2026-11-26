# Call Analytics: write-up

## Time spent
TIME_SPENT

## Approach in five lines
1. Code splits each transcript into numbered turns and reads the client brand from the greeting.
2. A local 3B model answers three small questions per call (classify; sentiment + yes/no outcome facts; actions + insights), each forced into a JSON Schema by Ollama.
3. Code applies the outcome rule to the yes/no facts, extracts reference numbers from the transcript, checks every quote word for word, removes personal data and sets flags and priority by fixed rules.
4. Invalid answers get one repair try; otherwise a `failed` record with a reason is written, and anything doubtful sets `needs_review` with reasons.
5. Hand labels for the 10 calls (frozen before tuning) and 8 trap tests scored four prompt versions; each change is logged with real before/after output.

## Model used and why
MODEL_PARAGRAPH

## Interpretations and decisions
- **Outcome** = state at the end of the call, judged by what was done, not promised (006). Stored with the yes/no facts behind it (`outcome.basis`).
- **Sentiment** = start, end and overall plus direction, because one label hides recovery (005) or collapse (006).
- **Non-customer calls** (test 004, wrong number 007) get a full record but are typed so they stay out of statistics.
- **Fixed category lists** for everything supervisors filter or count; free-text `detail` keeps nuance; `other` covers unseen calls.
- **Due dates** as spoken ("Thursday"): transcripts have no call date, so none are invented.
- **No customer personal data** in text fields (records go to other software unchecked; case numbers suffice). Agent first names are kept for coaching.
- **Extra fields** (`call_type`, `client_brand`, `agent_name`, `flags`, `supervisor_priority`, `references`, `evidence`, `needs_review`, `quality`) serve filtering, follow-up and trust at scale (README).
- **"Under 4 GB"** = peak resident memory of the model process, measured, with Ollama's prompt cache capped (its default allows 8 GB).

## How I checked my work
- **Hand labels** for all 10 calls (`eval/gold.json`, rules in `eval/labeling_guide.md`), written before tuning and reviewed by me; later only *added* checks, never changed labels.
- **Scorer** (`eval/evaluate.py`) for every version: per-field accuracy, must-have facts, reference numbers, personal-data leaks, and **8 trap tests** (006 prompt injection and false promises, test call, wrong number, conditional retention, off-topic chat, Hindi-English, personal data). Final: outcome 8/10, intent 10/10, facts 28/32, references 5/5, traps 7/8.
- **Checks inside every run:** quotes verified word for word, IDs taken from the transcript, contradictions set `needs_review`.
- **29 unit tests** with a fake model (bad files, repair, failures, privacy, identical record shape), passing on Python 3.9 and 3.15.
- **Run checks:** the final run went through a macOS sandbox that blocks all network except localhost; it was run twice and compared (determinism); 2 held-out calls I wrote were never used for tuning; and I read every final record against its call (`docs/manual_review.md`).

## Where the output is most likely to be wrong
- **Outcome when something is still pending:** 002 and 003 come out `resolved`, although 002 depends on the 30-day fix and 003 on the replacement shipping.
- **Exact sentiment level:** 7/10 exact at the end of the call, 9/10 within one step. 006's angry ending ("write down … your name") was read as neutral.
- **Insights:** a quote proves the words exist, not that they support the insight; some are shallow.
- **Details in long calls** can be dropped (the 8-hour fasting rule in 001).
- **Real traffic:** noisier speech-to-text and call types not in these 10. The scores come from 10 synthetic calls.

## AI tools I used, what I asked them, and what I had to add or correct
I used **Claude Code** as a coding assistant. I asked it to read the brief and calls and plan against the scoring table, draft hand labels (I reviewed them), and write the code, prompts, tests, evaluator and slides. I directed each iteration from the scores. What I had to add or correct (details in `docs/ai_usage.md`):
- It claimed call 001's postal code was a conflict; checking the digits by hand showed it is not.
- Its v1 prompt example was copied by the model into every record; removed. I overruled using real calls as examples, because that would leak answers into the evaluation.
- It did not force CPU (Ollama on a Mac uses the GPU by default) or cap Ollama's prompt cache (up to 8 GB); both added and verified in the server log.
- It pinned a library version that does not install on Python 3.9; fixed and tested on 3.9 and 3.15.
- Its own notes overstated or misstated results twice (a count of 8/10 that was really 10/10; a "left the company" finding the call does not support); I checked every figure against the saved runs.

## What I would do with more time
1. Hand-label ~200 real calls and measure each field before trusting the numbers. 2. Route `needs_review` calls to a person and turn corrections into tests. 3. Parallel workers for 10,000 calls a night. 4. Check that quotes *support* insights, not just exist. 5. Compare a 7B model where hardware allows.
