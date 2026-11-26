# Determinism check: same input, run three times

Settings: temperature 0, fixed seed 42, same prompts (v4).

| Comparison | Categorical fields* | Free text (summary, details, action items, evidence) |
|---|---|---|
| v4 run vs first final run (same code) | 10/10 records identical | 10/10 identical |
| v4 run vs final run (`outputs/records.json`, after the redaction fix) | **10/10 records identical** | 6 records differ in wording (001, 004, 005, 007, 008, 009); 2 of those differences are the intended redaction fix (005, 009) |

\* call type, primary intent, outcome status, sentiment start/end/overall, flags, supervisor priority, reference numbers.

**What this means:** the fields supervisors filter and count did not change between runs. Free-text wording can change slightly even at temperature 0. A likely cause is that Ollama/llama.cpp reuses cached parts of the prompt (the transcript shared by the three questions), which changes the order of floating-point operations. This was found by checking, not assumed. Scores against the hand labels were the same in all three runs. A production system that must reproduce text exactly would disable prompt-cache reuse and accept slower runs.
