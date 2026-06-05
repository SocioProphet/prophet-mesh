# Prophet Mesh

Prophet Mesh is the open agent-choir product centered on the Michael Agent as the default conductor.

Michael is the flagship relationship interface: the stable, clarifying, lifelong advisor that speaks with the user, maintains context, negotiates intent, routes work, delegates to specialist agents, and synthesizes the choir back into one coherent experience. The product is not a single-agent chatbot. It is a composable conductor-plus-choir system over an open mesh model family.

Premium customers can create named Michael-derived conductor agents and compose their own specialist choir. They may customize name, voice, domain vocabulary, memory scope, specialist roster, tools, workflows, model allowlists, and deployment topology. They may not bypass the trust kernel: identity, policy, evidence, attestation, revocation, audit, tenant isolation, and lifecycle semantics.

## Product line

- **Michael Agent**: default conductor, lifelong advisor, and canonical relationship surface.
- **Prophet Mesh Premium**: customer-named conductor agents and specialist choirs derived from the Michael trust kernel.
- **Prophet Mesh Enterprise**: private mesh deployment with organization policy, identity integration, tenant isolation, audit, and environment-specific runtimes.

## Architecture

```text
Human / Organization
  <-> Conductor Agent
        default: Michael Agent
        premium: customer-named Michael-derived conductor
  <-> Single Model Router Interface
  <-> Agent Choir
        memory steward
        router agent
        research agent
        planning agent
        writing agent
        coding agent
        analytics agent
        operations agent
        creative agent
        governance sentinel
  <-> Open Mesh Model Family
  <-> Tools, Workflows, Repositories, Devices, APIs
```

Core invariants:

1. The user primarily experiences one stable conductor relationship.
2. The conductor routes through one model-router interface.
3. The choir is composable across specialist agents and model families.
4. Relational memory is scoped, contextual, and governed.
5. Premium customers can name and train derived conductors and choirs.
6. Trust-kernel controls cannot be weakened or bypassed.

## Repository layout

```text
blueprints/               Agent blueprints and premium customization examples
docs/                     Architecture, product, market, and intake notes
examples/                 Accepted and rejected intake/evaluation fixtures
specs/                    Machine-readable contracts, including agent-choir.yaml, repo-state.yaml, model-router-interface.yaml, and model-task-policy.yaml
src/prophet_mesh/          Reference Python package and CLI validators
tests/                    Contract, lifecycle, intake, evaluation, choir, repo-state, router, and model-policy tests
```

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m ruff check src tests
python -m pytest
prophet-mesh describe
prophet-mesh lifecycle
prophet-mesh validate-blueprint blueprints/michael-agent.yaml
prophet-mesh validate-blueprint blueprints/premium-custom-agent.yaml
prophet-mesh validate-choir specs/agent-choir.yaml
prophet-mesh validate-repo-state specs/repo-state.yaml
prophet-mesh validate-router specs/model-router-interface.yaml
prophet-mesh validate-model-policy specs/model-task-policy.yaml
prophet-mesh validate-intake examples/customer-intake.accepted.json
prophet-mesh validate-evaluation examples/evaluation-report.accepted.json
```

## CLI

```bash
prophet-mesh describe
prophet-mesh lifecycle
prophet-mesh validate-blueprint blueprints/michael-agent.yaml
prophet-mesh validate-choir specs/agent-choir.yaml
prophet-mesh validate-repo-state specs/repo-state.yaml
prophet-mesh validate-router specs/model-router-interface.yaml
prophet-mesh validate-model-policy specs/model-task-policy.yaml
prophet-mesh validate-intake examples/customer-intake.accepted.json
prophet-mesh validate-evaluation examples/evaluation-report.accepted.json
```

## Status

This repository is the canonical product nucleus for the Prophet Mesh Agent Choir: architecture spec, machine-readable choir contract, repo-state architecture map, model-router interface contract, model task/domain policy, Michael and premium blueprints, lifecycle contract, customer intake workflow, evaluation harness, and CI gates. The next layer is runtime integration with model-router, Agentplane, memory-mesh, hellgraph, prophet-platform, agent-registry, agent-inbox, guardrail-fabric, and model-governance-ledger.
