# Security Report Template

Used for STANDARD and DEEP reviews (see `plays/code-review.md` for review
modes). For QUICK/PR reviews, a lighter-weight summary of just the
findings is usually sufficient — use judgment on how much of this
structure a small diff actually needs.

```markdown
# Security Assessment: <project/component name>

Date: YYYY-MM-DD
Review mode: QUICK | STANDARD | DEEP
Scope: <what was and was not reviewed>

## Executive Summary

Two to four sentences: overall risk posture, the most important
finding(s), and whether anything needs immediate attention. Written for
someone who will only read this section.

## Scope

What was reviewed (repository/paths/diff range), what was explicitly out
of scope, and why (e.g. "third-party vendored code excluded").

## Architecture

Brief description of the system relevant to security review: languages/
frameworks in use, major components, trust boundaries, deployment target
(see `plays/security-design.md`/`plays/threat-model.md` if a fuller
model exists elsewhere and can be linked instead of repeated here).

## Attack Surface

Entry points identified: API endpoints, file upload/download paths,
authentication flows, admin functionality, external integrations/
webhooks.

## Scanner Coverage

| Tool | Ran? | Coverage | Notes |
|---|---|---|---|
| Semgrep | yes/no | ... | ... |
| Gitleaks | yes/no | ... | ... |
| OSV-Scanner | yes/no | ... | ... |
| Trivy | yes/no | ... | ... |
| (ecosystem-native) | yes/no | ... | ... |

For anything not run, state the coverage impact and what fallback (if
any) was performed instead — see `plays/finding-validation.md`'s failure
handling guidance. Never state "no issues found" for a category that was
not actually checked by either a tool or an equivalent manual review.

## Findings Summary

```text
CRITICAL:       N
HIGH:           N
MEDIUM:         N
LOW:            N
INFORMATIONAL:  N
REJECTED:       N (kept separately, see below)
```

## Critical Findings

One `templates/finding.md` block per finding.

## High Findings

One `templates/finding.md` block per finding.

## Medium Findings

One `templates/finding.md` block per finding.

## Low Findings

One `templates/finding.md` block per finding.

## Informational Findings

One `templates/finding.md` block per finding (or a condensed list, if
there are many low-signal items — informational findings do not need
the full template if a one-line description is equally clear).

## Rejected Candidate Findings

A condensed list (per `plays/finding-validation.md`'s "Rejected
findings"), not the full template — candidate description and the reason
it was rejected. Do not clutter this with every rejected scanner
warning; keep the detailed list here and reference it from the main
findings summary above rather than expanding it inline.

## Residual Risks

Anything left over that was consciously not fixed (accepted risk,
deferred to a later phase, mitigated by a compensating control outside
the scope reviewed) and why.

## Recommended Actions

A short, prioritized punch list — not a restatement of every finding,
just what to do next and in what order.

## Verification Plan

How the fixes for the findings above will be confirmed once applied
(re-run the relevant scanners, re-run this review at a lighter mode
against the diff, specific manual tests) — see each finding's own
`### Verification` section for the per-finding detail this rolls up.
```
