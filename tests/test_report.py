from decimal import Decimal
from pathlib import Path

from expenses.__main__ import _select_transactions
from expenses.loader import read_rows
from expenses.report import build_report, format_eur, render_markdown

FIXTURE = Path(__file__).parent / "fixtures" / "sample_revolut.csv"


def _report():
    rows, colmap = read_rows(FIXTURE)
    outflows, inflows, non_eur = _select_transactions(rows, colmap, month=None)
    return build_report(outflows, inflows=inflows, non_eur=non_eur, source=str(FIXTURE))


def test_format_eur():
    assert format_eur(Decimal("1234.5")) == "€1,234.50"
    assert format_eur(Decimal("-6")) == "€-6.00"


def test_end_to_end_totals():
    report = _report()

    # 18 EUR outflows: completed, negative, excluding money movement.
    assert report["transaction_count"] == 18
    assert Decimal(report["total_spend"]) == Decimal("575.04")

    # Only the card refund counts as inflow; the Bank of Ireland top-up is
    # money movement and must be excluded.
    assert Decimal(report["total_inflow"]) == Decimal("12.00")
    assert Decimal(report["net"]) == Decimal("-563.04")


def test_end_to_end_categories():
    report = _report()
    totals = {cat["category"]: Decimal(cat["total"]) for cat in report["categories"]}

    assert totals["Groceries"] == Decimal("136.77")  # 42.17 + 63.40 + 31.20
    assert totals["Utilities"] == Decimal("139.30")  # 85.00 + 54.30
    assert totals["Transport & Parking"] == Decimal("18.50")  # 12.50 + 6.00
    assert totals["Dining & Social"] == Decimal("63.40")  # 38.90 + 24.50
    assert totals["Subscriptions"] == Decimal("27.98")  # 17.99 + 9.99
    assert totals["Fees"] == Decimal("1.50")  # 1.00 fee row + 0.50 card fee
    assert totals["Uncategorized"] == Decimal("42.00")  # 22.00 + 20.00


def test_non_eur_is_reported_not_counted():
    report = _report()
    assert len(report["non_eur"]) == 1
    assert report["non_eur"][0]["currency"] == "GBP"


def test_pending_is_ignored():
    rows, colmap = read_rows(FIXTURE)
    outflows, _, _ = _select_transactions(rows, colmap, month=None)
    assert all("Pending Coffee Shop" not in tx.description for tx in outflows)


def test_render_markdown_contains_table():
    markdown = render_markdown(_report())
    assert "# Expense summary" in markdown
    assert "| Category | Count | Total | Share |" in markdown
    assert "€575.04" in markdown
