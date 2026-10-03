# expenses

A small Python tool that turns a monthly **Revolut** CSV statement (including
linked **Bank of Ireland** activity) into a clean Euro spending report. Built
for a user in Galway, Ireland.

It picks the newest CSV from `statements/`, keeps only completed EUR
transactions, categorises spending with local keyword rules (Tesco, Dunnes,
ESB, Bord Gáis, Irish Rail, Q-Park, pubs, and more), and writes the summary as
Markdown, CSV, and JSON.

## Features

- Newest-statement auto-discovery (or point at a specific file).
- Completed-only filtering; pending/reverted/declined rows are skipped.
- Robust Euro parsing: `€1,234.56` and `1.234,56` both work.
- Excludes money movement (top-ups, transfers, exchanges) so Bank of Ireland
  top-ups don't offset real spending.
- Keyword categorisation tuned for Ireland, with an `Uncategorized` bucket.
- Reports: per-category totals, top merchants, uncategorized lines, and
  non-EUR rows listed separately.
- Standard-library core; Google Drive support is isolated for CI.

## Requirements

- Python 3.10+

## Quick start (local)

```bash
# 1. Put a Revolut CSV export in statements/ (it is git-ignored).
cp ~/Downloads/statement.csv statements/

# 2. Run without installing anything:
PYTHONPATH=src python -m expenses

# ...or install the console script:
pip install -e .
expenses
```

Output is printed to the terminal and saved to `output/summary_YYYY-MM.{md,csv,json}`.

### Useful options

```bash
expenses --file statements/statement.csv   # specific file
expenses --month 2024-01                   # filter to one month
expenses --format md                       # choose output formats
expenses --dump-columns                    # inspect a file's columns
expenses --help
```

`--dump-columns` is handy the first time you export from Revolut: it prints the
header names and how they map to the fields the tool expects.

## How transactions are selected

1. Rows are kept only when `State == COMPLETED`.
2. Non-EUR rows are reported under "Non-EUR" and excluded from totals.
3. `Type` values `TRANSFER`, `TOPUP`, `EXCHANGE` (money movement) are ignored.
4. Negative amounts are outflows; positive amounts are inflows and are shown
   separately, not netted against spending.
5. Negative `Fee` values become their own `Fees` line.

Categorisation rules live in [`src/expenses/config.py`](src/expenses/config.py) —
add or reorder keywords there; the first match wins.

## Google Drive in CI (one-off setup)

The monthly GitHub Actions workflow reads statements from a Google Drive folder
(`expenses`) using a service account, because a desktop Drive mount is not
available on a runner. The folder is located **by name**, so no folder ID is
needed.

1. Create a Google Cloud project and enable the **Google Drive API**.
2. Create a **service account**, then create and download a **JSON key**.
3. In Google Drive, share the `expenses` folder with the service-account email
   (`...@<project>.iam.gserviceaccount.com`) as **Viewer**.
4. Add the repository secret (Settings → Secrets and variables → Actions):
   - `GDRIVE_SERVICE_ACCOUNT_JSON` — the full contents of the JSON key.

If your folder is not called `expenses`, set `GDRIVE_FOLDER_NAME` (as an env var,
the `--folder-name` flag, or a repository variable).

You can test the fetch locally:

```bash
pip install -r requirements.txt
python scripts/fetch_statement.py \
  --service-account-file /path/to/key.json
```

## GitHub Actions

[`.github/workflows/monthly-report.yml`](.github/workflows/monthly-report.yml)
runs at **06:00 UTC on the 1st of each month** (and on manual dispatch). It
installs dependencies, runs the tests, fetches the newest statement from Drive,
generates the report, and uploads `output/` as the `expense-summary` artifact.

> Notes: scheduled workflows only run from the default branch, and GitHub
> disables schedules after ~60 days of repository inactivity. Re-enable from the
> Actions tab, or trigger a manual run.

## Project layout

```
src/expenses/
  __main__.py     CLI and pipeline orchestration
  config.py       categories, keyword rules, column aliases
  loader.py       newest-CSV discovery + CSV reading
  parser.py       amount/date parsing, Transaction model
  categorize.py   keyword → category
  report.py       aggregation + Markdown/CSV/JSON writers
scripts/
  fetch_statement.py   Google Drive download for CI
tests/                   unit + end-to-end tests on a fixture
```

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

## Privacy

`statements/*.csv`, `output/`, and service-account keys are git-ignored. Keep
the repository private and never commit real bank data.
