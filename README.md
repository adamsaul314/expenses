# expenses

A personal expense tracker for **Revolut** CSV statements in Euro, built for a
Galway (Ireland) user. Drop a monthly statement in, and it filters out
everything that isn't real spending, sorts it into local categories
(groceries, utilities, transport, dining, …), and produces a tidy report.

It can run **on your laptop in one command**, or **automatically once a month**
in GitHub Actions using a Google Drive folder as the source.

---

## What it does

- Finds the newest statement automatically (or you point it at a specific file).
- Keeps only **completed** transactions — pending, declined and reversed rows are skipped.
- Reads Euro amounts whether they're written `€1,234.56` or `1.234,56`.
- Ignores money movement (top-ups, transfers, exchanges), so transfers from your
  Bank of Ireland account don't cancel out real spending.
- Categorises by keyword — Tesco/Dunnes/Lidl → Groceries, ESB/Bord Gáis → Utilities,
  Irish Rail/Q-Park → Transport, pubs/Deliveroo → Dining & Social, and so on.
- Writes the result as **Markdown**, **CSV** and **JSON**:
  `output/summary_YYYY-MM.{md,csv,json}`.

---

## What we're using (and why)

| Piece | What it is | Why it's here |
|---|---|---|
| **Python 3.10+ (standard library only)** | The tracker itself — `csv`, `decimal`, `argparse`, `pathlib`. | No third-party dependencies for the core, so it runs almost anywhere. |
| **GNU Make** | A `Makefile` with friendly shortcuts. | `make report` is the whole monthly routine in one command. |
| **Google Drive API + service account** | A machine account that reads your `expenses` Drive folder. | A GitHub runner can't see the Drive folder mounted on your desktop, so it needs its own read-only credentials. |
| **GitHub Actions** | The scheduler/runner. | Generates the report on the 1st of each month even if your laptop is off, and stores it as an artifact. |
| **FastAPI + Chart.js** | The local web dashboard (also a PWA). | Charts and a searchable table on laptop and phone, reusing the same Python engine. |
| **pytest** | The test suite (66 tests). | Keeps the amount parsing, filtering and categorisation correct as you add keywords. |

The core tracker has **no dependencies**. Only the Drive download
(`scripts/fetch_statement.py`) needs the Google libraries, and that's isolated so
everyday local use stays simple.

---

## Everyday use

> On this machine the one-time setup is already done (virtualenv created, Drive
> folder shared, GitHub secret set). So day to day you only need the steps below.

### The monthly routine

**1. Get the statement into Google Drive**
In the Revolut app: *Profile → Statements → Export* (CSV), then upload it to your
Google Drive folder called **`expenses`**.

**2. Generate the report**

```bash
cd ~/Desktop/projects/expenses
make report
```

That downloads the newest statement from Drive and writes the report. Open
`output/summary_YYYY-MM.md` to read it — it also prints to the terminal.

**That's it.** If you'd rather do nothing, the GitHub Actions workflow does the
same thing automatically at **06:00 UTC on the 1st of every month** and saves the
report as a downloadable artifact.

### Reading the report

The Markdown summary has four parts:

- **Header** — the date range, source file, and total spend.
- **Spend by category** — how much went to each category and its share of the total.
- **Top merchants** — your biggest individual payees.
- **Uncategorized / Non-EUR** — anything the keyword rules didn't recognise, and
  rows in another currency (excluded from totals). Check this occasionally and add
  a keyword if a regular merchant shows up.

### Command cheat sheet

Run from the project folder.

| Command | What it does |
|---|---|
| `make report` | **Everyday command** — fetch newest statement from Drive, then report |
| `make run` | Report from the newest file already in `statements/` (no Drive) |
| `make fetch` | Only download the newest statement into `statements/` |
| `make web` | Serve the web dashboard at <http://127.0.0.1:8000> |
| `make backfill` | Download every Drive statement and rebuild monthly history |
| `make dump` | Show the statement's columns and how they were mapped |
| `make test` | Run the test suite |
| `make clean` | Delete the `output/` and `history/` folders |
| `make help` | List all shortcuts |

You can also call the tool directly (e.g. without the venv activated):

```bash
.venv/bin/expenses --file statements/statement.csv   # a specific file
.venv/bin/expenses --month 2026-10                    # only one month
.venv/bin/expenses --format md                        # Markdown only
.venv/bin/expenses --dump-columns                     # inspect columns
.venv/bin/expenses --help
```

---

## Web dashboard & phone app

A small local web app renders the same report as charts, plus a transaction
table you can search. It's also a **PWA**, so Android can install it to the home
screen — no Play Store needed.

### On your laptop

