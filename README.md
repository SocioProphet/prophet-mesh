# Prophet Mesh

Prophet Mesh is the distributed instantiation of the Michael Agent.

It packages Michael as a governed, evidence-native agent fabric: AgentUnit blueprints, swarm lifecycle compositions, memory/compute mesh integration, and policy-bound execution. The flagship product is the Michael Agent. Premium customers receive custom agent derivations that inherit the same trust kernel while changing domain memory, tools, persona surface, workflow bindings, and deployment topology.

## Product line

- **Michael Agent**: flagship general agent; evidence-first reasoning, contradiction handling, causal attribution, planning, and governance traceability.
- **Prophet Mesh Premium**: customer-specific agent packages built from the Michael trust kernel with custom capabilities, policies, memory adapters, and UX shells.
- **Prophet Mesh Enterprise**: private mesh deployment with organization policy, audit trails, key custody, and environment-specific runtimes.

## Architecture

```text
Michael Agent Spec
  -> AgentUnit Blueprint
  -> Prophet Mesh Runtime
  -> Swarm Lifecycle
  -> Evidence / Attestation Bus
  -> Memory Graph + Compute Mesh
  -> Customer Agent Packages
```

Core invariants:

1. Every agent has a principal, motive, policy, capabilities, memory scope, and lifecycle state.
2. Every lifecycle transition emits evidence.
3. Premium customization may extend the agent surface, but may not weaken evidence, policy, identity, revocation, or audit semantics.
4. Michael remains the canonical reference agent; customer agents are derivations, not forks of the trust kernel.

## Repository layout

```text
blueprints/               Agent blueprints and premium customization examples
docs/                     Architecture, product, and go-to-market notes
specs/                    Machine-readable contracts
src/prophet_mesh/          Reference Python package and CLI
tests/                    Contract and lifecycle tests
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
```

## CLI

```bash
prophet-mesh describe
prophet-mesh lifecycle
prophet-mesh validate-blueprint blueprints/michael-agent.yaml
```

## Status

This repository is the product nucleus: spec, lifecycle contract, reference package, and go-to-market skeleton. The next layer is runtime integration with Agentplane, memory-mesh, compute-mesh, and deployment targets.
