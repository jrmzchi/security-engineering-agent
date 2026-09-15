---
name: security-change-detection
description: Determine whether a requested or implemented software change touches a security-relevant attack surface, and how sensitive it is (NONE/LOW/MODERATE/HIGH). Use before implementing any non-trivial change, and again after implementation to re-check the actual diff. This is a lightweight classifier, not a full audit.
---

# Security Change Detection

Determines the security sensitivity of a change and what workflow it
needs — without performing a full audit itself. This is the entry
point `plays/secure-development-workflow.md` starts from.

## When to use

Before implementing any non-trivial change (to determine whether
`skills/security-design` runs first), and again after implementation
to re-check the actual diff.

## What it answers

```text
What security sensitivity does this change have?
What security domains are affected?
What security workflow is required?
Which scanners, if any, are justified?
```

Full procedure, the four sensitivity levels (NONE/LOW/MODERATE/HIGH)
with examples, detection signals per language/framework, and the
intent-vs-implementation distinction: `plays/security-change-detection.md`.

## Classify twice

Once from the request/intent, before writing code — this determines
whether `skills/security-design` runs first. Once from the actual diff,
after writing code — actual implementation can introduce security
behavior the original request never mentioned (a "simple" endpoint that
turns out to read a file by user-supplied path, say). Both passes use
the same procedure in `plays/security-change-detection.md`.

## Sensitivity is not severity

`HIGH` here means "this change touches a security-sensitive area and
needs a workflow" — it does not mean a vulnerability was found. Do not
confuse a HIGH-*sensitivity* change with a HIGH-*severity* finding (that
scale lives in `plays/finding-validation.md` and only applies once an
actual candidate finding exists).

## Output feeds the workflow, not a standalone report

The result of this classification determines what happens next per
`plays/secure-development-workflow.md` — which domains
`skills/security-review` loads (progressive disclosure, see that
skill's "Where to look next" table), which scanners
`plays/scanner-selection.md` says are justified, and whether
`skills/security-design` runs before implementation. Do not produce a
verbose standalone report for a NONE/LOW change — see
`plays/security-change-detection.md`'s "No security theater" note.
