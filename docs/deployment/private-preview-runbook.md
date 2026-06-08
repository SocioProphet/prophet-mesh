# Prophet Mesh Private Preview Runbook

## Purpose

This runbook defines the minimum deployment-smoke path for Prophet Mesh private preview. It is intentionally non-networked and deterministic at this stage: the goal is to prove that a request can move through the registered Agent Choir runtime with evidence, audit, approval, and validation controls intact.

## Deployment posture

Current status: ready for private-preview runtime smoke.

Not yet claimed:

- Production autonomy.
- External tool execution.
- External email sending.
- Persistent multi-tenant service operation.
- Live model invocation.
- Customer data processing.

## Required local gate

Run from the repository root:

```bash
python -m pip install -e '.[dev]'
python -m ruff check src tests
python -m pytest
make validate
```

Expected result:

- Ruff passes.
- Pytest passes.
- Agent registry validates.
- Runtime emits `artifacts/runtime/router-request.email.runtime.json`.
- Runtime artifact parses as JSON.
- Runtime artifact has `validation.valid=true`.
- Runtime artifact has `execution_trace.status=awaiting_approval`.

## Runtime smoke command

```bash
prophet-mesh run-runtime examples/router-request.email.json \
  --output artifacts/runtime/router-request.email.runtime.json
```

The runtime must generate a complete chain:

```text
router request
  -> router decision
  -> choir execution plan
  -> conductor response envelope
  -> execution trace
```

## Required invariants

The runtime smoke is valid only when all of the following are true:

- The conductor exists in `agents/`.
- The conductor is active.
- The conductor is `kind: conductor`.
- Every selected specialist exists in `agents/`.
- Every selected specialist is active.
- Every selected specialist is `kind: specialist`.
- The router decision preserves identity, policy, evidence, attestation, revocation, audit, and tenant isolation controls.
- The choir plan preserves evidence and audit on every step.
- Email reply tasks are not direct-allow execution paths.
- External action remains behind a human approval boundary.
- The execution trace records pending approval state.

## Registered default choir

The private-preview runtime expects these manifests:

- `agents/michael-agent.yaml`
- `agents/memory-steward.yaml`
- `agents/writing-agent.yaml`
- `agents/governance-sentinel.yaml`
- `agents/research-agent.yaml`
- `agents/coding-agent.yaml`
- `agents/analytics-agent.yaml`
- `agents/operations-agent.yaml`
- `agents/creative-agent.yaml`

## Evidence handling

Generated runtime artifacts are local evidence bundles and are ignored by git under `artifacts/runtime/`.

Curated examples should be promoted explicitly into `examples/` or a future release bundle. Do not commit incidental local runtime smoke output directly from `artifacts/runtime/`.

## Release decision

A private-preview build can proceed only when:

```bash
make validate
```

passes on a clean `main` checkout and the runtime artifact verifier confirms:

```text
validation.valid = true
execution_trace.status = awaiting_approval
```

## Next hardening milestones

1. Add memory-scope runtime contract.
2. Add persisted trace export format for release bundles.
3. Add Agent Registry mirror into `SocioProphet/agent-registry`.
4. Add Model Router mirror into `SocioProphet/model-router`.
5. Add Agentplane adapter for real task execution.
6. Add private-preview API surface.
