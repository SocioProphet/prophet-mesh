# Customer Intake Workflow

## Purpose

The customer intake workflow converts a premium prospect into a Michael-derived agent blueprint, implementation scope, and governed delivery plan. Intake must capture what the customer wants the agent to do, what authority the agent may exercise, what data it may touch, and which controls are mandatory before deployment.

## Intake stages

1. **Account and domain framing**: customer organization, business domain, operating environment, target users, and executive owner.
2. **Agent surface design**: requested agent name, audience, tone, language, user interface, and domain vocabulary.
3. **Workflow inventory**: jobs to be done, workflows to assist, workflows to automate, and workflows explicitly excluded.
4. **Authority mapping**: actions requiring human approval, actions the agent may recommend only, actions it may execute after approval, and actions never delegated.
5. **Memory and data boundaries**: approved sources, prohibited sources, retention requirements, export controls, tenant isolation, and first-party reuse permissions.
6. **Connector and tool design**: systems to read, systems to write, tool allowlists, runtime grants, revocation path, and audit obligations.
7. **Policy and compliance posture**: approval gates, restricted actions, regulated data, reporting requirements, and jurisdiction-specific constraints.
8. **Deployment topology**: managed cloud, private cloud, hybrid, local-first, identity provider, secrets ownership, and operational support model.
9. **Evaluation design**: benchmark tasks, evidence requirements, contradiction tests, failure modes, and acceptance criteria.
10. **SOW translation**: commercial scope, milestones, delivery artifacts, support cadence, and governance review schedule.

## Required outputs

- Customer intake record.
- Draft premium agent blueprint.
- Tool and connector register.
- Data-boundary memo.
- Policy and approval matrix.
- Evaluation harness plan.
- Deployment topology note.
- Implementation SOW inputs.

## Decision rules

- A premium agent cannot proceed without named authority boundaries.
- A connector cannot proceed without an owner, scope, policy gate, and revocation path.
- Customer data cannot enter canonical Michael state unless explicitly authorized.
- The agent may be customized, but identity, evidence, attestation, revocation, audit, and lifecycle semantics are invariant.

## Ready-for-design checklist

- Customer owner identified.
- Domain and user group identified.
- At least three target workflows described.
- Human approval points named.
- Memory sources listed and classified.
- Tool permissions listed and classified.
- Deployment topology selected.
- Evaluation tasks agreed.
- Data retention and audit requirements documented.