```bash
make web          # serves http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000>. You get summary cards, a category donut, a
month-over-month trend, top merchants, and a searchable/filterable transaction
table. Each month you process is stored in the git-ignored `history/` folder, so
the trend fills in over time. To seed history from every statement in Drive:

```bash
make backfill
```

### On your Android phone (PWA)

PWAs need HTTPS, so the phone reaches the local server through **Tailscale**
instead of opening a port to the public internet.

1. Install Tailscale on the laptop and the phone and sign in to the same tailnet
   (free for personal use):

   ```bash
   # laptop
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   sudo tailscale serve --bg 8000     # prints https://<machine>.<tailnet>.ts.net
   ```

2. Open that HTTPS URL on the phone (same tailnet).
3. In Chrome: **⋮ → Add to Home screen**. It opens full-screen and caches the
   shell for offline viewing.

Nothing is exposed publicly — it's only reachable inside your private tailnet.
If your folder is more than a month old, run `make backfill` first so the trend
chart has data.

---

## What counts as spending

For each statement, the tool applies these rules in order:

1. `State` must be `COMPLETED`.
2. Non-EUR rows are listed under **Non-EUR** and excluded from totals.
3. Transaction types `TRANSFER`, `TOPUP` and `EXCHANGE` (money movement) are ignored.
4. Negative amounts are outflows (spending); positive amounts are inflows, shown
   separately and *not* netted against spending.
5. A negative `Fee` becomes its own `Fees` line.

Categorisation is by keyword, first match wins, using word boundaries so short
terms don't over-match. The rules live in
[`src/expenses/config.py`](src/expenses/config.py).

### Adding or fixing a category

Open `src/expenses/config.py` and add a keyword to the relevant list, then:

```bash
make test     # make sure nothing broke
make run      # regenerate the report
```

To send an opaque card descriptor to a category, add the exact string (for
example, the gala charge `shenduqrwea` is mapped to Dining & Social).

---

## Automation (GitHub Actions)

[`.github/workflows/monthly-report.yml`](.github/workflows/monthly-report.yml)
runs on a schedule and can be triggered by hand. It:

1. installs dependencies,
2. runs the tests,
3. downloads the newest CSV from the Drive `expenses` folder,
4. generates the report,
5. uploads `output/` as the `expense-summary` artifact.

Trigger a run manually (needs the GitHub CLI, already installed here):

```bash
gh workflow run "Monthly expense report"
gh run watch
```

> Notes: scheduled workflows only run from the default branch, and GitHub pauses
> schedules after ~60 days of repository inactivity. Re-enable from the Actions
> tab if needed.

---

## One-time setup reference

This is what was configured — keep it for rebuilding on a new machine.

### A. Local tool

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,drive,web]"
```

(On Debian/Ubuntu, `sudo apt install python3.12-venv` first if `venv` is
missing. If you don't want to install anything, you can instead run the core
tool with `PYTHONPATH=src python3 -m expenses` — no Google Drive support.)

### B. Google Drive access

1. Create a Google Cloud project and enable the **Google Drive API**.
2. Create a **service account** and a **JSON key**.
3. Share the Drive folder (`expenses`) with the service-account email as **Viewer**.
4. Store the key contents as the repository secret `GDRIVE_SERVICE_ACCOUNT_JSON`.

The fetch script finds the folder **by name** (default `expenses`); set
`GDRIVE_FOLDER_NAME` or pass `--folder-name` if yours differs. On this machine
the key lives at `~/.config/expenses/service-account.json` and is used by
`make fetch`. Test it with:

```bash
.venv/bin/python scripts/fetch_statement.py \
  --service-account-file ~/.config/expenses/service-account.json
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `error: externally-managed-environment` when running `pip install` | Use the virtualenv above, or `PYTHONPATH=src python3 -m expenses` for the core tool. |
| `No CSV statements found` | Put a CSV in `statements/`, or run `make fetch`, or check the Drive folder name. |
| `no Drive folder named 'expenses'` | Share the folder with the service-account email (Viewer). |
| Lots of `Uncategorized` | Add keywords in `src/expenses/config.py`, then `make test && make run`. |
| Garbled names like `An PÃºcÃ¡n` | Already handled — the tool repairs double-encoded UTF-8 from Revolut exports. |

---

## Project layout

```
src/expenses/
  __main__.py     CLI entry point
  pipeline.py     shared processing used by both CLI and web
  config.py       categories, keyword rules, column aliases
  loader.py       newest-CSV discovery + CSV reading
  parser.py       amount/date parsing, UTF-8 repair, Transaction model
  categorize.py   keyword → category
  report.py       aggregation + Markdown/CSV/JSON writers
  web/            FastAPI app + PWA static assets (HTML/CSS/JS/icons)
scripts/
  fetch_statement.py    Google Drive download (used locally and in CI)
  backfill_history.py   rebuild monthly history from statements/
tests/                   unit, API and end-to-end tests on a redacted fixture
Makefile                 make report / web / fetch / backfill / test / dump / clean
.github/workflows/       monthly scheduled report
```

## Privacy

`statements/*.csv`, `output/`, and service-account keys are git-ignored. Keep the
repository private and never commit real bank data or the JSON key.
