# Play: Secure Development Workflow

Authoritative procedure connecting security into the normal development
lifecycle, proportionally — not a full audit after every change. This
play defines the workflow; `AGENTS.md`'s "Before implementing a
meaningful software change" and `CLAUDE.md`'s "Proactive workflow"
section route ordinary coding requests through it, so a plain "add an
endpoint" request triggers this, not just an explicit review request.

## Workflow

```text
Understand request
        |
Classify requested change (skills/security-change-detection)
        |
NONE / LOW / MODERATE / HIGH
        |
Pre-implementation security design if HIGH (skills/security-design)
        |
Implementation
        |
Inspect actual changes (git diff, including untracked files)
        |
Re-classify implemented change (skills/security-change-detection)
        |
Select relevant security domains (skills/security-review's "Where to
    look next" table)
        |
Select justified scanners (plays/scanner-selection.md)
        |
Determine review budget (plays/review-budget.md) -- depth only, never
    which domains
        |
Targeted security review (skills/security-review)
        |
Candidate findings
        |
Independent validation where required (skills/security-validate)
        |
Security Gate (skills/security-gate)
        |
Remediation if required (plays/security-remediation.md)
        |
Independent re-validation
        |
Regression verification
        |
Completion
```

## Proportionality is the point

```text
NONE     -> stop here. No design, no review, no scanner, no summary.
LOW      -> lightweight diff check only (plays/security-change-detection.md).
MODERATE -> targeted review: load only the relevant play(s)/reference(s);
            also check skills/security-design's own activation list
            independently (see plays/security-change-detection.md's
            MODERATE section).
HIGH     -> full path: design before code (when the pre-code
            classification is HIGH), targeted review after.
```

**The gate itself is not tied to this table.** Whenever targeted review
produces a finding, the gate applies regardless of which sensitivity
row got you there — see `skills/security-gate`'s "When to use". A
MODERATE change that happens to turn up a CONFIRMED HIGH finding still
gets gated; it just didn't require design beforehand.

Do not turn every code change into a STANDARD or DEEP audit. That
defeats the purpose of having a classifier at all, and per
`AGENTS.md`'s "Prefer more reliable findings over more findings" bias,
volume without proportionality is itself a quality problem — it trains
the person reading these summaries to stop reading them.

## Pre-implementation security design (HIGH only)

Use `skills/security-design` (procedure: `plays/security-design.md`).
Determine assets, actors, trust boundaries, attacker-controlled inputs,
privileged operations, required controls, what must never be trusted,
logging, and failure behavior — scaled to the actual feature, not
padded. Example:

```text
Feature: Authenticated file download

Security requirements:
- authentication required
- object authorization required
- client-provided filename must not become a trusted physical path
- canonical path must remain inside configured root
- files outside configured root must be inaccessible
- error responses must not disclose physical server paths
- relevant authorization/path failures should be logged safely
```

Implementation should then satisfy these requirements — and the
post-implementation review below checks that it actually did, not just
that some code was written.

## Post-implementation inspection

When Git is available:

```bash
git status --short
git diff
git diff --cached
```

**Account for untracked files** — `git diff` alone does not show them.
Do not rely only on changed lines when surrounding, unchanged code
participates in the new attack path (a newly added controller calling
an existing helper that does unsafe filesystem operations puts that
helper in scope — see `plays/code-review.md`'s "Diff-aware review").

## Re-classification after implementation

Run `skills/security-change-detection` again against what was actually
built. A request classified MODERATE from intent can come out HIGH once
the actual code is visible (or vice versa) — the workflow branches on
the *later* classification for what review/gate steps are required.

## Review budget: computed here, defined in plays/review-budget.md

Immediately after scanner selection and before targeted review starts,
compute `plays/review-budget.md`'s level (`MINIMAL`/`FOCUSED`/`ELEVATED`/
`AUDIT`) from the (re-)classification just established, using that
play's "Default starting point" table and Factors as the actual
procedure — this workflow does not restate either. The result governs
how much material `skills/security-review`'s targeted review step loads
within the domains already selected above (see that skill's "Scope"
step) — it never changes which domains are selected, and never lowers
what `plays/finding-validation.md`'s independent-validation requirement
(via `skills/security-validate`) or an explicitly requested `DEEP`
review mode already demand (see `plays/review-budget.md`'s "The floor
this play cannot lower").

## Targeted review

"Targeted" means: review only the security domains the (re-)
classification identified, using progressive disclosure — load the
specific play(s)/reference(s) that apply, not the whole skill tree.
Domain-to-play routing is **not** a separate table maintained here or
in `plays/scanner-selection.md` — it is `skills/security-review/SKILL.md`'s
existing "Where to look next" table and `skills/security-review/references/quick-reference.md`,
the same ones QUICK/STANDARD/DEEP already use; TARGETED reuses them at
finer grain rather than competing with them. See
`plays/scanner-selection.md` for TARGETED's formal definition and the
separate question of which *scanner tools* (Semgrep/Gitleaks/etc.) are
justified for the change. TARGETED sits alongside, and does not
replace, `skills/security-review`'s existing QUICK/STANDARD/DEEP modes
(see `plays/code-review.md`) — TARGETED is the mode this workflow uses
for ordinary development-time changes; QUICK/STANDARD/DEEP remain
available for an explicitly requested review of a diff or repository.

## Validation, gate, remediation

```text
HIGH/CRITICAL candidate -> skills/security-validate (never skip this
    for these severities)
Gate decision -> skills/security-gate (PASS/BLOCK/AWAITING_VALIDATION/
    PASS_WITH_WARNINGS/PASS_WITH_ACCEPTED_RISK)
Confirmed finding needing a fix -> plays/security-remediation.md
```

## Completion summary

Concise, not a full audit report, unless one was explicitly requested:

```text
Security Review

Change sensitivity: HIGH
Domains reviewed: authorization, filesystem, path handling
Findings: 0 confirmed HIGH/CRITICAL, 1 MEDIUM resolved
Gate: PASS
Verification: Path traversal regression test passed.
```

For a NONE-classified change, do not add a security summary at all
unless it adds real information.

## Ownership boundaries for this and future workflow-layer plays

This play, `plays/security-gate.md`, `plays/security-remediation.md`,
and `plays/scanner-selection.md` sit on top of the V1 plays — they
decide *when* and *whether* something runs, not *what* a finding's
status vocabulary is or *which* play covers a given vulnerability
class. Two files are the sole owners of those, and workflow-layer plays
must reference them rather than re-derive or restate:

```text
Finding status/confidence/severity vocabulary
    -> plays/finding-validation.md + templates/finding.md
       (CONFIRMED/REJECTED/NEEDS_VERIFICATION, HIGH/MEDIUM/LOW
       confidence, CRITICAL..INFORMATIONAL severity)

Symptom -> play/reference routing
    -> skills/security-review/SKILL.md's "Where to look next" table +
       skills/security-review/references/quick-reference.md
```

A workflow-layer play may introduce a *new* status for a concept V1
never had (this project's own `AWAITING_VALIDATION`,
`RISK_ACCEPTED`, `FIX_UNVERIFIED`, etc. are exactly that) — what it must
not do is redefine an existing one, or build a second routing table
covering ground the two files above already cover. When in doubt, add
a pointer instead of a new table.

## This does not replace explicit workflows

A user can still ask directly for `Review this repository using
STANDARD security review`, `Perform a DEEP security assessment`, or
`Threat-model this feature` — those go straight to
`skills/security-review`/`skills/threat-model` as before. This play
adds proactive routing for ordinary development requests; it does not
remove or gate the explicit entry points.
