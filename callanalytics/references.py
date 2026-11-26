"""Find case reference numbers in a transcript with code, not the model.

Speech-to-text writes IDs as spoken letters and digits: "R-F-two-two-zero-six-eight",
"C L M, dash, two nine one, dash, four four six". A 3B model often fails to turn these into
"RF-22068" (v2 produced "ESCSEVENEIGHTONETWO"), so a small tokeniser does it instead.

An ID is 1-4 spoken letters followed by 3+ digits, in a turn that (or whose previous turn)
mentions a case word such as "claim", "ticket" or "order". Phone and card numbers have no letter
prefix, so they are never picked up.
"""

import re
from typing import List, Tuple

from .grounding import canonical_reference

_DIGIT_WORDS = {"zero": "0", "oh": "0", "o": "0", "one": "1", "two": "2", "three": "3", "four": "4",
                "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"}
_FILLER = {"dash", "hyphen", "uh", "um", "hmm", "er"}
_REPEAT = {"double": 2, "triple": 3}
# first match wins, so the more specific words come first
_TYPE_WORDS = [("escalation", "escalation"), ("ticket", "ticket"), ("refund", "refund"), ("claim", "claim"),
               ("order", "order"), ("policy", "policy"), ("reference", "other"), ("case", "other")]


def _tokens(text: str) -> List[str]:
    out, repeat = [], 1
    text = re.sub(r"['\u2019][a-z]+", "", text.lower())  # "it's B C" -> "it B C", not the letter S
    for w in re.findall(r"[a-z0-9]+", text):
        if w in _FILLER:
            continue
        if w in _REPEAT:
            repeat = _REPEAT[w]
            continue
        if w in _DIGIT_WORDS:
            out.extend([_DIGIT_WORDS[w]] * repeat)
        elif w.isdigit():
            out.append(w)
        else:
            out.append(w)
        repeat = 1
    return out


def _collapse_repeat(letters: str) -> str:
    """'BCBC' (customer said the prefix twice) -> 'BC'."""
    half = len(letters) // 2
    if len(letters) % 2 == 0 and half and letters[:half] == letters[half:]:
        return letters[:half]
    return letters


def ids_in_text(text: str) -> List[str]:
    toks, found, i = _tokens(text), [], 0
    while i < len(toks):
        j = i
        while j < len(toks) and len(toks[j]) == 1 and toks[j].isalpha():
            j += 1
        letters = "".join(toks[i:j])
        k = j
        while k < len(toks) and toks[k].isdigit():
            k += 1
        digits = "".join(toks[j:k])
        lone_word = letters in ("a", "i")  # the article or pronoun, not an ID prefix
        if 1 <= len(letters) <= 8 and len(digits) >= 3 and not lone_word:
            letters = _collapse_repeat(letters)[-4:]
            found.append(canonical_reference(letters.upper() + digits))
            i = k
        else:
            i = max(j, i + 1)
    return found


def _type_of(text: str) -> str:
    low = text.lower()
    for word, kind in _TYPE_WORDS:
        if word in low:
            return kind
    return ""


def extract_references(turns) -> List[Tuple[str, str]]:
    """Return [(type, value)] in order of first mention, without duplicates."""
    result, seen = [], set()
    for n, turn in enumerate(turns):
        kind = _type_of(turn.text) or (_type_of(turns[n - 1].text) if n else "")
        if not kind:
            continue
        for value in ids_in_text(turn.text):
            if value not in seen:
                seen.add(value)
                result.append((kind, value))
    return result
