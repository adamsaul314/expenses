# Convenience shortcuts for the expenses tracker.
#
# Uses the project virtualenv explicitly, so you do NOT need to activate it.

VENV    := .venv
PY      := $(VENV)/bin/python
SA_KEY  ?= $(HOME)/.config/expenses/service-account.json

.DEFAULT_GOAL := help
.PHONY: help setup fetch report run test dump clean

help:
	@echo "Usage: make <target>"
	@echo
	@echo "  setup    Create .venv and install dev + Drive dependencies"
	@echo "  fetch    Download the newest statement from Google Drive"
	@echo "  report   Fetch from Drive, then generate the report (default flow)"
	@echo "  run      Generate a report from the newest local statement"
	@echo "  test     Run the test suite"
	@echo "  dump     Show how the newest statement's columns were detected"
	@echo "  clean    Remove the output/ directory"
	@echo
	@echo "  Override the key path with: make fetch SA_KEY=/path/to/key.json"

setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev,drive]"
	@echo "Done. Try: make report"

fetch:
	$(PY) scripts/fetch_statement.py --service-account-file "$(SA_KEY)"

run:
	$(PY) -m expenses

# The everyday command: pull the latest statement, then report.
report: fetch run

test:
	$(PY) -m pytest -q

dump:
	$(PY) -m expenses --dump-columns

clean:
	rm -rf output
