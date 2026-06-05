"""Command-line interface for Prophet Mesh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prophet_mesh.choir import validate_choir_spec_file
from prophet_mesh.contracts import AgentBlueprint
from prophet_mesh.evaluation import validate_evaluation_report_file
from prophet_mesh.intake import validate_intake_file
from prophet_mesh.lifecycle import LIFECYCLE
from prophet_mesh.repo_state import validate_repo_state_file
from prophet_mesh.router import validate_router_interface_file
from prophet_mesh.router_decision import validate_router_decision_file
from prophet_mesh.model_policy import validate_model_task_policy_file

DESCRIPTION = "Prophet Mesh: the distributed instantiation of the Michael Agent."


def _cmd_describe(_: argparse.Namespace) -> int:
    payload = {
        "name": "prophet-mesh",
        "definition": DESCRIPTION,
        "flagship_agent": "Michael Agent",
        "product_shape": "agent choir with Michael as the default conductor",
        "premium_model": "customer-specific named conductors and choirs derived from the Michael trust kernel",
        "trust_kernel": ["identity", "policy", "evidence", "attestation", "revocation", "audit"],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_lifecycle(_: argparse.Namespace) -> int:
    print(" -> ".join(LIFECYCLE))
    return 0


def _cmd_validate_blueprint(args: argparse.Namespace) -> int:
    blueprint = AgentBlueprint.from_yaml(Path(args.path))
    errors = blueprint.validate()
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "name": blueprint.name, "edition": blueprint.edition}, indent=2))
    return 0


def _cmd_validate_intake(args: argparse.Namespace) -> int:
    result = validate_intake_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def _cmd_validate_evaluation(args: argparse.Namespace) -> int:
    result = validate_evaluation_report_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def _cmd_validate_choir(args: argparse.Namespace) -> int:
    result = validate_choir_spec_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def _cmd_validate_repo_state(args: argparse.Namespace) -> int:
    result = validate_repo_state_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def _cmd_validate_router(args: argparse.Namespace) -> int:
    result = validate_router_interface_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def _cmd_validate_model_policy(args: argparse.Namespace) -> int:
    result = validate_model_task_policy_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def _cmd_validate_router_decision(args: argparse.Namespace) -> int:
    result = validate_router_decision_file(Path(args.path))
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prophet-mesh", description=DESCRIPTION)
    subcommands = parser.add_subparsers(dest="command", required=True)

    describe = subcommands.add_parser("describe", help="describe the product nucleus")
    describe.set_defaults(func=_cmd_describe)

    lifecycle = subcommands.add_parser("lifecycle", help="print the canonical swarm lifecycle")
    lifecycle.set_defaults(func=_cmd_lifecycle)

    validate_blueprint = subcommands.add_parser("validate-blueprint", help="validate an agent blueprint")
    validate_blueprint.add_argument("path")
    validate_blueprint.set_defaults(func=_cmd_validate_blueprint)

    validate_intake = subcommands.add_parser(
        "validate-intake",
        help="validate a premium customer intake artifact",
    )
    validate_intake.add_argument("path")
    validate_intake.set_defaults(func=_cmd_validate_intake)

    validate_evaluation = subcommands.add_parser(
        "validate-evaluation",
        help="validate a Prophet Mesh evaluation report",
    )
    validate_evaluation.add_argument("path")
    validate_evaluation.set_defaults(func=_cmd_validate_evaluation)

    validate_choir = subcommands.add_parser(
        "validate-choir",
        help="validate the Prophet Mesh Agent Choir spec",
    )
    validate_choir.add_argument("path")
    validate_choir.set_defaults(func=_cmd_validate_choir)

    validate_repo_state = subcommands.add_parser(
        "validate-repo-state",
        help="validate the Prophet Mesh repo-state architecture spec",
    )
    validate_repo_state.add_argument("path")
    validate_repo_state.set_defaults(func=_cmd_validate_repo_state)

    validate_router = subcommands.add_parser(
        "validate-router",
        help="validate the Prophet Mesh model-router interface contract",
    )
    validate_router.add_argument("path")
    validate_router.set_defaults(func=_cmd_validate_router)

    validate_model_policy = subcommands.add_parser(
        "validate-model-policy",
        help="validate the Prophet Mesh model task/domain policy",
    )
    validate_model_policy.add_argument("path")
    validate_model_policy.set_defaults(func=_cmd_validate_model_policy)

    validate_router_decision = subcommands.add_parser(
        "validate-router-decision",
        help="validate a Prophet Mesh router decision artifact",
    )
    validate_router_decision.add_argument("path")
    validate_router_decision.set_defaults(func=_cmd_validate_router_decision)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
