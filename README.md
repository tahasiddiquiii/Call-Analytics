# Call Analytics

Reads phone-call transcripts and writes one structured, machine-readable record per call, using a **small language model running locally on the CPU** (Qwen2.5-3B via Ollama). No hosted model, no GPU, no internet after the model download.

```
data/calls/*.txt  ──►  python -m callanalytics data/calls  ──►  outputs/records.json
```

## Quick start (macOS / Linux)

```bash
# 1. Get the code
git clone https://github.com/tahasiddiquiii/Call-Analytics.git
cd Call-Analytics

# 2. Install Ollama (local model runtime) and download the model (~1.9 GB, once)
brew install ollama            # or download from https://ollama.com/download
LLAMA_ARG_CACHE_RAM=1024 ollama serve &   # local server on localhost:11434; the cap keeps RAM bounded (see below)
ollama pull qwen2.5:3b

# 3. Install the Python code (tested on Python 3.9 and 3.15)
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run: one command, any folder of call files
python -m callanalytics data/calls
```

The output is written to `outputs/records.json`. Progress is printed per call. Options: `-o PATH` for another output file, `--model NAME` for another Ollama model, `-q` for quiet.

**Exit codes** (for schedulers): `0` ok · `1` more than 20 % of calls failed · `2` setup problem (Ollama not running, model missing, input folder missing). Each run also appends one line to `reports/run_log.jsonl`.

### Optional: tests, evaluation, benchmark

```bash
pip install -r requirements-dev.txt
pytest                                   # 30 tests, uses a fake model, runs in < 1 s
python eval/evaluate.py                  # scores outputs/records.json against hand labels
python scripts/benchmark.py data/calls   # run time + peak RAM of the model process
```

## Results at a glance

Scored against hand labels for all 10 calls (`eval/gold.json`), final run (`reports/eval_final.md`):

| Call type | Intent | Outcome status | End sentiment (±1 step) | Facts present | Reference numbers | Trap tests |
|---|---|---|---|---|---|---|
| 10/10 | 10/10 | 8/10 | 9/10 | 28/32 | 5/5 | 7/8 |

- The 4 prompt versions, what changed and why: [`docs/iterations.md`](docs/iterations.md) (v1 outcome 5/10 → v4 8/10; one version got *worse* and changed the design).
- Every record read against its call, including errors the scores miss: [`docs/manual_review.md`](docs/manual_review.md).
- Model bake-off (Qwen2.5-3B vs Llama 3.2-3B vs Qwen2.5-1.5B): [`reports/bakeoff.json`](reports/bakeoff.json).
- Two identical runs (determinism): [`reports/determinism.md`](reports/determinism.md). Final run made under a sandbox that blocks all non-local network.
- What the records say for a supervisor (counts and filters from the JSON only): [`reports/summary.md`](reports/summary.md).

**Known limits:** `resolved` is too optimistic when a solution still depends on a future step (002, 003); free-text fields (summaries, action items) contain errors in about half the calls and should be read as drafts; the model sometimes uses he/she for customers. Details in `docs/manual_review.md`.

## Model and runtime

| | |
|---|---|
| Model | Qwen2.5-3B-Instruct, 4-bit quantised (`qwen2.5:3b`, Q4_K_M) |
| File size | 1.9 GB |
| Peak RAM (model process) | 2.13 GB peak resident memory of the Ollama model process, sampled every 0.5 s (`scripts/benchmark.py`); `ollama ps` reports 2.7 GB loaded including the 8k context |
| Runtime | Ollama 0.40.18, **CPU only** (`num_gpu: 0`; Ollama confirms `offloaded 0/37 layers to GPU`, `100% CPU`) |
| Time for the 10 calls | 15.5 min in the final run (~93 s per call, 3 model requests each; earlier runs took ~20 min while the machine did other work) on an Apple M1, 8 GB RAM |
| Settings | temperature 0, seed 42, context 8192 tokens, output cap 1800 tokens |

