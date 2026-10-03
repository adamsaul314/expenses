"""Turn raw Revolut rows into typed transactions.

Amounts are parsed as :class:`decimal.Decimal` and tolerate the common European
and UK/Irish spellings (``1,234.56`` and ``1.234,56``), currency symbols,
currency codes and accounting-style negatives such as ``(12.34)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Iterator, Optional

from .config import COMPLETED_STATES, UNCATEGORIZED


class ParseError(ValueError):
    """Raised when a value cannot be parsed."""


@dataclass
class Transaction:
    """A single normalised statement line."""

    description: str
    amount: Decimal
    fee: Decimal = Decimal("0")
    currency: str = "EUR"
    state: str = ""
    type: str = ""
    product: str = ""
    completed: Optional[date] = None
    started: Optional[date] = None
    category: str = UNCATEGORIZED

    @property
    def is_outflow(self) -> bool:
        return self.amount < 0

    @property
    def spend(self) -> Decimal:
        """Positive magnitude of an outflow (``0`` for inflows)."""
        return -self.amount if self.amount < 0 else Decimal("0")

    @property
    def is_completed(self) -> bool:
        return self.state.strip().lower() in COMPLETED_STATES


_AMOUNT_CLEAN = re.compile(r"[^0-9,.\-+]")

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


def parse_amount(raw) -> Decimal:
    """Parse a Euro amount from a statement cell."""
    if raw is None:
        raise ParseError("amount is missing")
    text = str(raw).strip()
    if not text:
        raise ParseError("amount is empty")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    text = (
        text.replace("\u00a0", "")
        .replace("\u202f", "")
        .replace(" ", "")
    )
    text = _AMOUNT_CLEAN.sub("", text)

    sign = 1
    if text.startswith("-"):
        sign = -1
        text = text[1:]
    elif text.startswith("+"):
        text = text[1:]
    text = text.replace("-", "").replace("+", "")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # 1.234,56 -> comma is the decimal separator
            text = text.replace(".", "").replace(",", ".")
        else:
            # 1,234.56 -> comma is a thousands separator
            text = text.replace(",", "")
    elif text.count(",") == 1:
        left, _, right = text.partition(",")
        if 1 <= len(right) <= 2:
            text = f"{left}.{right}"
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")

    if not text:
        raise ParseError(f"amount has no digits: {raw!r}")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ParseError(f"invalid amount: {raw!r}") from exc

    if negative:
        value = -value
    return sign * value


def parse_date(raw) -> Optional[date]:
    """Parse a Revolut date cell, returning ``None`` if it is empty/invalid."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


_MOJIBAKE_MARKERS = ("Ã", "Â", "â€")


def repair_mojibake(text: str) -> str:
    """Repair UTF-8 text that was accidentally double-encoded.

    Some Revolut exports store e.g. ``An Púcán`` as ``An PÃºcÃ¡n``. Reversing
    the round-trip recovers the original; anything that doesn't survive the
    round-trip is returned unchanged.
    """
    if not text or not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def parse_transactions(
    rows: Iterable[dict], colmap: dict[str, str]
) -> Iterator[Transaction]:
    """Yield a :class:`Transaction` for every row with a usable amount."""
    by_canonical = {canonical: original for original, canonical in colmap.items()}

    def cell(row: dict, canonical: str):
        original = by_canonical.get(canonical)
        return row.get(original) if original is not None else None

    for row in rows:
        amount_raw = cell(row, "amount")
        if amount_raw is None or str(amount_raw).strip() == "":
            continue
        try:
            amount = parse_amount(amount_raw)
        except ParseError:
            continue

        fee = Decimal("0")
        fee_raw = cell(row, "fee")
        if fee_raw not in (None, ""):
            try:
                fee = parse_amount(fee_raw)
            except ParseError:
                fee = Decimal("0")

        currency = (cell(row, "currency") or "EUR")
        state = (cell(row, "state") or "")
        tx_type = (cell(row, "type") or "")
        product = (cell(row, "product") or "")
        description = (cell(row, "description") or "")

        yield Transaction(
            description=repair_mojibake(str(description).strip()),
            amount=amount,
            fee=fee,
            currency=str(currency).strip().upper(),
            state=str(state).strip(),
            type=str(tx_type).strip().upper(),
            product=repair_mojibake(str(product).strip()),
            completed=parse_date(cell(row, "completed_date")),
            started=parse_date(cell(row, "started_date")),
        )
