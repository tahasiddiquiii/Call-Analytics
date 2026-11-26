# Call Analytics: write-up

## Time spent
TIME_SPENT

## Approach in five lines
1. Code splits each transcript into numbered turns and reads the client brand from the greeting.
2. A local 3B model answers three small questions per call, each forced into a JSON Schema.
3. Code derives outcome, flags and priority, extracts IDs, verifies quotes and removes personal data.
4. Invalid answers get one repair try, else a `failed` record with a reason; anything doubtful sets `needs_review` with reasons.
5. Hand labels and 8 trap tests scored four prompt versions; each change is logged with real before/after output.

## Model used and why
**Qwen2.5-3B-Instruct**, 4-bit, 1.9 GB file, via **Ollama 0.40.18, CPU only** (0/37 layers on GPU). Peak RAM of the model process **2.1 GB**, measured. Hardware: Apple M1, 8 GB. **15.5 min for the 10 calls** (~93 s each). Chosen by a bake-off on my labels: Llama 3.2-3B got one more outcome right, but mistyped the wrong-number call and needs 3.5 GB; Qwen2.5-1.5B is faster but believed the false guarantee in 006.

## Interpretations and decisions
- **Outcome** = state at the end of the call, by what was done, not promised (006); the yes/no facts behind it are stored.
- **Sentiment** = start, end and overall, since one label hides recovery (005) or collapse (006).
- **Test and wrong-number calls** (004, 007) get records but are typed so they stay out of statistics.
- **Fixed categories** for filtering; **due dates** as spoken; **no customer personal data** (agent names kept).
- **"Under 4 GB"** = measured peak memory of the model process, with Ollama's prompt cache capped (default allows 8 GB).

## How I checked my work
- **Hand labels** for all 10 calls (`eval/gold.json`), written before tuning and reviewed by me; checks only ever added, labels never changed.
- **Scorer** for every version: per-field accuracy, facts, references, personal-data leaks, 8 trap tests (e.g. 006 prompt injection). Final: outcome 8/10, intent 10/10, facts 28/32, references 5/5, traps 7/8.
- **30 unit tests** (fake model) on Python 3.9 and 3.15; final run in a sandbox blocking non-local network; 3 runs gave identical categorical fields (wording varied); 2 held-out calls never tuned on.
- **Read every record against its call** (`docs/manual_review.md`): found 2 bugs in my redaction code and the errors below.

## Where the output is most likely to be wrong
- **"Resolved" is too optimistic** when a fix still depends on a future step (002, 003, held-out 101).
- **Free text is a draft:** about half the summaries/action lists have an error (invented follow-up in 008; "performed a factory reset" in 010, when it was declined); he/she used for customers.
- **Exact sentiment level** (7/10 exact, 9/10 within one step); 006's angry ending read as neutral.
- **Real traffic** is noisier than these 10 synthetic calls.

## AI tools I used, what I asked them, and what I had to add or correct
I used **Claude Code** to plan against the scoring, draft hand labels (I reviewed them), and write the code, prompts, tests, evaluator and slides; I directed each iteration from the scores. Corrections (`docs/ai_usage.md`): it misread call 001's postal code as a conflict; its prompt example was copied into every record (removed; real calls were never used as examples, so the evaluation stays honest); it did not force CPU or cap Ollama's 8 GB prompt cache (added, verified in the log); it pinned a library that breaks on Python 3.9 (fixed); its notes misstated two results (I checked every figure against the saved runs).

## What I would do with more time
Label ~200 real calls; review queue for `needs_review`; parallel workers for 10,000 calls a night; check quotes *support* insights; compare a 7B model (most important first).
