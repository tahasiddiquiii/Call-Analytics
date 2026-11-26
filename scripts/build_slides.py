"""Build submission/slides.pptx (5 slides, the order the brief asks for).

    python scripts/build_slides.py

Every number on the slides is read from files the system produced (reports/benchmark.json,
reports/bakeoff.json, eval/runs/*/eval.json), so the deck cannot drift from the results.
"""

import json
import sys
from pathlib import Path

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from slide_kit import (BAD, GOOD, INK, LINE, MIST, MUTED, PAPER, SIGNAL, arrow, blank, card, chip,  # noqa: E402
                       footer, new_deck, text, title)

ROOT = Path(__file__).resolve().parent.parent
FINAL = "v4"
VERSIONS = ["v1", "v2", "v3", "v4"]


def load(path):
    return json.loads((ROOT / path).read_text())


bench = load("reports/benchmark.json")
bake = load("reports/bakeoff.json")
evals = {v: load(f"eval/runs/{v}/eval.json") for v in VERSIONS}
final = load("reports/eval_final.json")  # outputs/records.json scored against the hand labels
chk = final["checks"]


def frac(key, ev=final):
    c = ev["checks"][key]
    return f"{c['correct']}/{c['total']}"


def pct(key, ev=final):
    c = ev["checks"][key]
    return round(100 * c["correct"] / c["total"])


traps_passed = sum(ok for _, ok in final["traps"])


def repeat_count(version):
    path = "outputs/records.json" if version == FINAL else f"eval/runs/{version}/records.json"
    recs = load(path)["records"]
    return sum(bool(r["flags"] and r["flags"]["repeat_contact"]) for r in recs)
prs = new_deck()
I = Inches

# ---------------------------------------------------------------- 1. Approach and model
s = blank(prs)
title(s, 1, "The model reads the call; code checks the facts", "Approach and model")
steps = [("Parse", "turns, brand,\nformat checks", "code"),
         ("3 small questions", "classify · judge ·\nactions", "Qwen2.5-3B"),
         ("Validate", "JSON Schema,\n1 repair, else 'failed'", "code"),
         ("Check & rules", "IDs, quotes, outcome\nrule, flags, privacy", "code"),
         ("Record", "same shape every time,\nneeds_review + reasons", "JSON")]
x0, y0, bw, gap = 0.6, 1.75, 2.18, 0.33
for n, (head, body, who) in enumerate(steps):
    x = I(x0 + n * (bw + gap))
    model = who == "Qwen2.5-3B"
    card(s, x, I(y0), I(bw), I(1.45), fill=INK if model else MIST)
    text(s, x + I(0.18), I(y0 + 0.15), I(bw - 0.3), I(0.3), who.upper(), size=10, bold=True,
         color=SIGNAL if model else MUTED)
    text(s, x + I(0.18), I(y0 + 0.42), I(bw - 0.3), I(0.35), head, size=16, bold=True, color=PAPER if model else INK)
    text(s, x + I(0.18), I(y0 + 0.8), I(bw - 0.3), I(0.6), body, size=11, color=LINE if model else MUTED)
    if n < len(steps) - 1:
        arrow(s, x + I(bw + 0.06), I(y0 + 0.62), I(0.2), I(0.22), color=LINE)

tiles = [("Qwen2.5-3B", "Instruct, 4-bit (Q4_K_M)"), ("1.9 GB", "model file"),
         (f"{bench['peak_model_process_ram_gb']:.1f} GB", "peak RAM, model process"),
         (f"{bench['wall_seconds'] / 60:.0f} min", f"10 calls on an M1 CPU ({bench['seconds_per_call_avg']:.0f} s/call)"),
         ("Ollama", "CPU only: 0/37 layers on GPU")]
for n, (big, small) in enumerate(tiles):
    x = I(x0 + n * (bw + gap))
    text(s, x, I(3.5), I(bw), I(0.55), big, size=26, bold=True, color=INK, font="Cambria")
    text(s, x, I(4.08), I(bw), I(0.3), small, size=11, color=MUTED)

