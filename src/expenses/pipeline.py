"""Shared processing pipeline used by both the CLI and the web API.

Anything that turns statements into reports lives here so the command line and
the web dashboard never drift apart.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Optional

from . import report as report_mod
from .categorize import categorize
from .config import MONEY_MOVEMENT_TYPES
from .loader import StatementError, find_latest_statement, read_rows
from .parser import Transaction, parse_transactions

HISTORY_DIR = Path("history")
CENTS = Decimal("0.01")


def list_statements(statements_dir: str | Path = "statements") -> list[Path]:
    """Return every CSV statement in *statements_dir*, oldest first."""
    directory = Path(statements_dir)
    if not directory.is_dir():
        return []
    files = [
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".csv" and not p.name.startswith(".")
    ]
    return sorted(files, key=lambda p: (p.stat().st_mtime, p.name))


def _expand_fees(transactions: Iterable[Transaction]):
    """Yield each transaction, plus a synthetic Fees line for negative fees."""
    for tx in transactions:
        yield tx
        if tx.fee and tx.fee < 0:
            label = f"Fee — {tx.description}" if tx.description else "Fee"
            yield Transaction(
                description=label,
                amount=tx.fee,
                currency=tx.currency,
                state=tx.state,
                type="FEE",
                product=tx.product,
                completed=tx.completed,
                started=tx.started,
            )


def categorize_transactions(transactions: Iterable[Transaction]) -> None:
    """Assign a category to each transaction in place."""
    for tx in transactions:
        tx.category = "Fees" if tx.type.lower() == "fee" else categorize(tx.description)


def select_transactions(
    rows: Iterable[dict], colmap: dict[str, str], month: Optional[str] = None
):
    """Filter rows down to EUR outflows/inflows, honouring state and type."""
    has_state = "state" in colmap.values()
    outflows: list[Transaction] = []
    inflows: list[Transaction] = []
    non_eur: list[Transaction] = []

    for tx in _expand_fees(parse_transactions(rows, colmap)):
        if has_state and not tx.is_completed:
            continue
        if month and (tx.completed is None or tx.completed.strftime("%Y-%m") != month):
            continue
        if tx.currency not in ("EUR", ""):
            non_eur.append(tx)
            continue
        if tx.type.lower() in MONEY_MOVEMENT_TYPES:
            continue
        if tx.amount < 0:
            outflows.append(tx)
        elif tx.amount > 0:
            inflows.append(tx)

    categorize_transactions(outflows)
    return outflows, inflows, non_eur


def _derive_month(outflows: list[Transaction]) -> str:
    dates = [tx.completed for tx in outflows if tx.completed]
    if dates:
        return max(dates).strftime("%Y-%m")
    return date.today().strftime("%Y-%m")


def _serialize_transactions(outflows: list[Transaction]) -> list[dict]:
    return [
        {
            "date": tx.completed.isoformat() if tx.completed else "",
            "description": tx.description,
            "amount": str(tx.amount.quantize(CENTS)),
            "currency": tx.currency,
            "category": tx.category,
            "type": tx.type,
        }
        for tx in outflows
    ]


def analyze_file(path: str | Path, month: Optional[str] = None) -> dict:
    """Process a single statement file into a report + transaction list."""
    rows, colmap = read_rows(path)
    outflows, inflows, non_eur = select_transactions(rows, colmap, month)
    report = report_mod.build_report(
        outflows, inflows=inflows, non_eur=non_eur, source=str(path)
    )
    return {
        "month": month or _derive_month(outflows),
        "source": str(path),
        "report": report,
        "transactions": _serialize_transactions(outflows),
    }


def analyze(
    path: Optional[str | Path] = None,
    *,
    statements_dir: str | Path = "statements",
    month: Optional[str] = None,
) -> dict:
    """Process *path*, or the newest statement in *statements_dir*."""
    target = Path(path) if path is not None else find_latest_statement(statements_dir)
    return analyze_file(target, month=month)


# --- Monthly history -------------------------------------------------------


def write_history(analysis: dict, history_dir: str | Path = HISTORY_DIR) -> Path:
    """Persist a processed month so the web UI can show history and trends."""
    directory = Path(history_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{analysis['month']}.json"
    target.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return target


def read_history(history_dir: str | Path = HISTORY_DIR) -> dict[str, dict]:
    """Load all stored monthly summaries, keyed by ``YYYY-MM``."""
    directory = Path(history_dir)
    months: dict[str, dict] = {}
    if not directory.is_dir():
        return months
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        month = data.get("month") or path.stem
        months[month] = data
    return months


def collect_months(
    statements_dir: str | Path = "statements",
    history_dir: str | Path = HISTORY_DIR,
) -> dict[str, dict]:
    """Merge stored history with any statements currently on disk.

    Fresh statements win, so editing or re-exporting a file updates the month.
    """
    months = read_history(history_dir)
    for path in list_statements(statements_dir):
        try:
            analysis = analyze_file(path)
        except (StatementError, OSError):
            continue
        months[analysis["month"]] = analysis
    return months
