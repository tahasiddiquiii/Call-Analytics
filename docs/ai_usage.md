# AI tools used while building, and what I corrected

**Tool:** Claude Code (Claude Opus, in the Claude desktop app) as a coding assistant. It is used only to *build* the system. The system itself uses only the local Qwen2.5-3B model.

## What I asked for, what it produced, what I changed

| # | I asked for | It produced | What I added, corrected or overruled |
|---|---|---|---|
| 1 | Read the brief and the 10 calls; list what each call tests | A table of "traps" per call | **Corrected:** it said call 001's postal code conflicts (500014 vs 50014). Checking the digits by hand: "five double zero one four" = 50014, matching the read-back. Removed from the expected labels. |
| 2 | A plan mapped to the scoring table | [`plan.md`](plan.md) (architecture, schema, checks, timeline) | I reviewed it, chose how to submit, and asked for both PPTX and PDF slides. |
| 3 | Draft hand labels for the 10 calls | Labels table, later `eval/gold.json` | I reviewed and approved them before any tuning; they were frozen so the score could not be bent to fit the output. |
| 4 | Choose and set up a local model | Ollama + Qwen2.5-3B | **Added:** forcing CPU. On a Mac, Ollama uses the GPU by default, which would break the "CPU only" rule. Set `num_gpu: 0` and confirmed in the Ollama log: `offloaded 0/37 layers to GPU`, `100% CPU`. |
| 5 | Few-shot examples for the prompt | One invented example call, deliberately not one of the 10 provided calls | **Decided:** examples taken from the 10 calls would leak the answers into the evaluation. The invented example was later removed too (v2), because the model copied it. |
| 6 | Parser for `Speaker: text` lines | First version appended unknown lines to the previous turn | **Corrected (caught by a test):** a `Supervisor:` line was being credited to the customer. Unknown speaker labels now become their own `Unknown` turn and are counted. |
| 7 | Record design | Schema with fixed category lists | **Decided:** flags and supervisor priority are computed by code from the model's answer, not asked of the model, so the same rule applies to every call and can be explained. |
| 8 | First end-to-end test (call 006) | A valid record, but an evidence quote that contained the customer's full name | **Added:** privacy rule for quotes too, and a documented limitation (verbatim quotes can contain names). |
| 9 | Fix the v1 errors with better prompt rules | v2: no example, a 5-step outcome rule in the prompt | **Measured worse** (outcome 3/10, references 0/5). Changed approach rather than adding more rules: three small questions, yes/no facts, and code for outcome, references and privacy (v3, v4). |
| 10 | Pin dependency versions | `pydantic==2.14.4` | **Corrected:** it does not install on Python 3.9 (the Mac's system Python). Switched to ranges and ran the tests on 3.9 and 3.15. |
| 11 | Prompt caching across the three questions | Worked, but Ollama's runner keeps a RAM prompt cache of up to 8 GB by default | **Added:** `LLAMA_ARG_CACHE_RAM=1024` so a long nightly run cannot exceed the 4 GB limit; confirmed in the server log. |
| 12 | Export slides to PDF from PowerPoint by script | Blocked by PowerPoint's sandbox | Used LibreOffice (headless) instead, which also renders slide images for a visual check. |
| 13 | Its own notes and slide text | Two misstatements: "8 of 10" copied insights (really 10 of 10), and "a customer left" (call 008 only says they may check other carriers) | **Corrected:** checked every figure and claim against the saved runs and transcripts. |
| 14 | Summarise "offline" testing | Wrote "ran with Wi-Fi off", which had not been done | **Corrected:** ran the final pipeline under a macOS sandbox that blocks all network except localhost, and described exactly that. |

Later prompt and rule changes, with before/after outputs, are in [iterations.md](iterations.md).
