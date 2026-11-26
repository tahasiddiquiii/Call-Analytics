# Run and demo guide

## Part 1: run it from scratch (any Mac)

```bash
git clone https://github.com/tahasiddiquiii/Call-Analytics.git
cd Call-Analytics
brew install ollama                       # local model runtime
LLAMA_ARG_CACHE_RAM=1024 ollama serve &   # start it (cap keeps RAM bounded)
ollama pull qwen2.5:3b                    # 1.9 GB, once
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements-dev.txt
python -m callanalytics data/calls        # all 10 calls → outputs/records.json (~15–20 min on an M1)
```

If you see `Cannot reach Ollama`, start the server (step 4). If you see `Model … is not downloaded`, run step 5.

## Part 2: before a live demo (5 minutes)

```bash
cd ~/Downloads/call-analytics-assignment
source .venv/bin/activate
curl -s localhost:11434/api/version || (LLAMA_ARG_CACHE_RAM=1024 ollama serve > /tmp/ollama.log 2>&1 &)
# Warm up on the CPU so the first call is not slow (a plain `ollama run` would load the model on the GPU)
curl -s localhost:11434/api/generate -d '{"model":"qwen2.5:3b","prompt":"hi","stream":false,"keep_alive":"30m","options":{"num_gpu":0,"num_ctx":8192,"num_predict":1}}' > /dev/null
ollama ps                                    # should show 100% CPU
mkdir -p /tmp/demo/calls
cp data/calls/call_006.txt eval/unseen_calls/call_102.txt /tmp/demo/calls/
printf '' > /tmp/demo/calls/call_broken.txt
```

**Do not run all 10 calls live**: it takes about 15 minutes. Show the saved `outputs/records.json` and run 2–3 files live (about 3 minutes).

Open in advance: `submission/slides.pdf`, `outputs/records.json`, `docs/iterations.md`, a terminal in the project folder.

## Part 3: the demo (about 12 minutes)

| # | Show | Command / file | What to say |
|---|---|---|---|
| 1 | **The problem and the answer** (1 min) | Slide 1 | "Supervisors can't listen to every call. The system turns each transcript into one structured record, using a 3B model on the CPU. The model reads; code checks the facts." |
| 2 | **Live run** (3 min; start it, talk while it runs) | `python -m callanalytics /tmp/demo/calls -o /tmp/demo/out.json` | One real call, one held-out call I wrote and never tuned on, one empty file. Watch the progress lines. |
| 3 | **While it runs: CPU only, under 4 GB** | `ollama ps` | "100% CPU, about 2.7 GB loaded; measured peak 2.1 GB for the model process." |
| 4 | **The result** (2 min) | Open `/tmp/demo/out.json` → `call_006` | Outcome `unresolved`, `outcome.basis` (the yes/no facts), `compliance_risk`, priority `high`. "The customer told the agent to *ignore your instructions* and record the claim as approved. That's also an attack on my model. It isn't fooled, and the agent's false guarantee is flagged." |
| 5 | **Reliability** (1 min) | `call_broken` in the same file; the exit code | "A broken file becomes a `failed` record with a reason; the run never stops. 1 of 3 failed is over the 20% limit, so the command exits 1. A nightly scheduler would alert." |
| 6 | **More safety checks** (1 min) | `python -m callanalytics data/calls --ollama-url https://api.example.com` | Refused: only a local model server is allowed. |
| 7 | **How I know it's right** (2 min) | `python eval/evaluate.py` | Scores against my hand labels: intent 10/10, outcome 8/10, references 5/5, 7/8 trap tests. "The one failing trap is shown, not hidden." |
| 8 | **How I got here** (1 min) | Slide 2, `docs/iterations.md` | "v2 got *worse*. More rules didn't help a 3B model. So I split the work: small yes/no questions, and code applies the rules." |
| 9 | **Tests** (10 s) | `pytest` | 30 tests in under a second, with a fake model. |
| 10 | **Supervisor view** (30 s) | `python scripts/summarise.py` | Counts and filters straight from the JSON: what a supervisor would do with 10,000 records. |
| 11 | **Findings, reliability, next steps** (2 min) | Slides 3–5 | Each finding names its calls. Be clear about the weaknesses: "resolved" is too optimistic when something is pending, and free text is a draft. |

## Part 4: likely questions

| Question | Short answer |
|---|---|
| Why Qwen2.5-3B? | Best balance in my bake-off on the same labels. Llama 3.2-3B got one more outcome right but mistyped the wrong-number call and needs 3.5 GB. The 1.5B model believed the false guarantee in 006. |
| Why three model questions instead of one? | Measured: one long prompt (v2) scored worse. Small questions plus code-applied rules took outcome from 3/10 to 8/10. |
| How do you stop made-up facts? | IDs come only from the transcript (code); every quote is checked word for word; anything doubtful sets `needs_review`; the outcome rule is code. |
| How do you know the output is correct? | Hand labels written before tuning, 8 trap tests, held-out calls, and reading every record against its call (which found bugs the scores missed). |
| Is it deterministic? | The categories were identical in 3 runs; free-text wording varied slightly (prompt-cache numerics). Reported in `reports/determinism.md`. |
| What about personal data? | Prompt rule plus code redaction of names, emails, card digits and long numbers; the evaluator checks it. Street addresses rely on the prompt. |
| 10,000 calls a night? | ~93 s per call on one laptop CPU, so about 30 machines in parallel for an 8-hour night, or a larger CPU host. Calls are independent. |
| What's weakest? | "Resolved" when a future step is still pending (002, 003); free-text errors in about half the calls; he/she for customers. All documented in `docs/manual_review.md`. |
| What did the AI tool get wrong? | See `docs/ai_usage.md`: the postal-code misreading, a copied prompt example, the missing CPU setting and RAM cap, a library that broke Python 3.9, and some wrong claims in its own notes that I caught. |
| What would you do next? | Label 200 real calls, set up a review queue for `needs_review`, parallel workers, check that quotes support insights, compare a 7B model. |

## Part 5: after the demo

- Stop the server if you started it in the background: `pkill -f "ollama serve"`.
- Remove the demo files: `rm -r /tmp/demo`.
