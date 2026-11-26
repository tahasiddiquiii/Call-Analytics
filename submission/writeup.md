# Call Analytics: write-up

## Time spent
TIME_SPENT

## Approach in five lines
1. Code splits each transcript into numbered turns and reads the client brand from the greeting.
2. A local 3B model (Qwen2.5 via Ollama, CPU only) fills one JSON record per call; Ollama is given the JSON Schema, so it can only answer in the right shape with allowed values.
3. Code validates the answer, asks once for a repair if it is invalid, and writes a `failed` record instead of crashing if it still is.
4. Code checks every reference number and evidence quote against the transcript, derives flags and supervisor priority by fixed rules, and sets `needs_review` with reasons when anything does not add up.
5. Hand labels for the 10 calls (frozen before tuning) and trap tests score every prompt version; each change is logged with before/after output.

## Model used and why
MODEL_PARAGRAPH

## Interpretations and decisions
- **Sentiment** is recorded at the start and end of the call plus overall, because one label hides a recovery (call 005) or a collapse (call 006).
- **Outcome** is the state when the call ended, judged by what was done, not by what the agent promised (call 006).
- **Non-customer calls** (test call 004, wrong number 007) still get a full record, so every file has one, but are typed so they can be excluded from statistics.
- **Fixed category lists** for everything a supervisor filters or counts; free-text `detail` fields keep the nuance. `other` keeps unseen call types working.
- **Due dates** are kept as spoken ("Thursday"), because the transcripts carry no call date; no dates are invented.
- **No personal data** (names, date of birth, address, phone, card) in the record's text fields: other software reads records unchecked, and case numbers are enough to follow up.
- **Extra fields** (`call_type`, `client_brand`, `flags`, `supervisor_priority`, `references`, `evidence`, `needs_review`, `quality`) exist for filtering, follow-up, and trust at scale; see the README.
- **"Under 4 GB RAM"** is read as peak memory of the model process during the run, measured.

## How I checked my work
CHECKING_PARAGRAPH

## Where the output is most likely to be wrong
WRONG_PARAGRAPH

## AI tools I used, what I asked them, and what I had to add or correct
AI_PARAGRAPH

## What I would do with more time
NEXT_PARAGRAPH
