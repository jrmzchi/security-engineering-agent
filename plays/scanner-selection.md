# Play: Scanner Selection

Authoritative procedure for the TARGETED review mode's definition, and
for which scanner *tools* (Semgrep/Gitleaks/OSV-Scanner/Trivy/
ecosystem-native audit) are justified for a given change. This play
does **not** own domain-to-play routing (which play/reference to read
for a given symptom) — that table already exists in
`skills/security-review/SKILL.md`'s "Where to look next" and
`skills/security-review/references/quick-reference.md`; duplicating it
here would just be a second copy that drifts from the first. See
`plays/finding-validation.md` and this project's general preference for
proportionate, reliable coverage over indiscriminate volume.

## TARGETED mode, defined

```text
QUICK      small diffs / PR reviews — plays/code-review.md
STANDARD   normal repository review — plays/code-review.md
DEEP       release/audit-grade review — plays/code-review.md
TARGETED   ordinary development-time changes, driven by
           skills/security-change-detection's classification — defined
           here
```

TARGETED reviews only the domains `skills/security-change-detection`
identified for the current change (its detection-signal categories —
e.g. "this diff matched the authorization and filesystem signal
groups"), using the *same* domain-to-play table QUICK/STANDARD/DEEP
already use (see above) — not a separate routing table, just a
narrower selection from the existing one, chosen by the classifier's
output instead of by review-mode convention. A MODERATE change whose
signals matched only "new dependency" loads `plays/dependency-security.md`
and nothing else; it does not load `plays/authentication.md` because
that wasn't part of what changed.

`plays/code-review.md`'s "Review modes" section and
`skills/security-review/SKILL.md` list QUICK/STANDARD/DEEP as of this
project's V1 baseline; TARGETED is defined here and is cross-referenced
from both of those entry points (see `plays/code-review.md`'s
"TARGETED" section and `skills/security-review/SKILL.md`'s step 1,
"Scope"), so it is visible from every entry point, not just this one.

## Scanner tool selection

```text
Change type                          Default scanner behavior
------------------------------------ ---------------------------------
Documentation / CSS / labels          None
Security-relevant code (any stack)    Semgrep, where the change is
                                       substantial enough that a
                                       pattern-based scan adds value
                                       over direct reading
Secret/configuration change           Gitleaks
Dependency manifest/lockfile          OSV-Scanner + ecosystem-native
                                       audit (dotnet list package /
                                       npm audit / pip-audit)
Container/IaC/configuration           Trivy, where applicable
STANDARD repository review            The relevant scanner set for the
                                       ecosystems actually present
DEEP/release review                   All applicable scanners
```

**Never run every scanner after every trivial edit.** A one-line
calculation fix (LOW sensitivity — see
`plays/security-change-detection.md`) does not warrant invoking
Semgrep, let alone the full `scripts/*/scan.*` sweep — that sweep
exists for STANDARD/DEEP review and explicit "scan this" requests, not
as a tax on every MODERATE change.

Scanner output remains **candidate evidence**, never confirmed
vulnerability evidence, regardless of which scanner or how it was
selected — see `plays/finding-validation.md`.

## Reusing evidence instead of re-scanning

If a scan already ran against the current repository state and covers
the domain in question, reuse that evidence rather than re-running the
same scanner. `output/scans/<timestamp>/normalized/summary.json`
records `gitCommit` and `dirty` (see `tools/README.md`) — treat a prior
scan as reusable when the repository is at the same commit with
`dirty: false`, or with `dirty: true` but no files relevant to the
domain in question touched since. Re-scan whenever `gitCommit` is
`null` (git unavailable, or no commits yet) or the match can't be
established with confidence.
