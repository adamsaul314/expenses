"""Aggregate transactions into a summary and render it as MD/CSV/JSON."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Optional

from .config import UNCATEGORIZED
from .parser import Transaction

CENTS = Decimal("0.01")


def format_eur(value: Decimal) -> str:
    """Format a value as e.g. ``€1,234.56``."""
    return f"€{value.quantize(CENTS):,.2f}"


def _money(value: Decimal) -> str:
    return str(value.quantize(CENTS))


def _merchant_key(description: str) -> str:
    cleaned = " ".join((description or "").split())
    return cleaned[:60] if cleaned else "(no description)"


def _period(dates: Iterable[Optional[object]]) -> str:
    present = [d for d in dates if d]
    if not present:
        return ""
    low, high = min(present), max(present)
    if low == high:
        return low.isoformat()  # type: ignore[union-attr]
    return f"{low.isoformat()} to {high.isoformat()}"  # type: ignore[union-attr]


def build_report(
    outflows: list[Transaction],
    inflows: Optional[list[Transaction]] = None,
    non_eur: Optional[list[Transaction]] = None,
    *,
    source: str = "",
    generated: Optional[datetime] = None,
) -> dict:
    """Build the summary structure shared by all output formats."""
    inflows = inflows or []
    non_eur = non_eur or []
    generated = generated or datetime.now(timezone.utc)

    total_spend = sum((t.spend for t in outflows), Decimal("0"))
    total_inflow = sum((t.amount for t in inflows), Decimal("0"))

    by_category: dict[str, dict] = {}
    by_merchant: dict[str, dict] = {}
    for tx in outflows:
        cat = by_category.setdefault(tx.category, {"count": 0, "total": Decimal("0")})
        cat["count"] += 1
        cat["total"] += tx.spend

        merchant = by_merchant.setdefault(
            _merchant_key(tx.description), {"count": 0, "total": Decimal("0")}
        )
        merchant["count"] += 1
        merchant["total"] += tx.spend

    categories = []
    for name, entry in sorted(
        by_category.items(), key=lambda item: item[1]["total"], reverse=True
    ):
        share = (entry["total"] / total_spend * 100) if total_spend else Decimal("0")
        categories.append(
            {
                "category": name,
                "count": entry["count"],
                "total": _money(entry["total"]),
                "share": str(share.quantize(Decimal("0.1"))),
            }
        )

    top_merchants = [
        {"merchant": name, "count": entry["count"], "total": _money(entry["total"])}
        for name, entry in sorted(
            by_merchant.items(), key=lambda item: item[1]["total"], reverse=True
        )[:10]
    ]

    return {
        "source": source,
        "generated": generated.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "currency": "EUR",
        "period": _period(tx.completed for tx in outflows),
        "total_spend": _money(total_spend),
        "total_inflow": _money(total_inflow),
        "net": _money(total_inflow - total_spend),
        "transaction_count": len(outflows),
        "categories": categories,
        "top_merchants": top_merchants,
        "uncategorized": [
            {
                "date": tx.completed.isoformat() if tx.completed else "",
                "description": tx.description,
                "amount": _money(tx.spend),
            }
            for tx in outflows
            if tx.category == UNCATEGORIZED
        ],
        "non_eur": [
            {
                "date": tx.completed.isoformat() if tx.completed else "",
                "description": tx.description,
                "amount": _money(tx.amount),
                "currency": tx.currency,
            }
            for tx in non_eur
        ],
    }


def render_markdown(report: dict) -> str:
    """Render *report* as a Markdown document."""
    total_spend = Decimal(report["total_spend"])
    total_inflow = Decimal(report["total_inflow"])

    lines = [
        f"# Expense summary — {report['period'] or 'unknown period'}",
        "",
        f"- **Source:** `{report['source']}`",
        f"- **Generated:** {report['generated']}",
        f"- **Transactions:** {report['transaction_count']}",
        f"- **Total spend:** {format_eur(total_spend)}",
        f"- **Inflow (excluded):** {format_eur(total_inflow)}",
        "",
        "## Spend by category",
        "",
        "| Category | Count | Total | Share |",
        "|---|---:|---:|---:|",
    ]
    if report["categories"]:
        for cat in report["categories"]:
            lines.append(
                f"| {cat['category']} | {cat['count']} | "
                f"{format_eur(Decimal(cat['total']))} | {cat['share']}% |"
            )
    else:
        lines.append("| _(no outflows)_ | 0 | €0.00 | 0.0% |")
    lines.append(
        f"| **Total** | **{report['transaction_count']}** | "
        f"**{format_eur(total_spend)}** | **100.0%** |"
    )
    lines.append("")

    if report["top_merchants"]:
        lines += [
            "## Top merchants",
            "",
            "| Merchant | Count | Total |",
            "|---|---:|---:|",
        ]
        for merchant in report["top_merchants"]:
            lines.append(
                f"| {merchant['merchant']} | {merchant['count']} | "
                f"{format_eur(Decimal(merchant['total']))} |"
            )
        lines.append("")

    if report["uncategorized"]:
        lines += ["## Uncategorized", ""]
        for item in report["uncategorized"]:
            lines.append(
                f"- {item['date']} — {item['description']} — "
                f"{format_eur(Decimal(item['amount']))}"
            )
        lines.append("")

    if report["non_eur"]:
        lines += ["## Non-EUR (excluded from totals)", ""]
        for item in report["non_eur"]:
            lines.append(
                f"- {item['date']} — {item['description']} — "
                f"{item['amount']} {item['currency']}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown(report: dict, path: str | Path) -> None:
    Path(path).write_text(render_markdown(report), encoding="utf-8")


def write_csv(report: dict, path: str | Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Category", "Count", "Total (EUR)", "Share (%)"])
        for cat in report["categories"]:
            writer.writerow(
                [cat["category"], cat["count"], cat["total"], cat["share"]]
            )
        writer.writerow(
            ["Total", report["transaction_count"], report["total_spend"], "100.0"]
        )


def write_json(report: dict, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
