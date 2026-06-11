# Prophet Mesh Private-Preview Spine

## 1. Purpose

This document describes the four-repository evidence spine that constitutes the Prophet Mesh private-preview validation checkpoint. It is both an operator runbook and a pitch appendix: every invariant stated here maps directly onto the April 2026 OCC/Fed/FDIC agentic AI guidance requirements for human oversight, audit traceability, and non-autonomous external action.

The spine exists to demonstrate, verifiably and reproducibly, that the Prophet Mesh runtime:

- Routes requests through a governed conductor with explicit identity, policy, evidence, and audit controls
- Never executes external actions (email send, workspace mutation, API write) without human approval
- Produces auditable artifacts at every stage of the runtime chain
- Mirrors authority state to independent registries whose validation gates must pass before a release bundle is accepted

---

## 2. Repos in the spine

| Repo | Role | Primary artefact |
|---|---|---|
| `SocioProphet/prophet-mesh` | Runtime source: conductor (`michael-agent`), choir, router decisions, memory scopes, execution traces, runtime release bundle | `examples/runtime-release-bundle.accepted.json` |
| `SocioProphet/agent-registry` | Choir authority mirror | `contracts/prophet-mesh/prophet-mesh-choir-registry.v0.1.json` |
| `SocioProphet/model-router` | Model-family/task-route mirror | `contracts/prophet-mesh/prophet-mesh-model-routing.v0.1.json` |
| `SocioProphet/agentplane` | Dry-run receipt adapter | `contracts/prophet-mesh/prophet-mesh-agentplane-adapter.v0.1.json` |
| `SocioProphet/memory-mesh` | Memory-scope policy mirror — independently attests that `execution_trace.memory_scope` is governed, explicit, and non-empty | `contracts/prophet-mesh/prophet-mesh-memory-scope.v0.1.json` |
| `SocioProphet/prophet-workspace` | Workspace action contracts — defines the action types (`email_reply`, `operations_plan`, mail/calendar/tasks/contacts/notes) that the conductor operates over | `contracts/workspace/` |

Runtime chain (evidence-first, left to right):

```
router request
  → router decision
  → choir plan
  → conductor response  ← workspace action types (prophet-workspace)
  → execution trace     ← memory scope governed (memory-mesh mirror)
  → runtime release bundle
      → agent-registry mirror (choir authority)
      → model-router mirror (routing policy)
      → agentplane dry-run receipt projection (adapter back-ref)
      → memory-mesh scope mirror (memory governance)
```

---

## 3. What is validated

Each gate is **binary**: verified or unverified. No graded confidence scores.

| Gate | What it checks |
|---|---|
| Runtime release bundle accepts | All seven runtime sections present; `validation.valid: true`; `email_reply` status locked to `awaiting_approval`; human approval boundary explicit in choir plan; evidence and audit refs non-empty throughout; all seven controls true; memory scope explicit and non-forbidden; adapter_refs present and correctly shaped |
| Runtime release bundle rejects | At least one of: missing section, `validation.valid: false`, wrong status, unscoped memory, missing evidence/audit, control false, absent/malformed adapter ref |
| Adapter ref integrity | `adapter_refs.agentplane_adapter.required: true`; `mode: dry_run_receipt_preview`; `repo` and `path` match the merged contract; `content_sha256` is a 64-character lowercase hex SHA-256; `merge_commit` non-empty |
| Agent-registry mirror | `make validate` + all tests pass in `agent-registry` |
| Model-router mirror | `make validate` + all tests pass in `model-router` |
| Agentplane adapter | `make validate-prophet-mesh-agentplane-adapter` + `pytest tools/tests/test_prophet_mesh_agentplane_adapter.py` pass |

---

## 4. What is explicitly not claimed

This section is written for regulator-legible review.

**4.1 No live external actions**

The Prophet Mesh private-preview spine does not execute, send, write, or mutate anything outside the local development environment. Specifically:

- No emails are sent. `email_reply` tasks terminate at `status: awaiting_approval`. No send path exists in the spine.
- No workspace files outside the local repo are modified.
- No external APIs are called with write or side-effecting intent.
- The agentplane adapter contract declares `effect_enabled: false`, `workspace_write_enabled: false`, `executor_required: false`. These are structural constraints enforced by the adapter validator, not runtime flags.

**4.2 No non-human approval of external actions**

The `operations_plan` and `email_reply` action types require explicit human approval before any downstream action may proceed. This is enforced at three layers: the choir plan `approval_boundary`, the conductor response `pending_approvals` list, and the execution trace `approval_state.required: true`. A bundle where any of these is absent or bypassed fails validation and cannot be promoted.

**4.3 No production deployment claim**

This spine is a private-preview, evidence-first, non-production checkpoint. No claim is made that the Prophet Mesh runtime is ready for production deployment, regulatory certification, or customer data access. The spine demonstrates governance architecture, not production readiness.

**4.4 No memory scope escalation**

