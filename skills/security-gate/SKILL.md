---
name: security-gate
description: Apply a deterministic PASS/BLOCK decision to a completed security review based on independently-validated findings and any attack-chain records. Use whenever a security-sensitive development task produced candidate findings, after HIGH/CRITICAL candidates have gone through skills/security-validate.
---

# Security Gate

Turns validated findings into a deterministic completion decision. This
is the last step of `plays/secure-development-workflow.md`, not a
replacement for validation — it consumes validation's output, it does
not perform validation itself.

## Outcomes

```text
PASS
PASS_WITH_WARNINGS
AWAITING_VALIDATION
BLOCK
PASS_WITH_ACCEPTED_RISK
```

Full policy table (which finding status/severity — or chain-record
Confidence/Chain severity — maps to which outcome), the precedence
order for aggregating multiple findings and chain records, the rule
that an unvalidated finding cannot trigger a HIGH/CRITICAL BLOCK on
scanner severity alone, and explicit-risk-acceptance handling:
`plays/security-gate.md`.

## The one rule that matters most

**Scanner severity alone must never BLOCK.** A HIGH/CRITICAL candidate
that has not been through `skills/security-validate` resolves to
`AWAITING_VALIDATION`, not `BLOCK` — see `plays/security-gate.md`'s
policy table. This is what keeps the gate from becoming noise that gets
routinely overridden. Note the outcome name is deliberately not
`NEEDS_VERIFICATION` — that name is already used, with a different
meaning, for a finding that *was* validated and the validator still
couldn't confirm or reject it (see `plays/security-gate.md`'s "Handling
an unresolved HIGH/CRITICAL candidate" for why that case actually
`BLOCK`s rather than passing through).

## Chain records are a second gate input

An attack chain record (`plays/attack-chain-analysis.md`) is not
itself a finding and doesn't go through `skills/security-validate` —
see `plays/security-gate.md`'s "Inputs this play consumes" and
"Default policy" table for exactly how it's gated, independent of each
component finding's individual outcome.

## When to use

Whenever candidate findings exist, from any source — `skills/security-review`,
a `security-team-lead`-coordinated audit, or a
`plays/security-remediation.md` re-validation pass — **regardless of
the change's sensitivity level**. A NONE/LOW change with no findings
has nothing to gate in practice; that is what skips it, not the
sensitivity label itself. Do not treat "MODERATE" as an exemption from
gating a CONFIRMED finding that targeted review happened to turn up.

## Risk acceptance is not the same as passing cleanly

If the user explicitly accepts a BLOCK-eligible finding rather than
resolving it, the outcome is `PASS_WITH_ACCEPTED_RISK`, and the
finding's record must retain its original severity/confidence and the
acceptance reason — see `plays/security-gate.md`'s "Explicit risk
acceptance" section. Do not silently rewrite it as an ordinary `PASS`.
