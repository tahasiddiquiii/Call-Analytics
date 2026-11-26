# Architecture

## Design principle

**The model does only what needs language understanding; code does everything that must be exact.** A 3B model reads well but follows long rule lists and bookkeeping poorly (measured in v2; see [iterations.md](iterations.md)). So the model answers small questions, and code turns the answers into the record, checks them against the transcript, and applies the same rules to every call.

## Pipeline

```
call_xxx.txt
   │
   ▼
1. Parse (parser.py)                          code
   numbered turns, client brand, format warnings
   │
   ▼
2. Three model questions (pipeline.py, llm.py)   Qwen2.5-3B via Ollama, CPU only
   system message = shared rules + transcript (identical for all three, so Ollama reuses its cache)
   ├─ classify  → call_type, agent_name, customer_name*, summary, intent, escalation request
   ├─ judge     → sentiment start/end/overall (code shows the customer's first and last turns),
   │              outcome facts: handed_over, solution_agreed, needs_future_step,
   │              flag facts: agent_overpromised, customer_may_leave, contacted_before,
   │              outcome detail + quote
   └─ actions   → action items, insights with quotes   (skipped for test / wrong-number calls)
   │
   ▼
3. Validate (schema.py)                       code
   Pydantic per answer → if invalid, 1 repair request (prompts/repair.md) → else a "failed" record
   │
   ▼
4. Checks and rules                           code
   rules.py       outcome status from the yes/no facts; flags; priority; trajectory;
                  drop insights that contradict the flags; fixed intent for non-customer calls
   references.py  case numbers extracted from the transcript ("R-F-two-two…" → RF-22068)
   grounding.py   quotes checked word for word against the transcript
   privacy.py     remove customer name*, titles + surnames, emails, card digits, long numbers
   → needs_review + review_reasons for anything doubtful
   │
   ▼
5. Write (pipeline.py)                        code
   all records sorted by call_id + run metadata → outputs/records.json (atomic: temp file + rename)
```

\* The customer's name is asked for only so code can remove it; it is never stored.

## Modules

| Module | Responsibility |
|---|---|
| `callanalytics/__main__.py` | CLI: arguments, setup checks (Ollama running, model present, folder exists), exit codes, run log |
| `callanalytics/config.py` | Settings (model, temperature 0, seed 42, 8k context, `num_gpu 0`, timeouts); refuses non-local servers |
| `callanalytics/parser.py` | Transcript file → turns. Tolerates bad bytes, wrapped lines, unknown speakers; finds the client brand |
| `callanalytics/llm.py` | Minimal Ollama client: JSON-Schema-constrained chat, timeouts, clear setup errors |
| `callanalytics/schema.py` | The three model answer shapes and the final record / output file (Pydantic); exports the JSON Schema |
| `callanalytics/pipeline.py` | Orchestration per call and per run; retries; failed records; atomic write |
| `callanalytics/rules.py` | Outcome rule, flags, priority, trajectory, consistency checks, corrections |
| `callanalytics/references.py` | Spoken-ID tokenizer for case numbers near words like "claim", "ticket", "order" |
| `callanalytics/grounding.py` | Number-word normalisation, canonical ID format, word-for-word quote matching |
| `callanalytics/privacy.py` | Deterministic redaction of personal data from text fields |

## Key rules in code

**Outcome status** (first match wins):

| Condition | Status |
|---|---|
| call type is test / wrong number / abandoned | `not_applicable` |
| `handed_over` | `escalated` |
| not `solution_agreed` | `unresolved` |
| `needs_future_step` | `resolved_pending_action` |
| otherwise | `resolved` |

**Supervisor priority:** high = compliance risk, or an open case (unresolved/escalated) with a negative ending; medium = churn risk, repeat contact, an open case or a negative ending; low = otherwise, and all non-customer calls.

**Flags:** `compliance_risk`, `churn_risk` and `repeat_contact` come from the judge task's yes/no answers; `escalation_requested` from the classify task. All are false for non-customer calls.

## Output contract

- `outputs/records.json` = `{schema_version, generated_at, run{…}, records[…]}`; JSON Schema in `schema/record.schema.json` (a test fails if it is out of date).
- Every record has the same keys. When `status` is `failed`, analysis fields are `null` or empty and `error` says why.
- `needs_review` is set **by code** (never by the model) with plain-English `review_reasons`.
- Field reference: README "Output format".

## Reliability design

| Risk | Protection |
|---|---|
| Invalid JSON or values | Schema-constrained decoding → validation → 1 repair → `failed` record |
| One bad call | Each call isolated; the run always continues |
| Invented IDs | IDs come from the transcript, never from the model |
| Invented quotes | Word-for-word check → `needs_review` |
| Personal data in records | Prompt rule + code redaction; evaluator checks |
| Long calls | Context budget; keeps start and end, flags `truncated` |
| Model server down or model missing | Clear message with the fix, exit code 2 |
| Too many failures | Exit code 1 above 20 % failed |
| Crash while writing | Atomic write |
| Memory growth over a long run | Ollama prompt cache capped (`LLAMA_ARG_CACHE_RAM=1024`) |

## Evaluation architecture

`eval/gold.json` (hand labels) → `eval/evaluate.py` scores any records file (per-field accuracy, facts, references, personal data, 8 trap tests) → `eval/runs/<version>/` keeps every run with the exact prompts it used. `scripts/bakeoff.py` runs other models through the same pipeline; `scripts/benchmark.py` measures time and peak RAM.
