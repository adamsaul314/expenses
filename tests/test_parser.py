from decimal import Decimal

import pytest

from expenses.loader import normalize_columns
from expenses.parser import parse_amount, parse_date, parse_transactions, repair_mojibake


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("-42.17", Decimal("-42.17")),
        ("42.17", Decimal("42.17")),
        ("€42.17", Decimal("42.17")),
        ("-€42.17", Decimal("-42.17")),
        ("1,234.56", Decimal("1234.56")),
        ("1.234,56", Decimal("1234.56")),
        ("-1.234,56", Decimal("-1234.56")),
        ("12.34 EUR", Decimal("12.34")),
        ("(12.34)", Decimal("-12.34")),
        ("0", Decimal("0")),
        ("  55.00 ", Decimal("55.00")),
        ("1\u00a0234,56", Decimal("1234.56")),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "abc", "€", None])
def test_parse_amount_rejects_junk(raw):
    with pytest.raises(Exception):
        parse_amount(raw)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2024-01-05 18:31:00", "2024-01-05"),
        ("2024-01-05", "2024-01-05"),
        ("2024-01-05T18:31:00", "2024-01-05"),
        ("05/01/2024", "2024-01-05"),
        ("", None),
        (None, None),
    ],
)
def test_parse_date(raw, expected):
    result = parse_date(raw)
    assert (result.isoformat() if result else None) == expected


def test_repair_mojibake():
    assert repair_mojibake("An PÃºcÃ¡n") == "An Púcán"
    assert repair_mojibake("Tesco Galway") == "Tesco Galway"
    assert repair_mojibake("") == ""


def test_normalize_columns_accepts_revolut_headers():
    headers = [
        "Type", "Product", "Started Date", "Completed Date",
        "Description", "Amount", "Fee", "Currency", "State", "Balance",
    ]
    colmap = normalize_columns(headers)
    assert colmap["Completed Date"] == "completed_date"
    assert colmap["Description"] == "description"
    assert colmap["State"] == "state"


def test_normalize_columns_rejects_missing_required():
    with pytest.raises(Exception):
        normalize_columns(["Description", "State"])  # no Amount column


def test_parse_transactions_skips_rows_without_amount():
    rows = [
        {"Description": "Tesco", "Amount": "-10.00", "State": "COMPLETED"},
        {"Description": "No amount", "Amount": "", "State": "COMPLETED"},
    ]
    colmap = {"Description": "description", "Amount": "amount", "State": "state"}
    transactions = list(parse_transactions(rows, colmap))
    assert len(transactions) == 1
    assert transactions[0].description == "Tesco"
    assert transactions[0].amount == Decimal("-10.00")
    assert transactions[0].is_completed
