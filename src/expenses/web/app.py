"""FastAPI backend for the Expenses dashboard.

Serves a small read-only JSON API on top of the shared pipeline, plus the
static single-page frontend (also a PWA) from ``web/static``.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .. import pipeline

STATIC_DIR = Path(__file__).parent / "static"

# Resolved relative to the working directory (the repository root), and
# overridable so tests and alternate deployments can point elsewhere.
STATEMENTS_DIR = Path(os.environ.get("EXPENSES_STATEMENTS_DIR", "statements"))
HISTORY_DIR = Path(os.environ.get("EXPENSES_HISTORY_DIR", "history"))

app = FastAPI(title="Expenses", docs_url=None, redoc_url=None)

_cache: dict = {}


def _months() -> dict[str, dict]:
    """Return ``{month: analysis}``, cached until the statements change."""
    signature = tuple(
        (str(p), p.stat().st_mtime) for p in pipeline.list_statements(STATEMENTS_DIR)
    )
    if signature != _cache.get("signature"):
        _cache["signature"] = signature
        _cache["months"] = pipeline.collect_months(STATEMENTS_DIR, HISTORY_DIR)
    return _cache.get("months", {})


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/months")
def list_months() -> dict:
    """Available months with headline totals, newest first."""
    months = _months()
    return {
        "months": [
            {
                "month": month,
                "total_spend": data["report"].get("total_spend", "0"),
                "transaction_count": data["report"].get("transaction_count", 0),
            }
            for month, data in sorted(months.items(), reverse=True)
        ]
    }


@app.get("/api/months/{month}")
def month_detail(month: str) -> dict:
    """Full report and transaction list for one ``YYYY-MM`` month."""
    months = _months()
    if month not in months:
        raise HTTPException(status_code=404, detail=f"No data for {month}")
    return months[month]


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
