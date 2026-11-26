# Features

## For the supervisor (what is in each record)

| Feature | Field | Notes |
|---|---|---|
| Short summary | `summary` | 1–3 sentences, in English even for mixed-language calls |
| Why the customer called | `intent.primary`, `intent.secondary[]`, `intent.detail` | 13 fixed categories that work across industries, plus free-text detail |
| How the call ended | `outcome.status`, `outcome.detail`, `outcome.basis` | 5 statuses; `basis` shows the yes/no facts behind the status, so it can be explained |
| How the customer felt | `sentiment.start/end/overall/trajectory` | Shows recovery or collapse during the call, not just one label |
| What happens next, and who does it | `action_items[]` (`owner`, `task`, `due`) | Owner: agent, company, customer or supervisor; due date as spoken, never invented |
| What a supervisor should know | `insights[]` (`category`, `text`, `quote`, `verified`) | 7 categories; each insight carries a quote checked against the transcript |
| One-click filters | `flags` | compliance risk, churn risk, repeat contact, escalation requested |
| What to listen to first | `supervisor_priority` | high / medium / low by a fixed, documented rule |
| Follow-up handles | `references[]` | Claim, ticket, refund, order, escalation and policy numbers in one format (`RF-22068`) |
| Which agent, which client | `agent_name`, `client_brand` | For coaching and for comparing client brands |
| Keeping test calls out of statistics | `call_type` | customer_service, test_call, wrong_number, abandoned |

## For trust and automation

| Feature | Where |
|---|---|
| Same record shape every time, published JSON Schema | `schema/record.schema.json` |
| `needs_review` + reasons, set by code | every record |
| Failed calls still produce a record with the error | `status: "failed"`, `error` |
| Evidence quotes verified word for word | `evidence[]`, `insights[].verified` |
| Reference numbers taken only from the transcript | `references.py` |
| Personal data removed from text fields | `privacy.py`; `quality.redactions` counts removals |
| Processing data for monitoring | `quality` (turns, requests, tokens, seconds, corrections) |
| Run metadata (model, prompt version, counts, time) | `run` block in the output file |
| Exit codes for schedulers (0 ok, 1 too many failures, 2 setup problem) | CLI |
| One line per run in a run log | `reports/run_log.jsonl` (local only) |
| Atomic write: no half-written output | `pipeline.write_atomic` |

## For running it

- One command for any folder of call files: `python -m callanalytics <folder>`; options `-o`, `--model`, `-q`.
- Local only: the client refuses any non-localhost model server.
- CPU only (`num_gpu: 0`); prompt cache capped so RAM stays bounded on long runs.
- Python 3.9 to 3.15; two runtime dependencies (`pydantic`, `requests`).

## For checking and improving it

| Tool | Command |
|---|---|
| Unit and end-to-end tests (fake model) | `pytest` |
| Score against hand labels + trap tests | `python eval/evaluate.py [records.json] [--report path]` |
| Time and peak RAM | `python scripts/benchmark.py data/calls` |
| Compare models | `python scripts/bakeoff.py qwen2.5:3b llama3.2:3b …` |
| Supervisor view (counts and filters from the JSON) | `python scripts/summarise.py` |
| Rebuild slides / PDFs | `python scripts/build_slides.py`, `python scripts/make_pdfs.py` |
| Regenerate the JSON Schema | `python -m callanalytics.schema` |
