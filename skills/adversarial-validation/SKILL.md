---
name: adversarial-validation
description: Actively try to defeat a claimed protection or remediation using a systematic bypass checklist, for a bounded set of high-risk cases (confirmed CRITICAL, confirmed HIGH with more than one control, HIGH/CRITICAL remediations, auth/authz bypass, SSRF allowlists, path canonicalization, upload restrictions, deserialization, multi-finding attack chains). Use after skills/security-validate has confirmed a finding, or as part of a HIGH/CRITICAL remediation's mandatory re-validation, when the case matches the trigger list — not for every finding.
---

# Adversarial Validation

A systematic bypass-hunting checklist, applied for a bounded set of
high-risk cases — not a separate pass with its own outcome states,
though its own conclusion is recorded as a structured evidence tag
that never decides the outcome by itself (see "Results" below). Full
procedure in `plays/adversarial-validation.md`, which extends
`plays/security-remediation.md`'s existing mandatory re-validation
question ("can the protection be bypassed a different way?") with a
concrete technique list, rather than adding a second, parallel
remediation-validation pass.

## When to use

Only the cases `plays/adversarial-validation.md`'s "When this
checklist is worth the effort" section lists by default (confirmed
CRITICAL; confirmed HIGH with more than one control or a
normalization/encoding-dependent one; HIGH/CRITICAL remediation;
auth/authz bypass; SSRF allowlist; path canonicalization; upload
restrictions; deserialization; any other control-bypass claim; a
multi-finding attack chain's inter-step controls). Not every LOW
finding, and not a blanket second pass on everything
`skills/security-validate` already touched or on every ordinary
remediation. Does not apply to exposure-type findings (leaked
credentials, reachable known-CVEs) — there's no claimed protection or
fix to attack.

## A different objective, not a duplicate

For an original finding's claimed protection: `skills/security-validate`
asks "does the evidence hold up?" (reduces false positives); this
checklist asks "can I actively find a way past this control anyway?"
(reduces false negatives) — run as a genuinely separate pass, per the
play's "Independence" section. For a remediation: this is not a
separate pass at all — it's a systematic technique list for answering
a question `plays/security-remediation.md`'s mandatory re-validation
already asks.

## Results: existing outcome vocabulary, plus a structured evidence tag

A demonstrated bypass on a claimed protection moves a `REJECTED`
finding back to `CONFIRMED` (never leave it `REJECTED` once a concrete
bypass exists) and may require re-assessing severity even for a finding
that was already `CONFIRMED`; an unresolved lead is
`NEEDS_VERIFICATION`; nothing found leaves the existing status as
supporting evidence, not a new conclusion. For a remediation, results
feed `plays/security-remediation.md`'s existing `RESOLVED`/
`STILL_VULNERABLE`/`FIX_UNVERIFIED` outcomes directly — see the play's
"Results use existing vocabulary, not a new one" section. The
checklist's own conclusion is additionally recorded as a structured
tag alongside that outcome — `CONTROL_HOLDS`/`BYPASS_FOUND`/
`CONTROL_INCONCLUSIVE`/`NOT_APPLICABLE` for a finding,
`FIX_HOLDS`/`FIX_BYPASSED`/`FIX_INCONCLUSIVE`/`NOT_APPLICABLE` for a
remediation, or `CONTROL_HOLDS`/`BYPASS_FOUND`/`CONTROL_INCONCLUSIVE`
(no `NOT_APPLICABLE`) independently defined for a chain — every value
is non-deterministic evidence, never a decision by itself, and never
instead of the outcome above.
See the play's "Structured result metadata" section, including "Why
this is safe" for how this differs from the parallel state machine an
earlier draft was rejected for (and from this same batch's own first
attempt, which reintroduced that exact problem before review caught
it).

## Sequential fallback

No separate subagent/context available and a genuinely independent
second look isn't practical → record `NEEDS_VERIFICATION` (or
`FIX_UNVERIFIED` for a remediation), never let the existing
status/outcome stand unearned. See the play's "Sequential fallback"
section.

## Safety boundary

Static reasoning about exploit paths in code already under review —
not live testing against a running system, and never printing
unredacted secret values even when technique 4 would otherwise call
for demonstrating an alternate payload. If confirming a bypass would
require live testing, say so and stop.

## Output

No new artifact, and the outcome still uses this kit's existing
finding/remediation vocabulary — see
`plays/adversarial-validation.md`'s "Where this is recorded" for the
dedicated structured-result field and what invokes this play today.
