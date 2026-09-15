# Security Design Template

Used with `plays/security-design.md`. Answer each question for the
feature being designed; skip a question only when genuinely not
applicable, and say so explicitly rather than omitting it silently.
Scale detail to the feature's actual risk (see that play's closing note).

```markdown
# Security Design: <feature name>

Date: YYYY-MM-DD
Feature: <one-line description of what is being built>

## Assets

What is worth protecting here.

## Actors

Every party that interacts with this feature.

## Trust Boundaries

Where the trust level changes for this feature specifically.

## Attacker-Controlled Input

Everything originating on the other side of a trust boundary that this
feature processes.

## Privileged Operations

What this feature does that reads/writes another user's data, changes
permissions, spends money, executes on the server, or touches the
filesystem.

## Required Security Controls

For each privileged operation and each attacker-controlled input: the
specific control (authentication, authorization — object AND function
level, input validation, output encoding, rate limiting, parameterization,
allowlisting).

## What Must Never Be Trusted

The explicit inverse of the attacker-controlled-input list: client-side
checks, hidden fields, unverified claims, IDs implying ownership.

## Logging

What should be logged (auth events, authorization denials, privileged
actions) and what must NOT be logged (secrets, full sensitive payloads).

## Failure Behavior

For each check/call above: does failure result in deny/reject (correct,
fail-closed) or allow/continue (needs to be fixed if so)?

---

These requirements are the baseline `skills/security-review` should
check the implementation against once the feature is built.
```
