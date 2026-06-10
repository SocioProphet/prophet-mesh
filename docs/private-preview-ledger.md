# Prophet Mesh Private-Preview Cross-Repo Status Ledger

Maintained under Lane D. All verification states are **binary**: verified / unverified.
Conflicting references to the same artifact path with divergent content hashes must be flagged explicitly — never silently resolved.

Last updated: 2026-06-10

---

## Spine repos — commit state

| Repo | Branch | Head commit | Verification state |
|---|---|---|---|
| `SocioProphet/prophet-mesh` | `main` | `6978e9b` (Gate runtime release bundle in CI) | **verified** — `make validate` + all tests pass |
| `SocioProphet/prophet-mesh` | `lane-a/adapter-back-ref` | PR #5 — adapter back-reference patch | **verified** — `make validate` + 35/35 tests pass (pending merge) |
| `SocioProphet/agent-registry` | `main` | latest | **verified** — `make validate` + 42 tests pass |
| `SocioProphet/model-router` | `main` | latest | **verified** — `make validate` + 11 tests pass |
| `SocioProphet/agentplane` | `main` | `faa767f42028ad0f2475c993700cdbef8490a38e` | **verified** — adapter validates, 113/114 tests pass (see stray-fixture note) |

---

## Agentplane adapter contract

| Field | Value | Verification state |
|---|---|---|
| Repo | `SocioProphet/agentplane` | verified |
| Path | `contracts/prophet-mesh/prophet-mesh-agentplane-adapter.v0.1.json` | verified |
| Merge commit | `faa767f42028ad0f2475c993700cdbef8490a38e` | verified — merged 2026-06-09, PR #274 |
| `content_sha256` | `38a3edb62813521a62f257f3f952271255d25dc3a05a14d6b96f04a6ff9b4268` | verified — `sha256sum` on local main at `faa767f` |
| `mode` | `dry_run_receipt_preview` | verified |
| `effect_enabled` | `false` | verified |
| `workspace_write_enabled` | `false` | verified |
| `executor_required` | `false` | verified |

---

## prophet-platform Health-AI demo readiness

| Item | State |
|---|---|
| `HealthAIDemoReadinessCard.vue` | **verified present** — committed through `61236509` |
| `make validate-health-ai-demo-readiness` | **verified passing** — confirmed end of prior session |
| FogStack/SVF/Workroom P2 fixture-backed runtime parity evidence | **verified complete** — through commit `61236509` |
| Lane F (live nonprod controller observations) | **unverified** — out of scope this session, requires explicit approval |

---

## Lane B — stray fixture finding

**Artifact**: `SocioProphet/agentplane` `tests/fixtures/receipts/integrity-evidence-request.valid.json`

**Finding**: Commit `faa767f` (Add Prophet Mesh dry-run receipt adapter) modified the path field in `integrity-evidence-request.valid.json` from `docs/example.md` to `repo/docs/example.md`. The fixture has `safe_root: "repo"`. The validator enforces that paths are relative to the safe root and must not include the root as a prefix. The change caused `integrity-evidence-result.valid.json` to fail validation (its path remains `docs/example.md`, correct).

**Test impact**: `test_valid_integrity_evidence_records_validate` fails. 1/114 tests fail in `make test`.

**Determination**: Gratuitous. The edit broke the test; it was not required by the adapter PR it was bundled with. The correct value is `docs/example.md` (relative, no root prefix).

**Action**: Recorded here. Not reverted. Revert is a trivial one-line change that should be done in a dedicated PR if the owner confirms. Do not bundle with Lane A or Lane C/D PRs.

---

## Non-production claim boundaries

The following claims are explicitly NOT made by this spine:

| Non-claim | Reason |
|---|---|
| Production deployment readiness | Spine is private-preview only; no customer data, no live services |
| Regulatory certification | No formal certification process has been run |
| Memory scope access beyond approved scopes | Validator enforces forbidden-scope rejection |
| External action without human approval | `email_reply` and `operations_plan` locked to `awaiting_approval` |
| Model availability as authorization | Authorization governed by policy gates independently of model availability |

---

## Remaining work

| Lane | Item | State |
|---|---|---|
| Lane A | prophet-mesh adapter back-ref patch | PR #5 open — pending merge |
| Lane C | Private-preview runbook | PR open (this PR) — pending merge |
| Lane D | Cross-repo ledger | This document — pending merge |
| Lane G | `prophet-mesh-memory-scope.v0.1.json` mirror in `memory-mesh` | Logged, not started |
| Lane E | Health-AI demo packaging/storyboard | Logged, not started |
| Lane F | Live nonprod controller observations | Out of scope — requires explicit approval and access confirmation |
| agentplane stray fixture | `integrity-evidence-request.valid.json` path revert | Identified, not reverted — owner decision required |

---

*Cross-reference: [`docs/private-preview-spine.md`](private-preview-spine.md)*
