# Michael Agent Product Requirements

## Product thesis

Michael Agent is the flagship Prophet Mesh product. It is not a generic chat assistant and not a persona layer. It is the canonical agent archetype for governed reasoning, evidence handling, contradiction pressure, causal attribution, planning, and auditable action.

Prophet Mesh is the distributed instantiation of Michael Agent. The mesh gives Michael state, memory, tools, lifecycle, policy, attestation, revocation, and deployment topology.

## Primary users

- Operators who need a high-trust agent for strategic synthesis and execution planning.
- Teams that need durable memory, evidence trails, and repeatable agent behavior.
- Premium customers that need a Michael-derived agent customized to their domain, connectors, workflows, and deployment constraints.
- Enterprise buyers that need private deployment, auditability, identity integration, policy controls, and tenant isolation.

## Product editions

| Edition | Buyer | Scope |
| --- | --- | --- |
| Michael Agent | Individuals and teams | Canonical flagship agent with evidence-first reasoning and governed planning. |
| Prophet Mesh Premium | Professional teams | Michael-derived custom agent with customer memory, tools, workflow bindings, and UX surface. |
| Prophet Mesh Enterprise | Regulated and infrastructure-heavy organizations | Private mesh deployment with policy packs, audit, identity integration, and environment-specific runtime controls. |

## Core capabilities

1. Evidence intake: ingest, normalize, preserve, cite, and reason over evidence packets.
2. Belief-state management: maintain active claims, dependencies, confidence, contradictions, and unresolved questions.
3. Causal attribution: update causal models as new evidence or outcomes arrive.
4. Counterexample search: actively pressure-test claims, plans, and narratives.
5. Governed action planning: produce execution plans that name authority, motive, risks, and required evidence.
6. Memory graph recall: retrieve durable context with provenance and scope discipline.
7. Lifecycle traceability: bind significant state transitions to evidence events and attestations.

## Trust-kernel invariants

The following properties are product requirements, not implementation details:

- Principal-bound identity.
- Policy checks before capability execution.
- Evidence packets for material claims and lifecycle transitions.
- Attestation for runtime transitions and important artifacts.
- Revocation for tools, grants, connectors, and customer-scoped actions.
- Audit trace for operator-facing and customer-facing actions.

## Non-goals

Michael Agent must not be positioned as an unconstrained automation bot, a bypass for organizational authority, a substitute for legal/compliance approval, or a customer data sink without explicit data-boundary agreements.

## Acceptance criteria for v0.1

- A user can inspect the canonical Michael blueprint.
- A premium customer blueprint can be validated as Michael-derived.
- The lifecycle state machine rejects invalid transitions.
- Product docs distinguish the flagship agent from premium customization.
- Every premium customization path preserves the trust kernel.
