.PHONY: install test lint describe validate validate-intake validate-choir validate-choir-plan validate-conductor-response validate-evaluation validate-repo-state validate-router validate-model-policy validate-router-decision dry-run-router

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
	prophet-mesh validate-choir specs/agent-choir.yaml
	prophet-mesh validate-repo-state specs/repo-state.yaml
	prophet-mesh validate-router specs/model-router-interface.yaml
	prophet-mesh validate-model-policy specs/model-task-policy.yaml
	prophet-mesh validate-router-decision examples/router-decision.accepted.json
	! prophet-mesh validate-router-decision examples/router-decision.rejected.json
	prophet-mesh dry-run-router examples/router-request.email.json
	prophet-mesh validate-choir-plan examples/choir-execution-plan.accepted.json
	! prophet-mesh validate-choir-plan examples/choir-execution-plan.rejected.json
	prophet-mesh validate-conductor-response examples/conductor-response.accepted.json
	! prophet-mesh validate-conductor-response examples/conductor-response.rejected.json
	prophet-mesh validate-intake examples/customer-intake.accepted.json
	! prophet-mesh validate-intake examples/customer-intake.rejected.json
	prophet-mesh validate-evaluation examples/evaluation-report.accepted.json
	! prophet-mesh validate-evaluation examples/evaluation-report.rejected.json

validate-intake:
	prophet-mesh validate-intake examples/customer-intake.accepted.json
	! prophet-mesh validate-intake examples/customer-intake.rejected.json

validate-choir:
	prophet-mesh validate-choir specs/agent-choir.yaml

validate-choir-plan:
	prophet-mesh validate-choir-plan examples/choir-execution-plan.accepted.json
	! prophet-mesh validate-choir-plan examples/choir-execution-plan.rejected.json

validate-conductor-response:
	prophet-mesh validate-conductor-response examples/conductor-response.accepted.json
	! prophet-mesh validate-conductor-response examples/conductor-response.rejected.json

validate-evaluation:
	prophet-mesh validate-evaluation examples/evaluation-report.accepted.json
	! prophet-mesh validate-evaluation examples/evaluation-report.rejected.json

validate-repo-state:
	prophet-mesh validate-repo-state specs/repo-state.yaml

validate-router:
	prophet-mesh validate-router specs/model-router-interface.yaml

validate-model-policy:
	prophet-mesh validate-model-policy specs/model-task-policy.yaml

validate-router-decision:
	prophet-mesh validate-router-decision examples/router-decision.accepted.json
	! prophet-mesh validate-router-decision examples/router-decision.rejected.json

dry-run-router:
	prophet-mesh dry-run-router examples/router-request.email.json
