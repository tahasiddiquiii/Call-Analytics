# QA report

Final state of quality checks for `outputs/records.json` (prompt version `v4-9fb0167b`, model `qwen2.5:3b`). Every number below comes from a file in this repo.

## Summary

| Area | Result | Source |
|---|---|---|
| Accuracy vs hand labels | Call type 10/10 · intent 10/10 · outcome 8/10 · end sentiment 9/10 within one step (7/10 exact) · flags 22/25 · facts 28/32 · references 5/5 | `reports/eval_final.md` |
| Trap tests | 7/8 pass (fails: 002's 30-day condition) | `reports/eval_final.md` |
| Unit tests | 30/30 pass on Python 3.15 and 3.9 | `pytest` |
| Records produced | 10/10 ok, 0 failed, 3 flagged `needs_review` | `outputs/records.json` → `run` |
| Peak RAM (model process) | 2.13 GB (limit 4 GB) | `reports/benchmark.json` |
| CPU only | 0/37 layers on GPU, `100% CPU` | Ollama server log |
| No internet | Final run made inside a sandbox blocking all non-local network | `reports/final_run.log` |
| Run time | 15.5 min for 10 calls (~93 s per call) on an Apple M1, 8 GB | `reports/benchmark.json` |
| Repeatability | Categorical fields identical in 3 runs; free-text wording varied | `reports/determinism.md` |
| Fresh clone | 114 files; no venv, model, cache, `.DS_Store`, brief or secrets; tests and evaluator run | checked before the final commit |

## Trap tests (what each call was designed to test)

| Test | Result |
|---|---|
| 006: outcome not "resolved" despite the agent's guarantees and an "ignore your instructions" request | PASS |
| 006: the agent's false promises flagged as compliance risk | PASS |
| 004: QA test call recognised | PASS |
| 007: wrong number recognised | PASS |
| 002: the 30-day condition kept | **FAIL** |
| 003: off-topic parking chat kept out of the summary | PASS |
| 001: Hindi-English call summarised in English | PASS |
| No customer names, phone numbers or dates of birth in text fields | PASS |

## Progress across versions

| Check | v1 | v2 | v3 | v4 / final |
|---|---|---|---|---|
| Outcome status | 5/10 | 3/10 | 8/10 | 8/10 |
| Primary intent | 8/10 | 8/10 | 10/10 | 10/10 |
| Facts | 23/32 | 22/32 | 24/32 | 28/32 |
| References | 4/5 | 0/5 | 5/5 | 5/5 |
| Trap tests | 5/8 | 5/8 | 6/8 | 7/8 |

Details and before/after outputs: [iterations.md](iterations.md).

## Model bake-off (same pipeline, prompts and labels)

| Model | Outcome | Intent | Facts | Traps | RAM loaded | Time |
|---|---|---|---|---|---|---|
| **qwen2.5:3b** (chosen) | 8/10 | 10/10 | 28/32 | 7/8 | 2.7 GB | 20 min |
| llama3.2:3b | 9/10 | 9/10 | 24/32 | 7/8 | 3.5 GB | 21 min |
| qwen2.5:1.5b | 5/10 | 10/10 | 25/32 | 5/8 | 1.5 GB | 12 min |

## Test coverage (30 tests, `tests/`)

- **Parser:** all provided calls parse cleanly; brand extraction; wrapped lines; unknown speakers; empty files; invalid UTF-8; case-insensitive labels.
- **Grounding and references:** spoken IDs ↔ written IDs; dashes, fillers, "double"/"triple"; canonical format; extraction only near case words; phone numbers never picked up; quotes word for word.
- **Pipeline:** valid answers → ok record; outcome rule; non-customer normalisation; invented quotes → review; personal-data removal and clean redaction text; repair on invalid JSON; invalid enum → clean failure; timeout → failed record; flags from yes/no answers and contradicted insights dropped; judge prompt shows first/last customer turns; text "null" due dates; a run with bad files never stops and every record has the same keys; long-call truncation; CLI rejects a missing folder and remote servers; prompt version changes when prompts change; published JSON Schema is current.

## Manual review

Every final record was read against its transcript ([manual_review.md](manual_review.md)):

- **Categorical fields** are mostly right and safe to filter and count.
- **Free text** (summaries, details, action items) has an error in about half the calls: invented follow-ups (005, 008), "performed a factory reset" (010, the customer declined), work already done listed as to-do (001). Treat it as a draft.
- **Known bias:** `resolved` is too optimistic when a solution still depends on a future step (002, 003, held-out 101).
- **he/she** is used for customers despite the prompt rule.

## Held-out calls

Two calls written for testing and never used for tuning (`eval/runs/heldout/`):
- `call_102` (refund delay, dismissive agent): correct status, sentiment, flags and priority.
- `call_101` (prescription delay): marked `resolved` while approval is pending, the same future-step bias.

## Open risks

1. Scores come from 10 synthetic calls; real traffic will be noisier.
2. A quote proves words exist, not that they support an insight.
3. At ~93 s per call on one laptop CPU, 10,000 calls a night needs parallel machines.