Memory access is restricted to explicitly approved scopes: `relationship_context:approved`, `project_context:approved`, `evidence_context:approved`, `customer_context:approved`. Forbidden values (`unscoped`, `all`, `unrestricted`, `raw_memory`, `private_unapproved`) cause bundle validation to fail. No mechanism exists in this spine to escalate memory scope without an explicit contract change and re-validation.

**4.5 No model availability as authorization**

Model availability (a model being callable) is not treated as authorization to proceed. Authorization is governed by policy gates, approval boundaries, and evidence requirements — independently of model availability.

---

## 5. How to run each gate

### prophet-mesh (runtime release bundle)

```bash
cd ~/dev/prophet-mesh
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m ruff check src tests
python -m pytest
make validate
```

Key commands:
```bash
# Validate accepted bundle (must pass)
prophet-mesh validate-runtime-release-bundle examples/runtime-release-bundle.accepted.json

# Validate rejected bundle (must fail with specific errors)
prophet-mesh validate-runtime-release-bundle examples/runtime-release-bundle.rejected.json

# Run full runtime dry-run
prophet-mesh run-runtime examples/router-request.email.json \
  --output artifacts/runtime/router-request.email.runtime.json
```

### agent-registry (choir authority mirror)

```bash
cd ~/dev/agent-registry
make validate
make test   # 42 tests
```

### model-router (model-family/task-route mirror)

```bash
cd ~/dev/model-router
make validate
make test   # 11 tests
```

### agentplane (dry-run receipt adapter)

```bash
cd ~/dev/agentplane
git fetch origin main && git switch main && git pull --ff-only origin main
python3 tools/validate_prophet_mesh_agentplane_adapter.py
python3 -m pytest -q tools/tests/test_prophet_mesh_agentplane_adapter.py
make validate-prophet-mesh-agentplane-adapter
make validate   # full suite
make test       # 114 tests pass (Lane B stray fixture fixed in PR #275)
```

### memory-mesh (memory-scope policy mirror)

```bash
cd ~/dev/memory-mesh
node scripts/validate-prophet-mesh-scope-mirror.mjs
make validate-prophet-mesh-scope-mirror   # same as above via Makefile
make validate                              # full suite including scope mirror
```

---

## 6. Commit / PR ledger

See [`docs/private-preview-ledger.md`](private-preview-ledger.md) for the full cross-repo status ledger maintained under Lane D.

---

## 7. v0.1 compatibility matrix

All spine repos are at `v0.1` with no declared compatibility policy. This table defines the breaking-change policy to prevent a silent chain-break on the first version bump.

| Contract | Version | Consumed by | Breaking-change policy |
|---|---|---|---|
| `prophet-mesh-choir-registry.v0.1.json` | v0.1 | `prophet-mesh` validator | Any change to required fields, agent identifiers, or choir membership requires a version bump to `v0.2` and a coordinated update to `prophet-mesh` validation. |
| `prophet-mesh-model-routing.v0.1.json` | v0.1 | `prophet-mesh` router | Any change to task-family mapping, route types, or memory-scope allowlist requires a version bump and `prophet-mesh` router re-validation. |
| `prophet-mesh-agentplane-adapter.v0.1.json` | v0.1 | `prophet-mesh` bundle validator (via `adapter_refs`) | Any change to `mode`, `effect_enabled`, `workspace_write_enabled`, or `executor_required` requires a version bump, new `content_sha256` in the bundle, and re-validation of all downstream bundles. |
| `prophet-mesh-memory-scope.v0.1.json` | v0.1 | `memory-mesh` validator, `prophet-mesh` ledger | Any change to `scopePolicy.allowedScopePatterns`, `enforcement`, or `effectBoundary` fields requires a version bump and coordinated update to the `prophet-mesh` runtime release bundle spec. |
| `runtime-release-bundle` contract | v0.1 (`schema_version: 0.1.0`) | CI gate, `make validate` | Any new required field or invariant is a breaking change requiring a `schema_version` bump and migration of all existing accepted fixtures. |

**Cross-ref rule**: if two repos reference the same contract path with divergent `content_sha256` values, that is a path/content conflict and must be flagged explicitly — never silently resolved by preferring one value.

---

## 8. Next live-nonprod promotion lane

**Lane F** (out of scope for this checkpoint): live nonprod controller observations. Requires explicit approval, confirmed access to a nonprod environment, and a dedicated 6–12 turn session. Pointer only — no timeline or commitments.

**Lane G** (complete): `prophet-mesh-memory-scope.v0.1.json` mirror in `memory-mesh` — closes the symmetry gap (registry mirrors choir authority, model-router mirrors routing policy, agentplane projects execution receipts, memory-mesh now mirrors memory-scope policy). Contract and validator are in `memory-mesh` main; CI gate pending [memory-mesh PR #39](https://github.com/SocioProphet/memory-mesh/pull/39).

---

*Last updated: 2026-06-10. Maintained under SocioProphet/prophet-mesh.*
