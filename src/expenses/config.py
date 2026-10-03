"""Categories, keyword rules and shared constants.

Keeping the tuning data here means the rest of the code stays generic: add or
reorder keywords without touching the parsing or reporting logic.
"""

from __future__ import annotations

# Canonical column names and the header spellings we accept from Revolut.
COLUMN_ALIASES = {
    "type": "type",
    "product": "product",
    "started date": "started_date",
    "started_date": "started_date",
    "completed date": "completed_date",
    "completed_date": "completed_date",
    "description": "description",
    "amount": "amount",
    "fee": "fee",
    "currency": "currency",
    "state": "state",
    "status": "state",
    "balance": "balance",
}

# Columns we cannot work without.
REQUIRED_COLUMNS = {"amount", "description"}

# ``State`` values we treat as settled. Anything else is skipped.
COMPLETED_STATES = {"completed"}

# Transaction ``Type``s that move money around rather than spend it. Excluded so
# Bank of Ireland top-ups don't offset real spending and internal moves don't
# double count. Tune here if your statements surface bills as transfers.
MONEY_MOVEMENT_TYPES = {"transfer", "topup", "top up", "top-up", "exchange"}

UNCATEGORIZED = "Uncategorized"

# Ordered rules: first match wins. Subscriptions deliberately precede Shopping
# so "Amazon Prime" isn't bucketed as Shopping.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "Groceries",
        (
            "tesco", "dunnes", "supervalu", "super valu", "lidl", "aldi",
            "centra", "spar", "joyce", "o'brien", "obrien", "costcutter",
            "daybreak", "mace", "londis",
        ),
    ),
    (
        "Utilities",
        (
            "esb", "electric ireland", "bord gais", "bord gáis", "gas",
            "gas networks", "irish water", "virgin media", "eir", "eircom",
            "sky", "vodafone", "three", "prepay power", "pinergy",
            "sse airtricity", "energia", "48 mobile",
        ),
    ),
    (
        "Transport & Parking",
        (
            "irish rail", "iarnrod", "iarnród", "bus eireann", "bus éireann",
            "tfi", "leap", "leapcard", "dublin bus", "q-park", "q park",
            "apcoa", "circle k", "applegreen", "topaz", "maxol", "esso",
            "texaco", "toll", "eflow", "e-flow", "m50", "parking",
            "taxi", "free now", "freenow", "uber", "bolt", "citylink",
            "go bus", "aircoach",
        ),
    ),
    (
        "Dining & Social",
        (
            "restaurant", "cafe", "café", "coffee", "pizza", "burger",
            "mcdonald", "kfc", "subway", "deliveroo", "just eat", "justeat",
            "uber eats", "ubereats", "pub", "bar", "tavern", "brewery",
            "wetherspoon", "spoons", "nando", "domino", "starbucks",
            "costa", "insomnia", "butlers", "dining", "takeaway",
            "supermac", "electric galway", "an pucan", "púcán", "pucan",
            "shenduqrwea",  # opaque card descriptor for a Galway gala event
        ),
    ),
    (
        "Housing & Rent",
        ("rent", "landlord", "mortgage", "property", "daft"),
    ),
    (
        "Health & Pharmacy",
        (
            "pharmacy", "boots", "chemist", "medical", "doctor", "gp",
            "dentist", "dental", "hospital", "vhi", "laya",
            "irish life health", "optician", "specsavers", "gym", "leisure",
        ),
    ),
    (
        "Subscriptions",
        (
            "netflix", "spotify", "disney", "prime video", "amazon prime",
            "amazon music", "audible", "apple.com", "apple", "itunes",
            "google", "youtube", "microsoft", "adobe", "patreon",
            "subscription", "openai", "chatgpt",
        ),
    ),
    (
        "Shopping",
        (
            "amazon", "argos", "penneys", "primark", "tk maxx",
            "harvey norman", "currys", "screwfix", "b&q", "woodies", "ikea",
            "decathlon", "sports direct", "zara", "h&m", "asos", "ebay",
        ),
    ),
    (
        "Cash & ATM",
        ("atm", "cash withdrawal", "withdrawal", "cash"),
    ),
    (
        "Fees",
        ("fee", "charge", "commission", "service charge"),
    ),
]
