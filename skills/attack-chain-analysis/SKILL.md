---
name: attack-chain-analysis
description: Determine whether multiple confirmed findings combine into a more serious attack chain than any of them individually suggest, and structure that chain with preconditions, ordered steps, boundary transitions, and combined severity. Use after a review has produced multiple CONFIRMED findings in the same area, to check whether they interact rather than treating each in isolation.
---

# Attack Chain Analysis

Whether multiple findings combine into something worse than any one of
them alone. Full procedure in `plays/attack-chain-analysis.md`, which
formalizes `plays/finding-validation.md`'s existing "Vulnerability
chaining" section rather than replacing it.

## When to use

- Multiple CONFIRMED findings exist in the same area of a review, and
  exploiting one plausibly enables reaching another
- Not needed for a single isolated finding, or for findings with no
  plausible causal connection — see "When a chain is real" below before
  spending effort looking for a chain that isn't there

## When a chain is real

Keep `plays/finding-validation.md`'s existing guardrail's core
requirement: **exploiting the first finding must actually enable
reaching the second** — not merely make it more convenient or provide
a hint. State that requirement concretely per consecutive pair of
steps: name the specific fact the earlier step establishes that the
later step's reachability depends on. If a later step would still be
reachable with an earlier one removed, that earlier step isn't a
required link — see the play's "When a chain is real" section for the
full worked contrast.

## Confidence and severity are not shortcuts from finding-validation.md

Chain confidence reuses `plays/finding-validation.md`'s HIGH/MEDIUM/LOW
scale (plus `NEEDS_VERIFICATION`) — not a new scale — bounded by the
lower of (a) each component finding's own confidence and (b) how
directly evidenced the preconditions linking them are; a chain built on
a MEDIUM-confidence finding can't itself be HIGH. Chain severity is
**not** the highest severity among the component findings — it's
assessed against the combined path using the same factors
`plays/finding-validation.md`'s severity model already lists (plus one
this play adds: persistence — whether the gained access outlives the
triggering request/session). See the play for the worked example
showing two MEDIUM findings combining into a CRITICAL chain (upload +
an execution-enabled directory = RCE).

## Deduplication

Component findings are reported once each, normally, using
`templates/finding.md`. The chain is an additional layer that
references them by ID/title — it does not restate their content.

## Output

Use `templates/attack-chain.md` — see
`plays/attack-chain-analysis.md`'s "Wired consumers" and "Relationship
to the Security Gate" for which consumers gate, trigger on, or report
this record today.
