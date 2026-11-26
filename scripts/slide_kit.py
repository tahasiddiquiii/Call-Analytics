"""Small drawing helpers for the slide deck (python-pptx). Kept separate so build_slides.py reads as content."""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

INK = RGBColor(0x13, 0x1B, 0x2E)  # dominant dark
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
MIST = RGBColor(0xEE, 0xF1, 0xF6)  # card background
LINE = RGBColor(0xD5, 0xDB, 0xE5)
MUTED = RGBColor(0x5B, 0x66, 0x7A)
SIGNAL = RGBColor(0xF2, 0x8C, 0x28)  # accent: the "supervisor's attention" colour
GOOD = RGBColor(0x1F, 0x8A, 0x5B)
BAD = RGBColor(0xC2, 0x3B, 0x3B)
FONT = "Calibri"
HEAD = "Cambria"

W, H = Inches(13.333), Inches(7.5)


def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    return prs


def blank(prs, dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = INK if dark else PAPER
    return slide


def text(slide, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT,
         font=FONT, anchor=MSO_ANCHOR.TOP, spacing=4, name=None):
    """runs: a string, or a list of paragraphs; each paragraph a string or list of (text, {opts})."""
    box = slide.shapes.add_textbox(x, y, w, h)
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(spacing)
        for chunk, opts in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = chunk
            f = r.font
            f.name = opts.get("font", font)
            f.size = Pt(opts.get("size", size))
            f.bold = opts.get("bold", bold)
            f.italic = opts.get("italic", False)
            f.color.rgb = opts.get("color", color)
    return box


def card(slide, x, y, w, h, fill=MIST, line=None, radius=0.06, name=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.adjustments[0] = radius
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    if name:
        shape.name = name
    return shape


def chip(slide, x, y, label, fill=INK, color=PAPER, size=11, w=None):
    """A small rounded tag, e.g. a call ID. Returns its width so chips can be laid out in a row."""
    width = w or Inches(0.13 + 0.085 * len(label) * size / 11)
    shape = card(slide, x, y, width, Inches(0.3 * size / 11), fill=fill, radius=0.5)
    tf = shape.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), True, color
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return width


def arrow(slide, x, y, w, h, color=MUTED):
    shape = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def title(slide, number, heading, kicker, dark=False):
    """Same position, font and size on every slide."""
    fg = PAPER if dark else INK
    text(slide, Inches(0.6), Inches(0.38), Inches(9), Inches(0.3),
         [[(f"{number:02d}  ", {"color": SIGNAL, "bold": True}), (kicker.upper(), {"color": MUTED if not dark else LINE})]],
         size=12, bold=True)
    text(slide, Inches(0.6), Inches(0.68), Inches(12.1), Inches(0.8), heading, size=34, bold=True, color=fg, font=HEAD)


def footer(slide, label, dark=False):
    text(slide, Inches(0.6), Inches(7.05), Inches(12.1), Inches(0.25), label, size=10,
         color=LINE if dark else MUTED)
