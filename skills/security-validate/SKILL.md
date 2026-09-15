---
name: security-validate
description: Independently validate HIGH and CRITICAL candidate security findings before they are reported as confirmed. Use after security-review produces candidate findings, whenever a HIGH or CRITICAL severity finding needs confirmation.
---

# Security Validate

Independently re-examine HIGH/CRITICAL candidate findings. Do not assume
the reviewer (or scanner) is correct. Full procedure in
`plays/finding-validation.md`.

## When to use

Every HIGH or CRITICAL candidate finding produced by `security-review`,
before it is reported as confirmed. This is not optional for those
severities.

## What to do, per candidate

```text
Reconstruct the attack path
Confirm attacker control of the input
Confirm code reachability
Confirm sink behavior
Inspect sanitization
Inspect validation
Inspect authorization
Inspect framework protections
Inspect environmental constraints
Determine realistic impact
```

## Result

Every candidate resolves to exactly one of:

```text
CONFIRMED
REJECTED
NEEDS_VERIFICATION
```

Always with a stated reason. Example:

```text
Candidate: SQL injection
Reviewer evidence: user input reaches a database query.
Validator discovers: Entity Framework parameterizes the value.
Result: REJECTED
Reason: attacker-controlled input does not modify query structure.
```

## Goal

Aggressively reduce false positives. A finding that cannot be
demonstrated with a concrete attack path is not CONFIRMED — see the
confidence model in `plays/finding-validation.md`.

## Independence

This is a distinct pass from the one that produced the candidate. Where
the environment supports it (e.g. a separate reviewer subagent), run it
independently rather than self-confirming.
