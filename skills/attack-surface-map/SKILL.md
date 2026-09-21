---
name: attack-surface-map
description: Build and maintain a persistent, evidence-backed graph of a target repository's entry points, trust boundaries, privileged operations, and sensitive sinks. Use when no map exists yet and security-sensitive work needs to know what depends on what, or when explicitly asked to (re)build/refresh the attack surface map.
---

# Attack Surface Map

Persistent, repo-wide graph of security-relevant entry points,
boundaries, and sinks. Full procedure in
`plays/attack-surface-mapping.md`.

## When to use

- No map exists yet (`.security/attack-surface.json` absent in the
  target repository) and the current task needs to know what entry
  points/controls/sinks exist beyond the immediate diff
- Explicit request: "rebuild the attack surface map", "refresh the
  attack surface map"
- A later task needs reverse-dependency reasoning (which entry points
  are affected by a changed shared component) — that capability
  consumes this map rather than rebuilding it
- Not needed for a trivial, non-security-sensitive change

## Not the same thing as an attack-path chain

`plays/finding-validation.md`'s attack-path model is a linear chain
built fresh for one candidate finding, then discarded. This skill
produces a persistent, reusable graph — many nodes and edges, built
once, consulted repeatedly. Consulting the map can speed up building a
chain for a specific finding, but never substitutes for independently
verifying that finding's actual path — see the play's "Not the same
thing as an attack-path chain" section.

## Vocabulary

16 node types (`ENTRY_POINT`, `TRUST_BOUNDARY`,
`AUTHENTICATION_CONTROL`, `AUTHORIZATION_CONTROL`,
`VALIDATION_CONTROL`, `SERVICE`, `DATA_STORE`, `FILESYSTEM`,
`EXTERNAL_SERVICE`, `PROCESS_EXECUTION`, `QUEUE`, `BACKGROUND_JOB`,
`ADMIN_SURFACE`, `SENSITIVE_SINK`, `SECRET_SOURCE`,
`CLIENT_SIDE_SINK`) and 14 edge types (`CALLS`, `READS`, `WRITES`,
`AUTHENTICATES`, `AUTHORIZES`, `VALIDATES`, `REDIRECTS_TO`, `FETCHES`,
`EXECUTES`, `UPLOADS_TO`, `DOWNLOADS_FROM`, `DESERIALIZES`,
`PUBLISHES`, `CONSUMES`) — full definitions in the play. Use only these;
don't invent new ones without updating the play's tables first.

## Evidence-backed, never hallucinated

Every node and edge cites a file/symbol observation, using the same
Value/Confidence/Evidence discipline as
`skills/project-security-baseline`. A route that can't be confidently
resolved (dynamic routing, reflection) gets `confidence: LOW` and
`status: NEEDS_VERIFICATION` — never asserted as if resolved.

## Don't over-model

Map only what's useful for security reasoning — entry points, trust
boundaries, privileged operations, sensitive sinks, and the controls
between them. An ordinary internal helper with no privileged operation,
no trust-boundary crossing, and no sensitive data isn't a node.

## Output

`.security/attack-surface.json` in the **target repository being
reviewed** — not in this kit's own repository. Use
`templates/attack-surface-map.md` for the schema.
