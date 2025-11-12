.PHONY: install lint typecheck test build check clean

install:
	pip install -e .[dev]

lint:
	ruff check src tests

typecheck:
	mypy src

test:
	pytest --maxfail=1 --durations=10

build:
	rm -rf dist/
	python -m build

check: lint typecheck test

clean:
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ .mypy_cache/ .nox/ .tox/ htmlcov/ .coverage .coverage.* site-packages
