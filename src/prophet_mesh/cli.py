"""Command-line interface for Prophet Mesh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prophet_mesh.contracts import AgentBlueprint
from prophet_mesh.evaluation import validate_evaluation_report_file
from prophet_mesh.intake import validate_intake_file
from prophet_mesh.lifecycle import LIFECYCLE

DESCRIPTION = "Prophet Mesh: the distributed instantiation of the Michael Agent."


def _cmd_describe(_: argparse.Namespace) -> int:
    payload = {
        "name": "prophet-mesh",
        "definition": DESCRIPTION,
        "flagship_agent": "Michael Agent",
        "premium_model": "customer-specific agents derived from the Michael trust kernel",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
