"""Locate and read a Revolut CSV statement."""

from __future__ import annotations

import csv
from pathlib import Path

from .config import COLUMN_ALIASES, REQUIRED_COLUMNS


class StatementError(Exception):
    """Raised when a statement file cannot be found or understood."""


def find_latest_statement(directory: str | Path = "statements") -> Path:
    """Return the most recently modified CSV in *directory*."""
    path = Path(directory)
    if not path.is_dir():
        raise StatementError(f"Statement directory not found: {path}")
    files = [
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() == ".csv" and not p.name.startswith(".")
    ]
    if not files:
        raise StatementError(
            f"No CSV statements found in {path}. Drop a Revolut export there or "
            "run scripts/fetch_statement.py."
        )
    return max(files, key=lambda p: (p.stat().st_mtime, p.name))


def normalize_columns(fieldnames, *, strict: bool = True) -> dict[str, str]:
    """Map original header names to canonical names.

    ``strict`` raises if a required column is missing; set it to ``False`` when
    you only want to inspect what was found (used by ``--dump-columns``).
    """
    colmap: dict[str, str] = {}
    for original in fieldnames:
        if not original:
            continue
        key = " ".join(original.strip().lower().replace("_", " ").split())
        canonical = COLUMN_ALIASES.get(key)
        if canonical:
            colmap[original] = canonical

    if strict:
        missing = REQUIRED_COLUMNS - set(colmap.values())
        if missing:
            names = ", ".join(sorted(missing))
            raise StatementError(
                f"Missing required column(s): {names}. Found: {list(fieldnames)}"
            )
    return colmap


def read_header(path: str | Path) -> list[str]:
    """Return the raw header row of *path*."""
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration as exc:  # pragma: no cover - defensive
            raise StatementError(f"Empty CSV: {path}") from exc


def read_rows(path: str | Path) -> tuple[list[dict], dict[str, str]]:
    """Return ``(rows, column_map)`` for the statement at *path*."""
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise StatementError(f"Empty CSV: {path}")
        colmap = normalize_columns(reader.fieldnames)
        rows = list(reader)
    return rows, colmap
