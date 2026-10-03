"""Command-line entry point: ``python -m expenses``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report as report_mod
from .loader import StatementError, find_latest_statement, normalize_columns, read_header
from .pipeline import analyze, write_history


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
        "--no-history",
        action="store_true",
        help="Do not update the local history used by the web UI.",
    )
    parser.add_argument(
        "--dump-columns",
        action="store_true",
        help="Print the statement's columns and how they map, then exit.",
    )
    return parser


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

    analysis = analyze(path=path, month=args.month)
    report = analysis["report"]

    # Keep monthly history for the web dashboard (skip when the user filtered,
    # since a filtered subset shouldn't overwrite the full month).
    if not args.month and not args.no_history:
        write_history(analysis)

    month_label = args.month or analysis["month"]
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
