from decimal import Decimal
from pathlib import Path
import shutil

from expenses import pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "sample_revolut.csv"


def test_analyze_file_returns_report_and_transactions():
    analysis = pipeline.analyze_file(FIXTURE)

    assert analysis["month"] == "2024-01"
    assert analysis["report"]["transaction_count"] == 18
    assert Decimal(analysis["report"]["total_spend"]) == Decimal("575.04")
    assert len(analysis["transactions"]) == 18
    assert {
        "date",
        "description",
        "amount",
        "currency",
        "category",
        "type",
    } <= set(analysis["transactions"][0])


def test_transactions_carry_categories():
    analysis = pipeline.analyze_file(FIXTURE)
    categories = {tx["category"] for tx in analysis["transactions"]}
    assert "Groceries" in categories
    assert "Utilities" in categories


def test_month_filter():
    analysis = pipeline.analyze_file(FIXTURE, month="2023-12")
    assert analysis["report"]["transaction_count"] == 0


def test_history_round_trip(tmp_path):
    analysis = pipeline.analyze_file(FIXTURE)
    path = pipeline.write_history(analysis, tmp_path)
    assert path.name == "2024-01.json"

    stored = pipeline.read_history(tmp_path)
    assert "2024-01" in stored
    assert stored["2024-01"]["report"]["total_spend"] == analysis["report"]["total_spend"]


def test_read_history_handles_missing_dir(tmp_path):
    assert pipeline.read_history(tmp_path / "nope") == {}


def test_collect_months_merges_statements(tmp_path):
    statements = tmp_path / "statements"
    statements.mkdir()
    shutil.copy(FIXTURE, statements / "sample.csv")

    months = pipeline.collect_months(statements, tmp_path / "history")
    assert "2024-01" in months
    assert months["2024-01"]["report"]["transaction_count"] == 18