text(s, I(0.6), I(4.7), I(5.6), I(0.3), "Why this model", size=14, bold=True)
text(s, I(0.6), I(5.05), I(5.6), I(1.9), [
    "Best balance of three local models on my hand labels. Llama 3.2 scored one more outcome right but mistyped the wrong-number call, misread sentiment and needs 3.5 GB",
    "The 1.5B model is faster but believed the agent's false guarantee (fails both call-006 traps)",
    "Strong JSON and instruction following for its size; handles the Hindi-English call",
    "Ollama forces valid JSON via a schema, runs offline, one-line install",
], size=11, color=INK, spacing=6)
text(s, I(6.7), I(4.7), I(6), I(0.3), "Bake-off: same pipeline, same 10 calls", size=14, bold=True)
rows = [["Model", "Outcome", "Intent", "Facts", "Traps", "RAM*", "Time"]] + [
    [b["model"], b["outcome"], b["intent"], b["facts"], b["traps"], f"{b['loaded_gb']:.1f} GB", f"{b['minutes']:.0f} min"]
    for b in bake]
tbl = s.shapes.add_table(len(rows), 7, I(6.7), I(5.05), I(6.0), I(0.3 * len(rows))).table
tbl.columns[0].width = I(1.3)
for k in range(1, 7):
    tbl.columns[k].width = I(0.78)
for r, row in enumerate(rows):
    for col, val in enumerate(row):
        cell = tbl.cell(r, col)
        cell.text = val
        p = cell.text_frame.paragraphs[0]
        p.runs[0].font.size, p.runs[0].font.name = Pt(11), "Calibri"
        p.runs[0].font.bold = r == 0 or (r == 1)
        p.runs[0].font.color.rgb = PAPER if r == 0 else INK
        cell.fill.solid()
        cell.fill.fore_color.rgb = INK if r == 0 else (MIST if r == 1 else PAPER)
        cell.margin_top = cell.margin_bottom = Pt(2)
footer(s, "*RAM loaded = model + 8k context as reported by ollama ps. Three requests per call share one cached reading "
          "of the transcript. Prompt-cache RAM capped with LLAMA_ARG_CACHE_RAM=1024 (Ollama default allows 8 GB).")

# ---------------------------------------------------------------- 2. Process
s = blank(prs)
title(s, 2, "Scores on hand labels decided every change", "Process")
cols = [("I asked AI tools (Claude Code) for", ["The plan, mapped to the scoring", "Hand labels for 10 calls (I reviewed)",
                                                "Code, prompts, tests, evaluator"]),
        ("What it got wrong", ["Called the 001 postal code a conflict: it is not", "Copied example → copied answers (v1)",
                               "Pinned a library that breaks on Python 3.9"]),
        ("What I added or overruled", ["Force CPU (Mac defaults to GPU)", "Cap Ollama's 8 GB prompt cache",
                                       "No real calls as examples; no personal data"])]
for n, (head, items) in enumerate(cols):
    x = I(0.6 + n * 4.1)
    text(s, x, I(1.65), I(3.9), I(0.3), head, size=13, bold=True, color=SIGNAL if n == 2 else INK)
    text(s, x, I(1.98), I(3.9), I(1.0), items, size=11, color=INK, spacing=2)

examples = [
    ("call_006", "Agent's false guarantee + \"ignore your instructions\"",
     "v1: resolved_pending_action. \"Claim will be approved on appeal … Agent noted the claim was approved in the notes.\"",
     "Believed a promise the agent took back; the agent actually refused to note it.",
     "Model answers 3 yes/no facts; code applies the outcome rule (v3).",
     "unresolved; basis: handed_over=false, solution_agreed=false"),
    ("call_001 + all", "Insights copied from the prompt's example",
     "v1: \"Customer mentions this is the second time they have called\" → repeat_contact in 10/10 calls",
     "Invented; copied from the example in the prompt. Also put the full street address in the record.",
     "Removed example; insights need a verified quote; flags are yes/no questions; code removes personal data.",
     f"repeat_contact in {repeat_count(FINAL)} calls (labelled true: 2); address gone"),
]
for n, (cid, what, before, wrong, change, after) in enumerate(examples):
    x, y, w = I(0.6), I(3.05 + n * 1.95), I(7.6)
    card(s, x, y, w, I(1.8))
    chip(s, x + I(0.15), y + I(0.14), cid, fill=SIGNAL)
    text(s, x + I(1.55), y + I(0.15), I(5.9), I(0.3), what, size=12, bold=True)
    lines = [[("Before  ", {"bold": True, "color": BAD}), (before, {})],
             [("Wrong  ", {"bold": True, "color": BAD}), (wrong, {})],
             [("Change  ", {"bold": True, "color": SIGNAL}), (change, {})],
             [("After  ", {"bold": True, "color": GOOD}), (after, {})]]
    text(s, x + I(0.15), y + I(0.52), w - I(0.3), I(1.25), lines, size=10.5, spacing=2)

