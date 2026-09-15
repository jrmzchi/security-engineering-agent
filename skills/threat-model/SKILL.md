---
name: threat-model
description: Perform a lightweight threat model for a new project or a significant new feature, scaled to project complexity. Use before implementation of a system with meaningful trust boundaries, sensitive data, or privileged operations.
---

# Threat Model

Perform a lightweight threat model, scaled to the size of what is being
built. Full procedure in `plays/threat-model.md`.

## When to use

- A new project or service, before significant implementation begins
- A significant new feature that introduces a new trust boundary,
  new sensitive data, or new privileged operation
- Not needed for small, low-risk internal utilities — scale down or skip

## Core concepts

```text
Assets            what needs protecting (data, credentials, availability)
Actors             who interacts with the system (users, admins, services, attackers)
Entry points        where actors interact with the system
Trust boundaries     where trust level changes
Data flows          how data moves across those boundaries
Privileges          what each actor/component can do
Threats             what could go wrong
Mitigations          what reduces the threat
Residual risks       what remains after mitigation
```

STRIDE may be used where helpful (Spoofing, Tampering, Repudiation,
Information disclosure, Denial of service, Elevation of privilege). Do
not force every project through every STRIDE category — apply the
categories that are relevant to the entry points and trust boundaries
actually present.

## Do not over-build this

Do not produce a large enterprise threat-model document for a small
application. A CLI tool with no network exposure and no sensitive data
needs a few lines. An internet-facing service handling payment data
needs the full treatment.

## Output

Use `templates/threat-model.md`. Feed identified threats and required
mitigations into `skills/security-design` for the features that need
concrete implementation requirements.
