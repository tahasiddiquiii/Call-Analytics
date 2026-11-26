"""Remove personal data from the record's free-text fields, with code.

The prompt already tells the model not to copy personal data, but v1 and v2 still wrote a street
address, card digits and "Mr. Pruitt" into the record. Because other software reads the records
unchecked, the last line of defence is deterministic: the model names the customer (only so the
name can be removed) and code strips it, plus titles with surnames, emails, card digits and long
numbers. Street addresses have no reliable pattern; they rely on the prompt and are measured by
the evaluator.
"""

import re
from typing import List, Optional, Tuple

_SPOKEN_EMAIL = r"\b\w+(?: dot \w+)* at \w+ dot (?:com|org|net|in)\b"
_PATTERNS = [
    (re.compile(r"\b(?:Mr|Mrs|Ms|Miss)\.? [A-Z][a-z]+\b"), "the customer"),
    (re.compile(rf"\b[\w.+-]+@[\w-]+\.[\w.]+\b|{_SPOKEN_EMAIL}", re.I), "[email removed]"),
    (re.compile(r"\b(?:card|visa|mastercard)(?: ending)?(?: in)? \d{4}\b", re.I), "the card on file"),
    (re.compile(r"(?<![A-Za-z-])\b(?:\d[\s-]?){7,}\b"), "[number removed]"),  # not case IDs like HM-4492017
]


def _name_patterns(customer_name: Optional[str]) -> List[re.Pattern]:
    if not customer_name or not customer_name.strip():
        return []
    parts = [p for p in re.split(r"\s+", customer_name.strip()) if len(p) >= 3]
    pats = [re.compile(rf"\b{re.escape(customer_name.strip())}\b", re.I)]
    pats += [re.compile(rf"\b{re.escape(p)}\b") for p in parts]
    return pats


def redact(text: str, customer_name: Optional[str] = None) -> Tuple[str, int]:
    """Return (clean text, number of replacements)."""
    count = 0
    for pattern, repl in [(p, "the customer") for p in _name_patterns(customer_name)] + _PATTERNS:
        text, n = pattern.subn(repl, text)
        count += n
    text = re.sub(r"\bthe customer's? the customer\b", "the customer", text, flags=re.I)
    if text.startswith("the customer"):
        text = "T" + text[1:]
    return text, count
