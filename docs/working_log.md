# Working log

What was done, in order, on 26 November 2026. Times come from the run logs (`eval/runs/*/run.log`, `reports/final_run.log`) and git commit times; other times are approximate.

| Time | Step | Outcome |
|---|---|---|
| ~11:45 | Read the brief (`Assignment.docx`) and all 10 transcripts; listed what each call tests | Traps identified: prompt injection and false promises (006), test call (004), wrong number (007), conditional retention (002), off-topic chat (003), Hindi-English (001), garbled IDs (010) |
| ~12:30 | Wrote the plan mapped to the scoring table ([plan.md](plan.md)); reviewed and approved by me with answers on submission format, slides format and labels | Private GitHub repo; PPTX + PDF; hand labels approved |
| ~13:30 | Setup: Ollama 0.40.18 (Homebrew), `qwen2.5:3b` (1.9 GB), Python venv, git | CPU only confirmed: `offloaded 0/37 layers to GPU`, 2.4 GB loaded |
| ~13:35 | Built parser, schema, model client, prompts v1, pipeline, CLI | First record (call 006) in 140 s; it believed the agent's false promise |
| 13:40–13:57 | **Run v1** (10 calls, 17.6 min) | Outcome 5/10; model copied the prompt's example into every record |
| ~13:45 | Tests (fake model), answer key `eval/gold.json`, evaluator with 8 trap tests, 2 held-out calls | A test caught a parser bug (fix #1 in [fixes.md](fixes.md)) |
| 13:59 | Commit 1: system, tests, evaluation, v1 baseline | — |
| 13:59–14:16 | **Run v2**: example removed, longer rules | Worse: outcome 3/10, references 0/5. Lesson: more rules do not help a 3B model |
| ~14:18 | Redesign: three small questions, yes/no outcome facts, code-extracted references, redaction; tests rewritten | Fixed ID tokenizer bug (#2); found the pinned library broke Python 3.9 (#9) |
| 14:22–14:40 | **Run v3** | Outcome 8/10, intent 10/10, references 5/5, no personal-data leaks |
| 14:42 | Commit 2: three-task design | — |
| ~14:41 | Found Ollama's 8 GB prompt cache; restarted the server with a 1 GB cap (#8) | `limits: 1024.000 MiB` confirmed |
| 14:42–15:03 | **Run v4** (under the benchmark): customer turns shown by code, flags as yes/no questions | Facts 28/32, traps 7/8; peak RAM 2.3 GB |
| ~15:05 | Fixed ID formatting bug (#3); wrote the iteration log, slide builder, write-up draft | — |
| ~15:10 | PowerPoint PDF export blocked by its sandbox (#11) | Paused at my request |
| ~15:55 | Resumed. **Model bake-off**: llama3.2:3b, qwen2.5:1.5b on the same pipeline | Qwen2.5-3B kept: best balance and RAM headroom |
| ~16:00 | Installed LibreOffice (to `~/Applications`) and poppler for PDFs and slide images | First visual check found wrapping titles (#13) |
| 16:31 | Commit 3: v4, bake-off, tooling, docs | — |
| 16:31–16:51 | **Final run #1** inside a no-internet sandbox; determinism check vs v4 | 10/10 records identical |
| 16:52–16:55 | **Held-out run** (2 unseen calls) | 102 correct; 101 shows the future-step bias |
| ~16:53 | **Manual review** of every record against its call | Found 2 redaction bugs (#4, #5) and the free-text errors |
| 16:55 | Commit 4: redaction fixes | — |
| 16:56–17:11 | **Final run #2** (`outputs/records.json`), sandboxed, 15.5 min, peak RAM 2.13 GB | Same scores; categorical fields identical across 3 runs, wording varied |
| ~17:12 | Supervisor summary, README results, QA texts; write-up cut to one page (#12) | — |
| 17:15 | Commit 5: final run, manual review, slides, write-up | Fresh-clone check: 114 files, tests pass |
| later | Push to GitHub | Blocked by the Mac's saved GitHub login (first the wrong account, then a password instead of a token); needs a token or `gh auth login` |
| later | Organised all documentation into `docs/` (this file, introduction, goals, architecture, features, rules, fixes, QA report); moved `plan.md` and the labelling guide here; corrected an inaccurate AI-usage claim (#19) | — |

## Still open

- Push to GitHub; confirm the repository is private and give the reviewer access.
