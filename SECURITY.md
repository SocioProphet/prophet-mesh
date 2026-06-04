# Security Policy

Prophet Mesh treats agent execution as a governed, revocable capability grant.

Required controls:

- Every agent action must resolve to a principal, capability, artifact delta, locale, event, and motive.
- Premium custom agents must preserve tenant isolation and customer-scoped policy boundaries.
- Tools and connectors must be declared in capabilities and authorized by policy before execution.
- Runtime grants must be short-lived and revocable.
- Evidence packets must be emitted for lifecycle transitions and material actions.
- Customer data must not be copied into first-party Michael state unless an explicit customer agreement permits it.

Report security issues privately to the maintainers while this repository is private or in controlled preview.