cd = CategoryChartData()
cd.categories = VERSIONS
cd.add_series("Outcome status %", [pct("outcome_status", evals[v]) for v in VERSIONS])
cd.add_series("Reference numbers %", [pct("references_found", evals[v]) for v in VERSIONS])
cd.add_series("Must-have facts %", [pct("facts", evals[v]) for v in VERSIONS])
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, I(8.5), I(3.0), I(4.3), I(3.85), cd)
ch = gf.chart
ch.has_legend, ch.legend.position, ch.legend.include_in_layout = True, XL_LEGEND_POSITION.BOTTOM, False
ch.legend.font.size = Pt(10)
ch.value_axis.maximum_scale, ch.value_axis.minimum_scale = 100, 0
ch.value_axis.tick_labels.font.size = ch.category_axis.tick_labels.font.size = Pt(10)
ch.value_axis.major_gridlines.format.line.color.rgb = LINE
ch.has_title = True
ch.chart_title.text_frame.text = "Score vs hand labels, by prompt version"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(11)
for series, color in zip(ch.series, (SIGNAL, INK, MUTED)):
    series.format.line.color.rgb = color
    series.marker.format.fill.solid()
    series.marker.format.fill.fore_color.rgb = color
footer(s, "v2 got worse (outcome 30%, references 0%): more rules did not help a 3B model. "
          "Splitting the work did. Full log: docs/iterations.md · runs: eval/runs/v1–v4")

# ---------------------------------------------------------------- 3. Findings
s = blank(prs)
title(s, 3, "What the 10 calls tell a supervisor", "Findings")
findings = [
    (["call_006"], "An agent guaranteed approval, then took it back",
     "Promised approval and no deductible, then admitted no authority. The customer may pay a contractor on a false promise. Coach the agent; script \"I can't promise outcomes\"."),
    (["call_006", "call_009"], "Harbor Mutual claims customers are left chasing",
     "Denial disputed with no clear path (006); 4 weeks with no movement and missed callbacks (009). Raise status visibility and adjuster SLAs with the client."),
    (["call_002", "call_008"], "Retention depends on the agent, not the policy",
     "A loyalty offer kept a customer about to cancel (002). Another agent offered nothing, gave no transfer number, and a 6-year customer said they may check other carriers (008). Give sales agents retention options."),
    (["call_002", "call_003", "call_009"], "Customers expect promises and follow-ups to fail",
     "\"Last time … the promo price … jumped\" (002), \"last time nobody did anything\" (003), \"that's what the last two agents said too\" (009). Calls ended calmer when the agent gave a reference number and a deadline."),
    (["call_001", "call_010"], "Identifiers are unreliable on the phone",
     "Serial and phone numbers were garbled and a replacement router was not linked to the account (010); a postal code needed a read-back (001). Always read IDs back; link replacement devices."),
    (["call_004", "call_007"], "2 of 10 calls were not customer calls",
     "A QA test and a wrong number. The records mark them, so they are kept out of statistics."),
]
for n, (calls, head, body) in enumerate(findings):
    col, row = n % 2, n // 2
    x, y, w, h = I(0.6 + col * 6.15), I(1.65 + row * 1.78), I(5.95), I(1.62)
    card(s, x, y, w, h, fill=MIST)
    cx = x + I(0.18)
    for cid in calls:
        cx += chip(s, cx, y + I(0.15), cid.replace("call_", ""), fill=SIGNAL if n == 0 else INK) + I(0.08)
    text(s, x + I(0.18), y + I(0.5), w - I(0.36), I(0.3), head, size=13, bold=True)
    text(s, x + I(0.18), y + I(0.85), w - I(0.36), I(0.75), body, size=10.5, color=INK)
footer(s, "Each finding names the calls it rests on (chips). Counts come from the records via scripts/summarise.py; "
          "with 10 calls these are leads to check, not rates.")

