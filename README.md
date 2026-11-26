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
ollama serve &                 # starts the local server on localhost:11434 (skip if the app is running)
ollama pull qwen2.5:3b

# 3. Install the Python code (Python 3.9+)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Run: one command, any folder of call files
python -m callanalytics data/calls
```

The output is written to `outputs/records.json`. Progress is printed per call. Options: `-o PATH` for another output file, `--model NAME` for another Ollama model, `-q` for quiet.

**Exit codes** (for schedulers): `0` ok · `1` more than 20 % of calls failed · `2` setup problem (Ollama not running, model missing, input folder missing). Each run also appends one line to `reports/run_log.jsonl`.

### Optional: tests, evaluation, benchmark

```bash
pip install -r requirements-dev.txt
pytest                                   # 23 tests, uses a fake model, runs in < 1 s
python eval/evaluate.py                  # scores outputs/records.json against hand labels
python scripts/benchmark.py data/calls   # run time + peak RAM of the model process
```

## Model and runtime

| | |
|---|---|
| Model | Qwen2.5-3B-Instruct, 4-bit quantised (`qwen2.5:3b`, Q4_K_M) |
| File size | 1.9 GB |
| Peak RAM (model process) | MEASURED_RAM |
| Runtime | Ollama MEASURED_OLLAMA, **CPU only** (`num_gpu: 0`; Ollama confirms `offloaded 0/37 layers to GPU`, `100% CPU`) |
| Time for the 10 calls | MEASURED_TIME on an Apple M1, 8 GB RAM |
| Settings | temperature 0, seed 42, context 8192 tokens, output cap 1800 tokens |

The client refuses any model server that is not on `localhost`, so the system cannot call a hosted service by mistake.

## How it works

```
call.txt → 1 parse → 2 model → 3 validate (+1 repair) → 4 check against transcript → 5 rules → record
           code       local LLM   code                    code                         code
```

1. **Parse** (`callanalytics/parser.py`): splits `Speaker: text` lines into numbered turns, tolerates bad bytes, wrapped lines and unknown speakers (counted, never credited to the customer), reads the client brand from the System greeting.
2. **Model** (`callanalytics/llm.py`): one request per call. The record's JSON Schema is passed to Ollama, so the model can only produce JSON of the right shape and allowed values.
3. **Validate** (`callanalytics/schema.py`): Pydantic checks the answer. If it is invalid, the errors are sent back once with `prompts/repair.md`. If it is still invalid, a `status: "failed"` record is written; the run continues.
4. **Check against the transcript** (`callanalytics/grounding.py`): every reference number must appear in the call (spoken IDs like "R-F-two-two-zero-six-eight" are normalised to `RF22068`), and every evidence quote must appear word for word.
5. **Rules** (`callanalytics/rules.py`): code derives the flags, the sentiment trajectory and the supervisor priority, and checks for contradictions (e.g. a test call with outcome "resolved"). Any problem sets `needs_review: true` with a plain-English reason.

The model does only what needs language understanding; everything that must be exact is done by code.

**Prompts:** every prompt sent to the model is in [`prompts/`](prompts/): `system.md` (instructions, field definitions, one invented example), `user_template.md` (wraps the transcript) and `repair.md` (retry). The version label plus a hash of the prompt files is stored in every output as `prompt_version`.

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
| `summary` | string | **(1)** 1–3 sentences |
| `intent` | `{primary, secondary[], detail}` | **(2)** `primary`/`secondary` from: `appointment_change`, `account_update`, `cancellation_request`, `billing_dispute`, `refund_request`, `order_issue`, `claim_appeal`, `claim_status`, `plan_change_inquiry`, `technical_support`, `general_inquiry`, `non_customer_call`, `other` |
| `outcome` | `{status, detail}` | **(3)** `status`: `resolved` · `resolved_pending_action` · `escalated` · `unresolved` · `not_applicable` |
| `sentiment` | `{start, end, overall, trajectory}` | **(4)** Customer feeling, each `very_negative` … `very_positive`; `trajectory` (`improved`/`stable`/`worsened`) computed by code |
| `action_items[]` | `{owner, task, due}` | **(5)** `owner`: `agent` · `company` · `customer` · `supervisor`; `due` as spoken in the call or null |
| `insights[]` | `{category, text}` | **(6)** `category`: `agent_conduct` · `compliance_risk` · `process_gap` · `product_feedback` · `churn_risk` · `repeat_contact` · `data_quality` |
| `flags` | `{compliance_risk, churn_risk, repeat_contact, escalation_requested}` booleans | One-click filters; first three derived from insight categories by code |
| `supervisor_priority` | `high` · `medium` · `low` | Rule (code): **high** = compliance risk, or case still open (unresolved/escalated) with a negative ending; **medium** = churn risk, repeat contact, open case or negative ending; **low** = otherwise, and all non-customer calls |
| `references[]` | `{type, value, verified}` | Case numbers (order, claim, ticket, refund, escalation, policy); `verified` = found in transcript by code |
| `evidence[]` | `{supports, turn, quote, verified}` | Short verbatim quotes backing the outcome, sentiment and insights; `verified` = found word for word by code |
| `needs_review` | boolean | Set by code when any check fails |
| `review_reasons[]` | strings | Why |
| `quality` | `{turns, customer_turns, unparsed_lines, truncated, attempts, processing_seconds, prompt_tokens, output_tokens}` | Monitoring data |

**Privacy:** the prompt tells the model not to copy names, dates of birth, addresses, phone, card or email details into the record; code flags long digit runs in text fields. Evidence quotes are verbatim and may still contain a name.

## Project layout

```
callanalytics/   the system (parser, llm client, schema, grounding, rules, pipeline, CLI)
prompts/         every prompt sent to the model
schema/          JSON Schema of the output, for other software
outputs/         records.json, generated by the system
eval/            hand labels, labelling guide, evaluator, earlier runs, held-out calls
tests/           unit and end-to-end tests (fake model)
scripts/         benchmark
reports/         evaluation and benchmark results
docs/            iteration log, AI-tool usage, manual review
submission/      slides (PPTX + PDF) and write-up
```
