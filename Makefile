.PHONY: install test lint describe validate validate-intake

install:
	python -m pip install -e '.[dev]'

test:
	python -m pytest

lint:
	python -m ruff check src tests

describe:
	prophet-mesh describe

validate:
	prophet-mesh validate-blueprint blueprints/michael-agent.yaml
	prophet-mesh validate-blueprint blueprints/premium-custom-agent.yaml
	prophet-mesh validate-intake examples/customer-intake.accepted.json
	! prophet-mesh validate-intake examples/customer-intake.rejected.json

validate-intake:
	prophet-mesh validate-intake examples/customer-intake.accepted.json
	! prophet-mesh validate-intake examples/customer-intake.rejected.json