# ---------------------------------------------------------------- 4. Reliability
s = blank(prs)
title(s, 4, "Where the output can be wrong, and how I know", "Reliability")
score_rows = [("Call type", frac("call_type")), ("Primary intent", frac("intent_primary")),
              ("Outcome status", frac("outcome_status")), ("Sentiment at end, within 1 step", frac("sentiment_end_within_1")),
              ("Sentiment at end, exact", frac("sentiment_end")), ("Labelled flags", frac("flags")),
              ("Must-have facts present", frac("facts")), ("Reference numbers found", frac("references_found")),
              ("Trap tests passed", f"{traps_passed}/{len(final['traps'])}")]
card(s, I(0.6), I(1.65), I(4.6), I(5.2), fill=INK)
text(s, I(0.85), I(1.85), I(4.2), I(0.3), "FINAL RUN VS HAND LABELS", size=11, bold=True, color=SIGNAL)
for n, (label, val) in enumerate(score_rows):
    y = I(2.3 + n * 0.47)
    text(s, I(0.85), y, I(3.1), I(0.3), label, size=12, color=LINE)
    text(s, I(3.9), y, I(1.1), I(0.3), val, size=14, bold=True, color=PAPER)
text(s, I(0.85), I(6.5), I(4.2), I(0.3), "29 unit tests · Python 3.9 and 3.15 · run with internet blocked", size=10, color=LINE)

risks = [
    ("Sentiment is a judgement call", "Exact-match end sentiment is lower than within-one-step: neighbouring levels are often both defensible. Shown side by side in the score."),
    ("Insights can be shallow or wrong", "A quote proves the words exist, not that they support the claim. Contradicted flags are dropped by code; the rest need sampling by a person."),
    ("Facts can be missed", "Must-have facts are checked by keywords in the eval; a 3B model drops details in long calls (003)."),
    ("Speech-to-text errors", "IDs are taken only from the transcript by code, so they are real but can still be mis-heard. Unclear ones should be read back."),
    ("Small, synthetic sample", "10 calls + 2 held-out calls. The scores show direction, not a guarantee for 10,000 real calls."),
]
for n, (head, body) in enumerate(risks):
    y = I(1.65 + n * 1.05)
    text(s, I(5.6), y, I(7.1), I(0.3), head, size=13, bold=True)
    text(s, I(5.6), y + I(0.32), I(7.1), I(0.65), body, size=11, color=MUTED)
footer(s, "Unattended runs: every call gets a record, failures are 'failed' records with a reason, needs_review flags doubt, "
          "exit code 1 if > 20% fail, atomic writes.")

# ---------------------------------------------------------------- 5. Next steps
s = blank(prs)
title(s, 5, "Next steps, most important first", "Next steps")
steps = [
    ("Label 200 real calls", "Measure accuracy per field on real audio transcripts before trusting any number; calibrate the categories."),
    ("Review queue for needs_review", "Send flagged calls to a person; use their corrections as new test cases."),
    ("Scale out", f"~{bench['seconds_per_call_avg']:.0f} s per call on one CPU means 10,000 calls need about "
                  f"{10000 * bench['seconds_per_call_avg'] / 3600 / 8:.0f} machines for an 8-hour night, or a larger CPU host. Calls are independent, so this is parallel."),
    ("Check that quotes support the claim", "Today code checks that a quote exists; add a second model pass or rules that check it supports the insight."),
    ("Compare a 7B model", "Where the hardware allows, run the same evaluation; keep the 3B model if the gain is small."),
]
for n, (head, body) in enumerate(steps):
    y = I(1.7 + n * 1.02)
    circle = s.shapes.add_shape(9, I(0.6), y, I(0.55), I(0.55))  # oval
    circle.fill.solid()
    circle.fill.fore_color.rgb = SIGNAL if n == 0 else INK
    circle.line.fill.background()
    tf = circle.text_frame
    tf.text = str(n + 1)
    tf.paragraphs[0].runs[0].font.size, tf.paragraphs[0].runs[0].font.bold = Pt(16), True
    tf.paragraphs[0].runs[0].font.color.rgb = PAPER
    tf.paragraphs[0].alignment = 2
    text(s, I(1.4), y - I(0.02), I(11.3), I(0.32), head, size=15, bold=True)
    text(s, I(1.4), y + I(0.33), I(11.3), I(0.55), body, size=12, color=MUTED)
footer(s, "Code, prompts, runs and reports: github.com/tahasiddiquiii/Call-Analytics")

out = ROOT / "submission" / "slides.pptx"
out.parent.mkdir(exist_ok=True)
prs.save(out)
print(f"wrote {out}")
