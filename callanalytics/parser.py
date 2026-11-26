"""Read a transcript file into speaker turns. Pure code, no model."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SPEAKERS = ("System", "Agent", "Customer")
_TURN_RE = re.compile(r"^\s*(system|agent|customer)\s*:\s*(.*)$", re.IGNORECASE)
_OTHER_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{0,24}:\s")  # a speaker label we do not expect
# "on behalf of Skyline Broadband." -> "Skyline Broadband"; department words are dropped.
_BRAND_RE = re.compile(
    r"on behalf of\s+(.+?)(?:\s+(?:technical support|customer care|customer service|support|billing|sales))?\s*[.,;!]",
    re.IGNORECASE,
)


@dataclass
class Turn:
    index: int  # 1-based, as shown to the model
    speaker: str  # System | Agent | Customer
    text: str


@dataclass
class Transcript:
    call_id: str
    turns: List[Turn]
    unparsed_lines: int = 0  # lines that were not "Speaker: text" (kept as continuation text)
    decode_errors: bool = False
    brand: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def count(self, speaker: str) -> int:
        return sum(1 for t in self.turns if t.speaker == speaker)

    def render(self, turns: Optional[List[Turn]] = None) -> str:
        """Numbered lines for the model: '[3] Customer: ...'."""
        return "\n".join(f"[{t.index}] {t.speaker}: {t.text}" for t in (turns or self.turns))


def parse_text(call_id: str, text: str, decode_errors: bool = False) -> Transcript:
    turns: List[Turn] = []
    unparsed = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _TURN_RE.match(line)
        if m:
            speaker = m.group(1).capitalize()
            turns.append(Turn(index=len(turns) + 1, speaker=speaker, text=m.group(2).strip()))
        elif _OTHER_LABEL_RE.match(line):  # e.g. "Supervisor: ..." - never credit it to the customer
            unparsed += 1
            turns.append(Turn(index=len(turns) + 1, speaker="Unknown", text=line))
        else:
            unparsed += 1
            if turns:  # a wrapped line: keep the words, attach to the previous turn
                turns[-1].text = f"{turns[-1].text} {line}".strip()
            else:  # text before any speaker label: keep it as an unknown turn
                turns.append(Turn(index=1, speaker="Unknown", text=line))

    transcript = Transcript(call_id=call_id, turns=turns, unparsed_lines=unparsed, decode_errors=decode_errors)
    transcript.brand = _find_brand(turns)
    if unparsed:
        transcript.warnings.append(f"{unparsed} line(s) not in 'Speaker: text' format")
    if decode_errors:
        transcript.warnings.append("file contained bytes that are not valid UTF-8")
    return transcript


def parse_file(path: Path) -> Transcript:
    data = path.read_bytes()
    try:
        text, bad = data.decode("utf-8-sig"), False
    except UnicodeDecodeError:
        text, bad = data.decode("utf-8", errors="replace"), True
    return parse_text(path.stem, text, decode_errors=bad)


def _find_brand(turns: List[Turn]) -> Optional[str]:
    for turn in turns:
        if turn.speaker == "System":
            m = _BRAND_RE.search(turn.text)
            if m:
                return m.group(1).strip()
    return None
