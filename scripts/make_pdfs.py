"""Convert submission/slides.pptx and submission/writeup.md to PDF with LibreOffice (headless).

    python scripts/make_pdfs.py

Needs LibreOffice (`brew install --cask libreoffice`). Set SOFFICE to its path if it is not found.
The write-up is turned into simple HTML first (headings, lists, bold, code) so it prints as one page.
"""

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = ROOT / "submission"
CANDIDATES = [os.environ.get("SOFFICE", ""), shutil.which("soffice") or "",
              str(Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice"),
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"]

CSS = """
@page { size: A4; margin: 13mm 15mm; }
body { font-family: Calibri, Carlito, Arial, sans-serif; font-size: 9.2pt; line-height: 1.28; color: #131B2E; }
h1 { font-family: Cambria, Caladea, serif; font-size: 15pt; margin: 0 0 4pt 0; }
h2 { font-size: 10.2pt; margin: 7pt 0 2pt 0; color: #131B2E; border-bottom: 0.6pt solid #D5DBE5; }
p, li { margin: 0 0 2pt 0; }
ul, ol { margin: 0 0 2pt 0; padding-left: 13pt; }
code { font-family: Menlo, Courier New, monospace; font-size: 8.3pt; }
"""


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)


def md_to_html(md: str) -> str:
    out, lst = [], None
    for line in md.splitlines():
        m_ul, m_ol = re.match(r"^- (.*)", line), re.match(r"^\d+\. (.*)", line)
        kind = "ul" if m_ul else "ol" if m_ol else None
        if lst and kind != lst:
            out.append(f"</{lst}>")
            lst = None
        if kind and not lst:
            out.append(f"<{kind}>")
            lst = kind
        if kind:
            out.append(f"<li>{inline((m_ul or m_ol).group(1))}</li>")
        elif line.startswith("## "):  # bold paragraph: LibreOffice's heading styles add too much space
            out.append(f"<p style='margin-top:5pt'><b><font size='3' color='#131B2E'>{inline(line[3:])}</font></b></p>")
        elif line.startswith("# "):
            out.append(f"<p><b><font size='5' face='Cambria'>{inline(line[2:])}</font></b></p>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    if lst:
        out.append(f"</{lst}>")
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(out)}</body></html>"


def convert(soffice: str, src: Path, filt: str, profile: str) -> None:
    subprocess.run([soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", filt,
                    "--outdir", str(SUB), str(src)], check=True, capture_output=True)


def main() -> int:
    soffice = next((c for c in CANDIDATES if c and Path(c).exists()), None)
    if not soffice:
        print("LibreOffice not found; set SOFFICE=/path/to/soffice", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        convert(soffice, SUB / "slides.pptx", "pdf", f"{tmp}/profile")
        page = Path(tmp) / "writeup.html"
        page.write_text(md_to_html((SUB / "writeup.md").read_text()), encoding="utf-8")
        convert(soffice, page, "pdf:writer_web_pdf_Export", f"{tmp}/profile")
    print("wrote", SUB / "slides.pdf", "and", SUB / "writeup.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
