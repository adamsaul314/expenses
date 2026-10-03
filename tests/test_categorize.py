import pytest

from expenses.categorize import categorize


@pytest.mark.parametrize(
    "description,category",
    [
        ("TESCO GALWAY", "Groceries"),
        ("Dunnes Stores Eyre Square", "Groceries"),
        ("LIDL IRELAND", "Groceries"),
        ("ESB Networks", "Utilities"),
        ("Bord Gais Energy", "Utilities"),
        ("Irish Rail", "Transport & Parking"),
        ("Q-Park Galway", "Transport & Parking"),
        ("The Kings Head Pub", "Dining & Social"),
        ("Deliveroo", "Dining & Social"),
        ("An Púcán", "Dining & Social"),
        ("Supermac's", "Dining & Social"),
        ("Electric Galway", "Dining & Social"),
        ("48 Mobile", "Utilities"),
        ("Boots Pharmacy", "Health & Pharmacy"),
        ("NETFLIX.COM", "Subscriptions"),
        ("AMAZON PRIME", "Subscriptions"),
        ("Amazon Marketplace", "Shopping"),
        ("ATM Withdrawal", "Cash & ATM"),
        ("Some Unknown Shop XYZ", "Uncategorized"),
        ("", "Uncategorized"),
    ],
)
def test_categorize(description, category):
    assert categorize(description) == category


def test_word_boundaries_do_not_overmatch():
    # "eir" must not match inside "their", "bar" not inside "Barcelona".
    assert categorize("Their Company") == "Uncategorized"
    assert categorize("Barcelona Flights") == "Uncategorized"
