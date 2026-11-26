# Fixes

Every bug and mistake found during the build, how it was found, and how it was fixed. Model-quality changes between prompt versions are in [iterations.md](iterations.md).

## Code bugs

| # | Problem | How it was found | Fix | Guarded by |
|---|---|---|---|---|
| 1 | A line from an unexpected speaker (`Supervisor: …`) was appended to the customer's turn, so it was credited to the customer | Unit test on a messy fixture file | Unknown speaker labels become their own `Unknown` turn and are counted as unparsed | `test_messy_file_keeps_text_and_counts_bad_lines` |
| 2 | `"It's B C …"` was read as the ID prefix `S-B-C`, giving `BCBC-774192` and `SCLM-291446` | Running the reference extractor on all 10 calls | Strip contractions before tokenising; collapse a repeated prefix; ignore a lone "a"/"I" | `test_spoken_ids_are_extracted_by_code_only_near_case_words` |
| 3 | `canonical_reference` did not convert number words, so v2 stored `ESCSEVENEIGHTONETWO` while marking it verified | Investigating why an obviously wrong ID was "verified" | Normalise number words before formatting | `test_canonical_reference_format` |
| 4 | Redaction produced "Mr. the customer" | Manual review of the final records | Remove titles with surnames before bare names; clean up leftovers | `test_redaction_leaves_clean_text` |
| 5 | Redaction produced "their the card on file" | Manual review of the final records | Card pattern includes the word before it | `test_redaction_leaves_clean_text` |
| 6 | The model sometimes wrote the text `"null"` as a due date | Reading v3 output | `rules.normalise_due` turns text nulls into real nulls | `test_text_null_due_dates_become_real_nulls` |

## Environment and setup issues

| # | Problem | How it was found | Fix |
|---|---|---|---|
| 7 | Ollama on a Mac uses the GPU by default, which breaks the CPU-only rule | Known Ollama behaviour; checked in the server log | `num_gpu: 0` on every request; log shows `offloaded 0/37 layers to GPU`, `ollama ps` shows `100% CPU` |
| 8 | Ollama's runner keeps a prompt cache in RAM of up to 8 GB by default, so a long nightly run could exceed 4 GB | Reading the server log (`limits: 8192 MiB`) | Start the server with `LLAMA_ARG_CACHE_RAM=1024`; confirmed `limits: 1024.000 MiB`; peak measured 2.13 GB |
| 9 | Pinned `pydantic==2.14.4` does not install on Python 3.9, so the README's "3.9+" claim was false | Running the tests in a Python 3.9 virtual environment | Tested version ranges; tests pass on 3.9 and 3.15 |
| 10 | The run log folder did not exist, so the first baseline run failed to start | The run exited immediately | Create the folder first |
| 11 | Exporting slides to PDF from PowerPoint by script failed (PowerPoint's sandbox) | Error -9074 and a hang | LibreOffice (headless) instead, installed to `~/Applications` because the session could not write to `/Applications` |
| 12 | The write-up PDF ran to 2 pages; the brief allows one | Rendering the PDF | Cut wording; render headings as bold paragraphs |
| 13 | Slide titles wrapped onto content; a table header wrapped | Visual check of rendered slides | Shorter titles; wider table columns |

## Mistakes in documentation and claims (all corrected)

| # | Wrong claim | Correct version | How it was caught |
|---|---|---|---|
| 14 | "Call 001's postal code is a conflict (500014 vs 50014)" | "Five double zero one four" = 50014, matching the read-back | Re-reading the digits while writing the labels |
| 15 | "v1 invented repeat_contact in 8 of 10 calls" | 10 of 10 | Counting from the saved v1 records |
| 16 | Finding: "a 6-year customer left" (008) | The customer said they *may* check other carriers | Re-reading the transcript |
| 17 | Finding cited call 005's "last time … nothing came" as distrust of this company | That remark is about another company; replaced with 002 and 009 | Re-reading the transcript |
| 18 | "Ran with Wi-Fi off" | Not done; replaced by a real test: the final run inside a sandbox that blocks all non-local network | Checking the claim before publishing |
| 19 | AI-usage rows describing AI mistakes that never happened (e.g. "suggested real calls as examples") | Rewritten to what actually happened | Re-reading the log against the history |
| 20 | "Runs are deterministic" | Categorical fields were identical in 3 runs; free-text wording varied | Comparing a third run field by field |
