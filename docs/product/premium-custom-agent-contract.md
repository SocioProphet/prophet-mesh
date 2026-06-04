# Premium Customer Agent Contract

## Purpose

Premium customer agents are Michael-derived agents. They may change customer-facing behavior, domain memory, connectors, workflows, deployment topology, and interface surface. They may not weaken the Prophet Mesh trust kernel.

## Commercial model

The premium line is sold as implementation plus recurring mesh operation:

1. Discovery and agent design.
2. Domain ontology and vocabulary mapping.
3. Memory connector integration.
4. Tool and workflow binding.
5. Policy pack design.
6. Evaluation harness configuration.
7. Deployment and attestation review.
8. Ongoing managed runtime, support, and governance updates.

## Customization matrix

| Surface | Customer configurable | Constraint |
| --- | --- | --- |
| Agent name | Yes | Must not imply authority the customer has not granted. |
| Domain vocabulary | Yes | Must preserve evidence and provenance semantics. |
| Memory connectors | Yes | Must be customer-approved and scoped by policy. |
| Tool allowlist | Yes | Capability execution requires policy authorization. |
| Workflow catalog | Yes | Material actions require evidence and authority. |
| UX shell | Yes | Must expose trust and audit affordances where required. |
| Deployment topology | Yes | Local, private cloud, managed cloud, and hybrid are valid. |
| Policy overlays | Restricted | May be more restrictive; may not disable the trust kernel. |
| Identity | No | Principal-bound identity is mandatory. |
| Evidence | No | Evidence packets are mandatory for material claims and transitions. |
| Attestation | No | Runtime transitions and important artifacts must be attestable. |
| Revocation | No | Grants, tools, and connectors must be revocable. |
| Audit | No | Governance trace cannot be disabled. |
| Lifecycle semantics | No | The canonical swarm lifecycle is invariant. |

## Customer intake schema

- Customer organization and operating domain.
- Agent name and desired surface identity.
- Primary workflows and success criteria.
- Required memory sources and data boundaries.
- Required connectors and tool permissions.
- Human approval points and escalation policy.
- Deployment target and identity provider.
- Audit, retention, and export requirements.
- Compliance obligations and restricted actions.

## Tenant isolation

Customer memory, tools, policies, logs, and attestations must be scoped to the customer tenant unless a signed agreement explicitly authorizes cross-tenant or first-party reuse. Customer data must not be absorbed into canonical Michael Agent state without explicit authorization.

## Acceptance criteria for a premium delivery

- The customer blueprint validates as `michael-derived`.
- All configured capabilities require evidence and policy gates.
- Tool and connector grants are short-lived or revocable.
- The customer can inspect lifecycle events and audit artifacts.
- The implementation SOW names every data source, tool, authority boundary, and runtime environment.
