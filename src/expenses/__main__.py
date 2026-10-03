"""Command-line entry point: ``python -m expenses``."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import report as report_mod
from .categorize import categorize
from .config import MONEY_MOVEMENT_TYPES
from .loader import StatementError, find_latest_statement, normalize_columns, read_header, read_rows
from .parser import Transaction, parse_transactions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expenses",
        description="Summarize a monthly Revolut CSV statement and report outflows in Euro.",
    )
    parser.add_argument(
        "--file",
        help="Specific statement CSV to read (default: newest in --statements-dir).",
    )
    parser.add_argument(
        "--statements-dir",
        default="statements",
        help="Directory to search for statements (default: statements).",
    )
    parser.add_argument(
        "--month",
        help="Only include transactions in YYYY-MM.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory for generated summary files (default: output).",
    )
    parser.add_argument(
        "--format",
        default="md,csv,json",
        help="Comma-separated output formats: md,csv,json (default: all).",
    )
    parser.add_argument(
        "--dump-columns",
        action="store_true",
        help="Print the statement's columns and how they map, then exit.",
    )
    return parser


def _expand_fees(transactions):
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


def _categorize(transactions) -> None:
    for tx in transactions:
        if tx.type.lower() == "fee":
            tx.category = "Fees"
        else:
            tx.category = categorize(tx.description)


def _derive_month(outflows, path: Path) -> str:
    dates = [tx.completed for tx in outflows if tx.completed]
    if dates:
        return max(dates).strftime("%Y-%m")
    return date.today().strftime("%Y-%m")


def _select_transactions(rows, colmap, month):
    """Filter rows down to EUR outflows/inflows, honouring state and type."""
    has_state = "state" in colmap.values()
    transactions = list(parse_transactions(rows, colmap))

    outflows: list[Transaction] = []
    inflows: list[Transaction] = []
    non_eur: list[Transaction] = []

    for tx in _expand_fees(transactions):
        if has_state and not tx.is_completed:
            continue
        if month and (tx.completed is None or tx.completed.strftime("%Y-%m") != month):
            continue
        if tx.currency not in ("EUR", ""):
            non_eur.append(tx)
            continue
        if tx.type.lower() in MONEY_MOVEMENT_TYPES:
            # Money movement (e.g. Bank of Ireland top-ups), not spending.
            continue
        if tx.amount < 0:
            outflows.append(tx)
        elif tx.amount > 0:
            inflows.append(tx)

    _categorize(outflows)
    return outflows, inflows, non_eur


def run(args: argparse.Namespace) -> int:
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise StatementError(f"File not found: {path}")
    else:
        path = find_latest_statement(args.statements_dir)

    if args.dump_columns:
        fieldnames = read_header(path)
        colmap = normalize_columns(fieldnames, strict=False)
        print(f"Columns in {path}:")
        for original in fieldnames:
            canonical = colmap.get(original)
            suffix = f" -> {canonical}" if canonical else "   (unrecognized)"
            print(f"  {original!r}{suffix}")
        return 0

    rows, colmap = read_rows(path)
    outflows, inflows, non_eur = _select_transactions(rows, colmap, args.month)

    report = report_mod.build_report(
        outflows, inflows=inflows, non_eur=non_eur, source=str(path)
    )

    month_label = args.month or _derive_month(outflows, path)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    formats = {part.strip().lower() for part in args.format.split(",") if part.strip()}
    written: list[Path] = []
    if "md" in formats:
        target = out_dir / f"summary_{month_label}.md"
        report_mod.write_markdown(report, target)
        written.append(target)
    if "csv" in formats:
        target = out_dir / f"summary_{month_label}.csv"
        report_mod.write_csv(report, target)
        written.append(target)
    if "json" in formats:
        target = out_dir / f"summary_{month_label}.json"
        report_mod.write_json(report, target)
        written.append(target)

    print(report_mod.render_markdown(report))
    if written:
        print("Saved:")
        for target in written:
            print(f"  {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except StatementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
