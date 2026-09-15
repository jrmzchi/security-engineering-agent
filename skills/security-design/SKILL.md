---
name: security-design
description: Establish security requirements before or while implementing authentication, authorization, APIs, file upload/download, database operations, external HTTP requests, admin functionality, credential handling, cryptography, session/cookie handling, CORS, user-controlled redirects, background jobs, system commands, or filesystem access. Use before writing code for these, or when reviewing a design/architecture proposal.
---

# Security Design

Establish security requirements **before code is written**, or while a
design is being reviewed.

## When to use

Use this skill when designing or reviewing:

```text
authentication
authorization
APIs
file upload
file download
database operations
external HTTP requests
admin functionality
credential handling
cryptography
session handling
cookies
CORS
user-controlled redirects
background jobs
system commands
filesystem access
```

## What it answers

For the feature in question, work through:

```text
What are the assets?
Who are the actors?
What are the trust boundaries?
What input is attacker-controlled?
What operations are privileged?
What security controls are required?
What must never be trusted?
What should be logged?
What failure behavior is safe?
```

The full procedure, worked examples per feature type, and the output
format are in `plays/security-design.md`. A condensed per-feature-type
checklist is in `skills/security-design/references/design-checklist.md`
for fast lookup once you already know the pattern.

## Output

Produce implementation requirements using `templates/security-design.md`
**before** the feature is implemented — not as a retrospective review.
Scale detail to the feature's actual risk: a public read-only listing
endpoint does not need the same depth as an admin credential-reset flow.

## Relationship to security-review

`security-design` is proactive (used before/during implementation).
`security-review` (see `skills/security-review/SKILL.md`) is reactive
(used after/during implementation, against actual code). Requirements
produced here should be checked for compliance during the later review.
