# Threat Model Template

Used with `plays/threat-model.md`. Scale the depth of every section to
the project's actual complexity and risk — see that play's "Scale to
project complexity" guidance. A small internal tool may fill this out in
a few lines total; do not pad it to look thorough.

```markdown
# Threat Model: <system/feature name>

Date: YYYY-MM-DD
Scope: <what this threat model covers, and what it explicitly does not>

## Assets

What needs protecting (data, credentials, availability, integrity,
reputation) — named concretely.

## Actors

Every party that interacts with the system: end users, admins,
background services, other internal systems, external third parties,
and plausible attackers (with a one-line motive each where it clarifies
the threat).

## Entry Points

Every place an actor interacts with the system (UI, API, CLI, file
imports, webhooks, message queues, admin tools).

## Trust Boundaries

Where the trust level changes between actors/components.

## Data Flows

For sensitive data specifically: where it travels, at rest and in
transit, and who/what can read it at each hop.

## Privileges

What each actor/component can do, and what it should not be able to do.

## Threats

For each relevant entry point/trust boundary, what could go wrong.
STRIDE categories may be used where helpful (Spoofing, Tampering,
Repudiation, Information disclosure, Denial of service, Elevation of
privilege) — apply only the categories relevant to what was actually
found above, not all six for every entry point.

## Mitigations

For each threat judged worth addressing: the concrete mitigation, and a
pointer to `skills/security-design` output (see
`templates/security-design.md`) for anything that still needs
implementation-level requirements worked out.

## Residual Risks

What remains after mitigation, and why it is accepted (cost, likelihood,
business decision) — with who signed off on accepting it, if that
matters for this project's process.
```
