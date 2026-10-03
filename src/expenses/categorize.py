"""Keyword-based categorisation.

Rules live in :mod:`expenses.config`; this module compiles them into
word-boundary regular expressions so short keywords (``esb``, ``eir``, ``bar``)
don't match inside unrelated words. The first matching category wins.
"""

from __future__ import annotations

import re

from .config import CATEGORY_RULES, UNCATEGORIZED

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        category,
        re.compile(
            r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b",
            re.IGNORECASE,
        ),
    )
    for category, keywords in CATEGORY_RULES
]


def categorize(description: str) -> str:
    """Return the category for *description*, or ``Uncategorized``."""
    text = " ".join((description or "").split())
    if not text:
        return UNCATEGORIZED
    for category, pattern in _PATTERNS:
        if pattern.search(text):
            return category
    return UNCATEGORIZED
