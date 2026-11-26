# AI tools used while building, and what I corrected

**Tool:** Claude Code (Claude Opus, in the Claude desktop app) as a coding assistant. It is used only to *build* the system. The system itself uses only the local Qwen2.5-3B model.

## What I asked for, what it produced, what I changed

| # | I asked for | It produced | What I added, corrected or overruled |
|---|---|---|---|
| 1 | Read the brief and the 10 calls; list what each call tests | A table of "traps" per call | **Corrected:** it said call 001's postal code conflicts (500014 vs 50014). Checking the digits by hand: "five double zero one four" = 50014, matching the read-back. Removed from the expected labels. |
| 2 | A plan mapped to the scoring table | `plan.md` (architecture, schema, checks, timeline) | I reviewed it, chose a private GitHub repo over a zip, and asked for both PPTX and PDF slides. |
| 3 | Draft hand labels for the 10 calls | Labels table, later `eval/gold.json` | I reviewed and approved them before any tuning; they were frozen so the score could not be bent to fit the output. |
| 4 | Choose and set up a local model | Ollama + Qwen2.5-3B | **Added:** forcing CPU. On a Mac, Ollama uses the GPU by default, which would break the "CPU only" rule. Set `num_gpu: 0` and confirmed in the Ollama log: `offloaded 0/37 layers to GPU`, `100% CPU`. |
| 5 | Few-shot examples for the prompt | Suggested using provided calls as examples | **Overruled:** examples taken from the 10 calls would leak the answers and make the evaluation meaningless. Used one invented call instead. |
| 6 | Parser for `Speaker: text` lines | First version appended unknown lines to the previous turn | **Corrected (caught by a test):** a `Supervisor:` line was being credited to the customer. Unknown speaker labels now become their own `Unknown` turn and are counted. |
| 7 | Record design | Schema with fixed category lists | **Decided:** flags and supervisor priority are computed by code from the model's answer, not asked of the model, so the same rule applies to every call and can be explained. |
| 8 | First end-to-end test (call 006) | A valid record, but an evidence quote that contained the customer's full name | **Added:** privacy rule for quotes too, and a documented limitation (verbatim quotes can contain names). |

Later prompt and rule changes, with before/after outputs, are in [iterations.md](iterations.md).
