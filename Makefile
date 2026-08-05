PY ?= .venv/bin/python

.PHONY: demo test lint typecheck upworthy build clean

demo:
	$(PY) -m abkit.cli demo --out results
	$(PY) -m abkit.cli inject-readme README.md --results results

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

typecheck:
	$(PY) -m mypy src

upworthy:
	$(PY) examples/upworthy/fetch_data.py
	$(PY) examples/upworthy/audit_upworthy.py

build:
	$(PY) -m build

clean:
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache
