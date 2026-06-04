# Prophet Mesh Agent Choir

## Decision

Prophet Mesh is not a single-agent product. It is an agent choir with a canonical conductor.

Michael Agent is the default conductor, relationship interface, and flagship experience. The broader product is the choir: specialist agents, memory stewards, router agents, governance sentinels, tool operators, and customer-derived conductor agents that all inherit the same trust kernel.

## Product distinction

Most assistants present one branded personality. Prophet Mesh presents one stable primary relationship while allowing customer-owned conductor agents to be trained, named, scoped, and governed for premium accounts.

The default experience is Michael. A premium organization can create a named derived conductor, but that conductor remains Michael-derived unless and until a separate authorized archetype is created. Derived conductors may change name, domain vocabulary, workflows, tone, interface, and memory scope. They may not bypass identity, policy, evidence, attestation, revocation, audit, or lifecycle semantics.

## Core model

```text
Human / Organization
  <-> Conductor Agent
        default: Michael Agent
        premium: customer-named Michael-derived conductor
  <-> Single Model Router Interface
  <-> Agent Choir
        memory steward
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

## Conductor responsibilities

The conductor agent owns the relationship surface. It chats, clarifies, remembers, negotiates intent, and decides which internal specialist or model path to invoke. It is not required to do every task itself. Its job is to coordinate the choir and synthesize the result into one coherent relationship-facing experience.

Required conductor properties:

- Stable primary identity.
- Relationship-aware memory.
- User-configurable communication surface within policy.
- Single router interface for model and agent pathways.
- Delegation to specialist agents.
- Synthesis of multi-agent results.
- Refusal or escalation when authority is missing.
- Preservation of trust-kernel invariants.

## Choir roles

| Role | Purpose |
| --- | --- |
| Memory Steward | Maintains relational, project, preference, and evidence memory boundaries. |
| Router Agent | Selects model, tool, and agent pathways through the model router. |
| Research Agent | Finds and normalizes source material. |
| Planning Agent | Produces execution plans, milestones, and risk registers. |
| Writing Agent | Drafts reusable written artifacts. |
| Coding Agent | Produces code, tests, patches, and repository changes. |
| Analytics Agent | Evaluates metrics, evidence, traces, and decision data. |
| Operations Agent | Coordinates workflows, tickets, deployments, and runbooks. |
| Creative Agent | Produces design, narrative, image, and concept artifacts. |
| Governance Sentinel | Enforces identity, policy, evidence, attestation, revocation, and audit. |

## Repo-state mapping

Prophet Mesh is the canonical repository for this spec and the commercial product package. Existing repositories become implementation layers:

- `SocioProphet/model-router`: the single routing interface.
- `SocioProphet/agentplane`: runtime substrate for agent execution.
- `SocioProphet/agent-registry`: registry of conductor and specialist agents.
- `SocioProphet/agent-inbox`: message/task intake plane for agents.
- `SocioProphet/memory-mesh`: contextual and relational memory substrate.
- `SocioProphet/hellgraph`: graph-backed identity, evidence, and relationship state.
- `SocioProphet/prophet-platform`: control plane, policy, evidence, deployment, and runtime integration.
- `SocioProphet/functional-model-surfaces`: model, adapter, dataset, eval, guardrail, tool, and routing contracts.
- `SocioProphet/guardrail-fabric`: safety and policy enforcement surface.
- `SocioProphet/model-governance-ledger`: evidence, evaluation, promotion, and rollback ledger.
- `SocioProphet/Noetica`, `SocioProphet/holmes`, and related intelligence repos: specialist reasoning and language-fabric lanes.

## Premium customer model

A premium customer does not buy a raw chatbot. They buy a named conductor and choir package:

1. Conductor identity: name, domain surface, tone, and operator relationship.
2. Choir composition: which specialist agents are enabled.
3. Memory scope: customer-approved sources, retention, and relationship boundaries.
4. Router policy: which model families and tools are allowed.
5. Governance: identity, evidence, attestation, revocation, audit, and lifecycle requirements.
6. Evaluation: proof that the conductor and choir preserve the trust kernel.

## Non-negotiable invariant

The conductor can be customized. The choir can be composed. The model family can be open. The trust kernel cannot be bypassed.