The client refuses any model server that is not on `localhost`, so the system cannot call a hosted service by mistake.

## How it works

```
call.txt → 1 parse → 2 three small model questions → 3 validate (+1 repair each) → 4 checks, rules, privacy → record
           code       local LLM (shared cached transcript)  code                     code
```

1. **Parse** (`callanalytics/parser.py`): splits `Speaker: text` lines into numbered turns. It tolerates bad bytes, wrapped lines and unknown speakers (counted, never credited to the customer) and reads the client brand from the System greeting.
2. **Three small model questions** (`prompts/task_*.md`), each with its own JSON Schema passed to Ollama, so the model can only answer in the right shape with allowed values:
   - *classify*: call type, agent name, summary, intent, escalation request (and the customer's name, used only so code can remove it);
   - *judge*: the customer's first and last words **quoted before** rating sentiment, plus three yes/no facts about the outcome;
   - *actions*: action items and insights, each insight with a supporting quote (skipped for test calls and wrong numbers).
   The transcript sits in the system message, identical for all three, so Ollama reuses its cached reading of the call.
3. **Validate** (`callanalytics/schema.py`): Pydantic checks each answer. If it is invalid, the errors are sent back once with `prompts/repair.md`. If it is still invalid, a `status: "failed"` record is written and the run continues.
4. **Code does everything that must be exact** (`rules.py`, `references.py`, `grounding.py`, `privacy.py`):
   - **outcome status** from the three yes/no facts with a fixed rule: not a customer call → `not_applicable`; handed to another team → `escalated`; no accepted solution → `unresolved`; depends on a future step → `resolved_pending_action`; else `resolved`. The facts are kept in `outcome.basis`, so every status can be explained;
   - **reference numbers** extracted from the transcript by code ("R-F-two-two-zero-six-eight" → `RF-22068`), so they are always real;
   - **quotes** (evidence and insights) checked word for word against the transcript;
   - **flags, sentiment trajectory and supervisor priority** by fixed rules;
   - **personal data** (customer name, titles with surnames, emails, card digits, long numbers) removed from text fields;
   - any problem sets `needs_review: true` with a plain-English reason.

The model does only what needs language understanding; everything that must be exact is done by code. This split came from evaluation: see `docs/iterations.md`.

**Prompts:** every prompt sent to the model is in [`prompts/`](prompts/): `system.md` (shared rules + the transcript), `task_classify.md`, `task_judge.md`, `task_actions.md` and `repair.md`. The version label plus a hash of the prompt files is stored in every output as `prompt_version`.

## Output format

`outputs/records.json` (JSON Schema: [`schema/record.schema.json`](schema/record.schema.json), `schema_version` "1.0"):

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-11-27T10:15:00Z",
  "run": { "model": "...", "runtime": "...", "device": "cpu", "prompt_version": "...", "input_dir": "...",
           "calls_total": 10, "calls_ok": 10, "calls_failed": 0, "calls_needing_review": 0, "total_seconds": 0 },
  "records": [ /* one per call file, sorted by call_id */ ]
}
```

Every record has **the same keys in every case**. When `status` is `"failed"`, the analysis fields are `null` or empty lists, and `error` says why.

| Field | Type / allowed values | Meaning |
|---|---|---|
| `call_id` | string | File name without `.txt` |
| `status` | `ok` · `failed` | Whether analysis succeeded |
| `error` | string · null | Why it failed |
| `call_type` | `customer_service` · `test_call` · `wrong_number` · `abandoned` | Lets supervisors exclude non-customer calls from statistics |
| `client_brand` | string · null | From the System greeting, by code |
| `agent_name` | string · null | As the agent introduced themselves; lets supervisors coach individuals |
| `summary` | string | **(1)** 1–3 sentences |
| `intent` | `{primary, secondary[], detail}` | **(2)** `primary`/`secondary` from: `appointment_change`, `account_update`, `cancellation_request`, `billing_dispute`, `refund_request`, `order_issue`, `claim_appeal`, `claim_status`, `plan_change_inquiry`, `technical_support`, `general_inquiry`, `non_customer_call`, `other` |
| `outcome` | `{status, detail, basis}` | **(3)** `status`: `resolved` · `resolved_pending_action` · `escalated` · `unresolved` · `not_applicable`, computed by code from `basis` = `{handed_over, solution_agreed, needs_future_step}` (the model's yes/no answers; null for non-customer calls) |
| `sentiment` | `{start, end, overall, trajectory}` | **(4)** Customer feeling, each `very_negative` … `very_positive`; `trajectory` (`improved`/`stable`/`worsened`) computed by code |
| `action_items[]` | `{owner, task, due}` | **(5)** `owner`: `agent` · `company` · `customer` · `supervisor`; `due` as spoken in the call or null |
| `insights[]` | `{category, text, quote, verified}` | **(6)** `quote` proves the insight; `verified` = found word for word by code. `category`: `agent_conduct` · `compliance_risk` · `process_gap` · `product_feedback` · `churn_risk` · `repeat_contact` · `data_quality` |
| `flags` | `{compliance_risk, churn_risk, repeat_contact, escalation_requested}` booleans | One-click filters; first three derived from insight categories by code |
| `supervisor_priority` | `high` · `medium` · `low` | Rule (code): **high** = compliance risk, or case still open (unresolved/escalated) with a negative ending; **medium** = churn risk, repeat contact, open case or negative ending; **low** = otherwise, and all non-customer calls |
| `references[]` | `{type, value, verified}` | Case numbers (order, claim, ticket, refund, escalation, policy, other) **extracted by code** in one format (`RF-22068`); `verified` is therefore always true |
| `evidence[]` | `{supports, turn, quote, verified}` | The customer's first and last words (sentiment) and the words that show how the call ended (outcome); `verified` = found word for word by code |
| `needs_review` | boolean | Set by code when any check fails |
| `review_reasons[]` | strings | Why |
| `quality` | `{turns, customer_turns, unparsed_lines, truncated, model_requests, processing_seconds, prompt_tokens, output_tokens, redactions, rule_corrections[]}` | Monitoring data: how hard the call was to process and what code changed |

**Privacy:** customer data is kept out of text fields in two layers: the prompt asks for none, and code removes the customer's name, titles with surnames, emails, card digits and long numbers (`quality.redactions` counts them). Street addresses have no reliable pattern and rely on the prompt; the evaluator checks them. Agent first names are kept on purpose, for coaching.

## Documentation

All project documentation is in [`docs/`](docs/).

| File | Contents |
|---|---|
| [architecture.md](docs/architecture.md) | Pipeline, modules, rules in code, output contract, reliability design |
| [iterations.md](docs/iterations.md) | v1→v4 with real before/after outputs and scores; bake-off |
| [fixes.md](docs/fixes.md) | Every bug and wrong claim found, and how it was fixed |
| [qa_report.md](docs/qa_report.md) | Final quality results, tests, held-out calls, open risks |
| [manual_review.md](docs/manual_review.md) | Every record read against its call |
| [labeling_guide.md](docs/labeling_guide.md) | How the hand labels were made |
| [ai_usage.md](docs/ai_usage.md) | AI tools used, what they produced, what was corrected |
| [working_log.md](docs/working_log.md) | What was done, in order, with times |

## Project layout

```
callanalytics/   the system (parser, llm client, schema, grounding, rules, pipeline, CLI)
prompts/         every prompt sent to the model
schema/          JSON Schema of the output, for other software
outputs/         records.json, generated by the system
eval/            hand labels, labelling guide, evaluator, runs v1–v4 (records + prompts used), bake-off, held-out calls
tests/           unit and end-to-end tests (fake model)
scripts/         benchmark (time + RAM), bakeoff (model comparison), summarise (supervisor view), slides and PDFs
reports/         evaluation and benchmark results
docs/            all documentation (see above)
submission/      slides (PPTX + PDF) and write-up
```
