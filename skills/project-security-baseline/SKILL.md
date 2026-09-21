---
name: project-security-baseline
description: Build and maintain a persistent, evidence-backed description of a target repository's security-relevant architecture (languages, frameworks, hosting, authentication, authorization, database, external services, secret sources, admin surfaces). Use when no baseline exists yet and security-sensitive work needs project context, or when explicitly asked to (re)build/refresh the security baseline.
---

# Project Security Baseline

Persistent, repo-wide architecture facts — distinct from a single
feature's design requirements. Full procedure in
`plays/project-security-baseline.md`.

## When to use

- No baseline exists yet (`.security/baseline.json` absent in the
  target repository) and the current task is security-sensitive enough
  to need project context beyond the immediate diff
- Explicit request: "rebuild security baseline", "refresh the project
  baseline"
- A prior baseline exists but its evidence has gone stale (see the
  play's "Freshness and invalidation") and an affected fact needs
  re-evaluation
- Not needed for a trivial, non-security-sensitive change — do not
  force a full build for a CSS-color edit

## Other uses of the word "baseline" in this kit

`skills/security-design` produces a throwaway requirements document
for **one feature**, before it's built — not this skill's persistent,
repo-wide fact base. `plays/finding-validation.md`'s "Baseline origin"
is a **per-finding** tag (was this specific vulnerability introduced by
the current diff, or did it pre-exist?) — not an architecture fact
either. Gitleaks also has its own "baseline"/allowlist file, unrelated
to this skill. See the play's "Other uses of the word 'baseline' in
this kit" section for the full disambiguation; don't conflate any of
them.

## What it answers

```text
Languages? Frameworks? Runtime? Hosting? Deployment OS?
Authentication? Authorization? Database? ORM? Frontend?
External services? File storage? Secret sources? Background jobs?
Admin surfaces? Public surfaces? Security middleware? Sensitive data?
```

## The fact schema

Every material claim carries **Value, Confidence (HIGH/MEDIUM/LOW/
UNKNOWN), Evidence, and Freshness** — never asserted without evidence,
and `UNKNOWN` is a legitimate answer rather than a framework-default
guess. Full rules, including how this confidence scale differs from
`plays/finding-validation.md`'s finding-confidence scale, are in the
play.

## Output

`.security/baseline.json` (machine-readable) and `.security/README.md`
(compact human-readable summary) in the **target repository being
reviewed** — not in this kit's own repository. Use
`templates/project-security-baseline.md` for both. Keep only the
compact summary in most task contexts; load a specific fact's full
evidence only when that fact is actually relevant to the current work.

## Relationship to security-change-detection

Baseline facts are meant to refine, not replace,
`skills/security-change-detection`'s NONE/LOW/MODERATE/HIGH
classification (e.g. a HIGH-sensitivity change to an internet-facing
endpoint with low baseline confidence deserves more scrutiny than the
same change to a well-understood internal tool) — see
`plays/project-security-baseline.md`'s "Output" section for exactly
what's wired today and what mapping remains open.
