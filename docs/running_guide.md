# Running guide

Every command needed to set up, run, check and troubleshoot the project. Commands are for macOS (zsh); they also work on Linux except where noted. Run them from the project folder.

**Contents**
1. [Requirements](#1-requirements)
2. [First-time setup](#2-first-time-setup)
3. [Start of every session](#3-start-of-every-session)
4. [Run all calls](#4-run-all-calls)
5. [Run one call or a few calls](#5-run-one-call-or-a-few-calls)
6. [Run a call you have just been given](#6-run-a-call-you-have-just-been-given)
7. [Read the output](#7-read-the-output)
8. [Check one call against its hand label](#8-check-one-call-against-its-hand-label)
9. [Unit tests](#9-unit-tests)
10. [Evaluation](#10-evaluation)
11. [Other scripts](#11-other-scripts)
12. [Options, environment variables, exit codes](#12-options-environment-variables-exit-codes)
13. [Troubleshooting](#13-troubleshooting)
14. [Stop and clean up](#14-stop-and-clean-up)

> **Protect the evaluated output.** `outputs/records.json` is the final, evaluated run. By default `python -m callanalytics` and `scripts/benchmark.py` **overwrite it**. For any test or demo run, add `-o /tmp/<something>.json`. If you overwrite it by mistake: `git checkout -- outputs/records.json`.

---

## 1. Requirements

| | |
|---|---|
| OS | macOS or Linux (tested on an Apple M1, 8 GB RAM) |
| Python | 3.9 or newer (tested on 3.9 and 3.15) |
| Ollama | 0.40.x (tested on 0.40.18) |
| Disk | about 2 GB for the model |
| Network | only for the one-time install and model download; runs are fully offline |

## 2. First-time setup

```bash
git clone https://github.com/tahasiddiquiii/Call-Analytics.git
cd Call-Analytics

brew install ollama                          # or https://ollama.com/download (Linux: curl -fsSL https://ollama.com/install.sh | sh)
LLAMA_ARG_CACHE_RAM=1024 ollama serve > /tmp/ollama.log 2>&1 &
ollama pull qwen2.5:3b                       # 1.9 GB, once

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt          # runtime + tests + benchmark (runtime only: requirements.txt)

pytest -q                                    # expect: 30 passed
```

## 3. Start of every session

```bash
cd ~/Downloads/call-analytics-assignment     # or wherever the project is
source .venv/bin/activate                    # prompt shows (.venv)

# Start Ollama with the RAM cap if it is not running
curl -s localhost:11434/api/version || (LLAMA_ARG_CACHE_RAM=1024 ollama serve > /tmp/ollama.log 2>&1 &)
```

**Is the running server using the RAM cap?** If you did not start it yourself with `LLAMA_ARG_CACHE_RAM=1024`, restart it:

```bash
pkill -f "ollama serve"; sleep 2
LLAMA_ARG_CACHE_RAM=1024 ollama serve > /tmp/ollama.log 2>&1 &
sleep 3 && curl -s localhost:11434/api/version     # {"version":"0.40.18"}
```

**Warm up on the CPU** (loads the model so the first call is not slow; a plain `ollama run` would load it on the GPU):

```bash
curl -s localhost:11434/api/generate -d '{"model":"qwen2.5:3b","prompt":"hi","stream":false,"keep_alive":"30m","options":{"num_gpu":0,"num_ctx":8192,"num_predict":1}}' > /dev/null
ollama ps                                    # PROCESSOR must say 100% CPU, SIZE about 2.7 GB
grep "limits" /tmp/ollama.log | tail -1      # must show "limits: 1024.000 MiB" (appears only after a prompt)
```

Before a long run, close heavy apps (browsers, IDE indexing): the machine has 8 GB in total.

## 4. Run all calls

```bash
python -m callanalytics data/calls -o /tmp/all.json      # test run, keeps outputs/records.json safe
python -m callanalytics data/calls                       # overwrites outputs/records.json
```

- Takes about **15–20 minutes** for the 10 calls (about 60–100 s per call).
- One progress line per call: `[3/10] call_003  ok  85.2s`. The status is `ok`, `needs review` or `failed`.
- The last line gives the totals: `Wrote …: 10 ok, 0 failed, 3 need review, 929s total`.
- Each run also adds one line to `reports/run_log.jsonl` (ignored by git).

The two held-out calls (never used for tuning):

```bash
python -m callanalytics eval/unseen_calls -o /tmp/heldout.json     # saved result: eval/runs/heldout/
```

## 5. Run one call or a few calls

The command takes a **folder** and processes every `*.txt` file in it. To run one call, put it in a folder on its own:

```bash
rm -rf /tmp/one && mkdir -p /tmp/one
cp data/calls/call_006.txt /tmp/one/
python -m callanalytics /tmp/one -o /tmp/one/out.json              # about 100 s
```

Several chosen calls:

```bash
rm -rf /tmp/some && mkdir -p /tmp/some
cp data/calls/call_002.txt data/calls/call_006.txt eval/unseen_calls/call_102.txt /tmp/some/
python -m callanalytics /tmp/some -o /tmp/some/out.json
```

Show how a broken file is handled (it becomes a `failed` record and the run continues):

```bash
printf '' > /tmp/some/call_broken.txt
python -m callanalytics /tmp/some -o /tmp/some/out.json; echo "exit code: $?"
# call_broken: status "failed", error "file has no transcript lines"
# 1 of 4 failed is over the 20% limit, so the command exits 1
```

## 6. Run a call you have just been given

### 6.1 Create the file

```bash
rm -rf /tmp/one && mkdir -p /tmp/one
nano /tmp/one/call_new.txt          # paste the transcript, save with Ctrl-O, Enter, exit with Ctrl-X
```

Or paste it directly in the terminal:

```bash
cat > /tmp/one/call_new.txt <<'EOF'
System: Thank you for calling Brightcart. Your call may be recorded.
Agent: Brightcart support, this is Joel.
Customer: Hi, my order hasn't arrived.
EOF
```

Or copy a file you received (Downloads, AirDrop, email):

```bash
cp ~/Downloads/their_call.txt /tmp/one/call_new.txt
```

### 6.2 Check the format

| Rule | Why |
|---|---|
| The file name ends in **lower-case `.txt`** | Only `*.txt` is read. A file ending in `.TXT` or `.text` is **skipped completely**. |
| One turn per line: `Agent: …`, `Customer: …`, optionally `System: …` | Only these three labels are recognised (any case). |
| Other labels (`Rep:`, `Caller:`, `Speaker 1:`) are kept but marked `Unknown` | They are **never** counted as the customer, so sentiment and evidence will be poor. Convert them (below). |
| A first line `System: Thank you for calling <Brand>…` | Fills `client_brand`; without it the brand is `null`. |
| The file name becomes `call_id` | `call_new.txt` → `call_new`. |
| Wrapped lines, bad bytes and Latin-1 text are tolerated | They are counted in `quality.unparsed_lines`. |

**Convert other speaker labels** (adjust the names to what the file uses):

```bash
sed -i '' -E 's/^[[:space:]]*(Rep|Representative|Advisor|Support|Associate|Operator)[[:space:]]*:/Agent:/I; s/^[[:space:]]*(Caller|Client|Member|Patient|User)[[:space:]]*:/Customer:/I' /tmp/one/call_new.txt
```

(On Linux use `sed -i -E` without the `''`.) For `Speaker 1:` / `Speaker 2:`, read the file first to see which is the agent, then:

```bash
sed -i '' -E 's/^Speaker 1:/Agent:/; s/^Speaker 2:/Customer:/' /tmp/one/call_new.txt
```

**Other file types:**

```bash
mv /tmp/one/call_new.TXT /tmp/one/call_new.txt                   # upper-case extension
textutil -convert txt /tmp/one/call_new.docx                      # Word / RTF → .txt (macOS)
rm /tmp/one/call_new.docx                                         # keep only the .txt in the folder
```

For a PDF, copy the text out, paste it into a `.txt` file (6.1), then check the labels.

**Check the parse before running the model** (instant, no model needed):

```bash
python -c "from pathlib import Path; from callanalytics.parser import parse_file; t = parse_file(Path('/tmp/one/call_new.txt')); print('turns', len(t.turns), '| agent', t.count('Agent'), '| customer', t.count('Customer'), '| unknown', t.count('Unknown'), '| brand', t.brand)"
```

You want `customer` above 0 and `unknown` at 0.

### 6.3 Run it and show it

```bash
python -m callanalytics /tmp/one -o /tmp/one/out.json
jq '.records[0] | {summary, intent, outcome, sentiment, flags, supervisor_priority, needs_review, review_reasons}' /tmp/one/out.json
```

There is no hand label for a new call. To check it, read the record against the transcript (section 7 shows the quotes and references).

## 7. Read the output

Every output file has a `run` block (totals and settings) and a `records` list. Replace `call_006` and the file path as needed.

```bash
F=/tmp/one/out.json                                       # or outputs/records.json for the final run

jq '.run' $F                                              # model, CPU, prompt version, totals, time
jq -r '.records[] | "\(.call_id)  \(.status)  \(.call_type)  \(.outcome.status)  \(.supervisor_priority)  review=\(.needs_review)"' $F

jq '.records[] | select(.call_id=="call_006")' $F         # the whole record

jq '.records[] | select(.call_id=="call_006") | {call_type, intent: .intent.primary, outcome: .outcome.status, basis: .outcome.basis, sentiment, flags, supervisor_priority, needs_review, review_reasons}' $F

jq -r '.records[] | select(.call_id=="call_006") | .insights[] | "\(.category) | verified=\(.verified) | \(.quote)"' $F
jq -r '.records[] | select(.call_id=="call_006") | .evidence[] | "\(.supports) | turn \(.turn) | verified=\(.verified) | \(.quote)"' $F
jq '.records[] | select(.call_id=="call_006") | .references' $F
jq '.records[] | select(.call_id=="call_006") | .action_items' $F
jq '.records[] | select(.call_id=="call_006") | .quality' $F       # turns, tokens, time, redactions, rule corrections
jq '.records[] | select(.status=="failed") | {call_id, error}' $F  # failed calls and why
```

Find a quote in the transcript to show it is real:

```bash
grep -n "denied again" data/calls/call_006.txt
```

Without `jq`: `python -m json.tool /tmp/one/out.json | less`, or open the file in the IDE.

## 8. Check one call against its hand label

The hand labels are in `eval/gold.json` (calls 001–010 only). Show the label next to the output:

```bash
jq '.records[] | select(.call_id=="call_006") | {call_type, intent: .intent.primary, outcome: .outcome.status, sentiment, flags}' /tmp/one/out.json
jq '.calls.call_006 | {call_type, intent_primary, outcome_status, sentiment_start, sentiment_end, flags_true, flags_false, must_mention}' eval/gold.json
```

> **Do not run `eval/evaluate.py` on a file with fewer than the 10 labelled calls.** It stops with a traceback (`AttributeError: 'NoneType' object has no attribute 'get'`) when calls 001, 002 or 003 are missing. Use the comparison above for single calls.

## 9. Unit tests

The tests use a fake model, so they need neither Ollama nor the model. Each run takes under a second.

```bash
pytest -q                                            # all 30
pytest -v                                            # all, with names
pytest tests/test_parser.py -v                       # one file: parser
pytest tests/test_grounding.py -v                    # one file: reference numbers and quote checks
pytest tests/test_pipeline.py -v                     # one file: pipeline, rules, privacy, CLI
pytest tests/test_pipeline.py::test_outcome_status_comes_from_the_rule_not_the_model -v    # one test
pytest -k "outcome or invented or personal" -v       # tests whose names match
pytest --collect-only -q                             # list all test names
```

## 10. Evaluation

```bash
python eval/evaluate.py                                          # scores outputs/records.json (all 10 calls)
python eval/evaluate.py /tmp/all.json                            # score a new full run
python eval/evaluate.py eval/runs/v1/records.json                # an older prompt version (v1–v4)
python eval/evaluate.py eval/bakeoff/llama3.2_3b/records.json    # another model from the bake-off
python eval/evaluate.py /tmp/all.json --report /tmp/eval.md      # also write a Markdown report
```

The output gives per-field scores, the 8 trap tests and the problems in each call. Expected for `outputs/records.json`: intent 10/10, outcome 8/10, facts 28/32, references 5/5, traps 7/8.

## 11. Other scripts

| Purpose | Command | Notes |
|---|---|---|
| Supervisor summary (counts and filters from the JSON) | `python scripts/summarise.py` | Prints the summary and **rewrites `reports/summary.md`**. Pass a file to summarise another run: `python scripts/summarise.py /tmp/all.json`. Then run `git checkout -- reports/summary.md` to restore the original. |
| Run time and peak RAM | `python scripts/benchmark.py data/calls /tmp/bench.json` | Runs the full pipeline (15–20 min). **Rewrites `reports/benchmark.json`**. Without the second argument it overwrites `outputs/records.json`. |
| Model bake-off | `python scripts/bakeoff.py qwen2.5:3b=eval/runs/v4 llama3.2:3b qwen2.5:1.5b` | A `name=folder` reuses a saved run; other models are run now (about 20 min each, after `ollama pull <model>`). Rewrites `reports/bakeoff.json`. |
| Rebuild slides | `python scripts/build_slides.py` | Rewrites `submission/slides.pptx` from the reports. |
| Rebuild PDFs | `python scripts/make_pdfs.py` | Needs LibreOffice (`brew install --cask libreoffice`). |

## 12. Options, environment variables, exit codes

```bash
python -m callanalytics --help
```

| Flag | Environment variable | Default | Meaning |
|---|---|---|---|
| `input_dir` (required) | | | Folder of `*.txt` call files |
| `-o`, `--output` | | `outputs/records.json` | Output file |
| `--model` | `CALLANALYTICS_MODEL` | `qwen2.5:3b` | Any model pulled into Ollama |
| `--ollama-url` | `CALLANALYTICS_OLLAMA_URL` | `http://localhost:11434` | Must be `localhost`, `127.0.0.1` or `::1`. Anything else is refused. |
| `--max-failure-ratio` | | `0.2` | Exit 1 if more than this share of calls fail |
| `-q`, `--quiet` | | off | Only warnings and errors |
| | `CALLANALYTICS_TIMEOUT` | `600` | Seconds to wait for one model answer |

Fixed settings (`callanalytics/config.py`):
- temperature 0 and seed 42;
- 8192-token context and an 1800-token output cap;
- `num_gpu 0` (CPU only);
- one repair attempt.

Other examples:

```bash
python -m callanalytics data/calls --model llama3.2:3b -o /tmp/llama.json      # another model
python -m callanalytics data/calls --ollama-url https://api.example.com        # refused, exit 2 (local-only check)
python -m callanalytics /tmp/some -o /tmp/out.json --max-failure-ratio 0.5     # allow more failures
```

**Exit codes**

| Code | Meaning |
|---|---|
| 0 | Run finished; failures at or below the limit |
| 1 | More than 20% of calls failed. The output file is still written. |
| 2 | Setup problem: Ollama not reachable, model not downloaded, folder missing or without `.txt` files, or a non-local server URL |

To see the exit code: `echo $?` right after the command.

## 13. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Cannot reach Ollama at http://localhost:11434` (exit 2) | Server not running | `LLAMA_ARG_CACHE_RAM=1024 ollama serve > /tmp/ollama.log 2>&1 &` |
| `Model 'qwen2.5:3b' is not downloaded` (exit 2) | Model missing | `ollama pull qwen2.5:3b` (1.9 GB) |
| `Input folder not found` / `No .txt call files in …` (exit 2) | Wrong path, or files not ending in `.txt` | `ls <folder>`; rename `.TXT` → `.txt` |
| `Model server must run on this computer (localhost)` | `--ollama-url` or `CALLANALYTICS_OLLAMA_URL` is not local | Remove it, or use `http://localhost:11434`; check with `echo $CALLANALYTICS_OLLAMA_URL` |
| `ollama serve`: `address already in use` | A server is already running (perhaps the Ollama app, without the RAM cap) | Use it, or restart with the cap: `pkill -f "ollama serve"` (quit the Ollama menu-bar app too), then start it again |
| `ModuleNotFoundError: pydantic` / `No module named callanalytics` | venv not active, or not in the project folder | `cd` to the project, `source .venv/bin/activate` |
| `ollama ps` shows GPU, not `100% CPU` | Model loaded by `ollama run` or another app | `ollama stop qwen2.5:3b`, then the CPU warm-up in section 3 |
| First call much slower than the rest | Model still loading | Warm up first (section 3) |
| Run is very slow, or the Mac is swapping | Not enough free RAM | Close browsers and other apps; check memory pressure in Activity Monitor |
| A call fails with `model did not answer within 600s` | Machine overloaded | Free RAM/CPU and run that call alone (section 5); or `CALLANALYTICS_TIMEOUT=900` |
| A call fails after the repair attempt (invalid answer) | The model's JSON did not pass validation twice | Shown as `failed` with the reason in `error`; rerun that call alone |
| Record has `needs_review: true` | A check failed (quote not found word for word, call truncated, rule correction) | Not an error; read `review_reasons` |
| Customer sentiment and evidence look empty or wrong for a given call | Speaker labels not `Agent:` / `Customer:` | Check `quality.customer_turns` and section 6.2 |
| `client_brand` is `null` | No `System: Thank you for calling <Brand>` line | Expected; add the line if the brand is known |
| `eval/evaluate.py` crashes with `AttributeError` | Input file has fewer than the 10 labelled calls | Use section 8 for single calls |
| `outputs/records.json` or `reports/*` changed by accident | Ran without `-o`, or ran a script that rewrites reports | `git checkout -- outputs/records.json reports/` |
| `jq: command not found` (Linux) | jq not installed | `sudo apt install jq`, or use `python -m json.tool` |
| The same call gives slightly different results in two runs | Ollama's prompt-cache reuse changes the floating-point order | Known; see `reports/determinism.md`. The evaluated result is `outputs/records.json`. |

Server log for deeper problems: `tail -50 /tmp/ollama.log`. It shows the GPU offload line, the cache limit and request errors.

## 14. Stop and clean up

```bash
ollama stop qwen2.5:3b             # unload the model, free RAM (server keeps running)
pkill -f "ollama serve"            # stop the server
rm -rf /tmp/one /tmp/some /tmp/all.json /tmp/heldout.json
deactivate                         # leave the venv
git status --short                 # should be empty; restore anything changed with git checkout -- <file>
```
