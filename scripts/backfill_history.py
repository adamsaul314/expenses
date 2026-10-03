#!/usr/bin/env python3
"""Rebuild the local monthly history from every statement in ``statements/``.

Run after ``fetch_statement.py --all`` so the web dashboard can show trends.
"""

from __future__ import annotations

import sys

from expenses import pipeline


def main() -> int:
    months = pipeline.collect_months("statements", "history")
    if not months:
        print("No statements found in statements/ — nothing to backfill.")
        return 1
    for month, analysis in sorted(months.items()):
        pipeline.write_history(analysis, "history")
        report = analysis["report"]
        print(f"{month}: {report['total_spend']} EUR across {report['transaction_count']} transactions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
