.PHONY: install test lint describe

install:
	python -m pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check src tests

describe:
	prophet-mesh describe
