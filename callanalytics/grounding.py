"""Check the model's claims against the transcript.

Speech-to-text writes IDs as words ("R-F-two-two-zero-six-eight"), while the model writes them as
"RF-22068". To compare them we turn both into a compact form: number words become digits,
separators and filler words are dropped, everything is lower case.
"""

import re
from typing import Iterable

_DIGITS = {
    "zero": "0", "oh": "0", "o": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}
_REPEAT = {"double": 2, "triple": 3}
_FILLER = {"dash", "hyphen", "uh", "um", "hmm", "er", "space"}
_WORD_RE = re.compile(r"[a-z0-9]+")


def compact(text: str) -> str:
    """'C L M, dash, two nine one' -> 'clm291'.  'five double zero' -> '500'."""
    words = _WORD_RE.findall(text.lower())
    out = []
    repeat = 1
    for w in words:
        if w in _REPEAT:
            repeat = _REPEAT[w]
            continue
        if w in _FILLER:
            continue
        token = _DIGITS.get(w, w)
        out.append(token * repeat if len(token) == 1 else token)
        repeat = 1
    return "".join(out)


def normalise_words(text: str) -> str:
    """Lower case, punctuation removed, single spaces. Used for quote matching."""
    return " ".join(_WORD_RE.findall(text.lower().replace("'", "")))


def reference_in_transcript(value: str, turn_texts: Iterable[str]) -> bool:
    needle = compact(value)
    if len(needle) < 3:
        return False
    return needle in compact(" ".join(turn_texts))


def quote_in_transcript(quote: str, turn_texts: Iterable[str]) -> bool:
    needle = normalise_words(quote)
    if not needle:
        return False
    return any(needle in normalise_words(t) for t in turn_texts)


_REF_RE = re.compile(r"^([A-Z]+)([0-9][0-9A-Z]*)$")


def canonical_reference(value: str) -> str:
    """One format for every case number, so software can match them: 'R-F-22068' -> 'RF-22068'."""
    flat = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    m = _REF_RE.match(flat)
    return f"{m.group(1)}-{m.group(2)}" if m else (flat or value.strip())


def find_quote_turn(quote: str, turns) -> int:
    """Return the 1-based turn that contains the quote, or 0 if none does."""
    needle = normalise_words(quote)
    for t in turns:
        if needle and needle in normalise_words(t.text):
            return t.index
    return 0
