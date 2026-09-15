# AGENTS.md

This repository is a portable security engineering kit. It works with any
AI coding agent that can read Markdown and execute local commands — Codex
included.

## Where things live

```text
skills/       reusable security capabilities (what to do, when)
plays/        the detailed step-by-step procedures (authoritative)
references/   technology/security knowledge (authoritative)
agents/       portable role definitions (reviewer, validator, architect, ...)
templates/    finding / report / threat-model output formats
tools/        wrappers around external scanners (Semgrep, Gitleaks, OSV, Trivy)
scripts/      cross-platform install / scan / doctor entry points
```

Do not guess at security procedure details — they are not duplicated here.
Read the relevant skill, which points to the relevant play, which points to
the relevant reference.

## When to use which skill

```text
Designing a security-sensitive feature (auth, file upload, API, crypto,
system commands, ...) BEFORE or WHILE writing code
    -> skills/security-design/SKILL.md

Reviewing existing code, a diff, or a pull request
    -> skills/security-review/SKILL.md

A HIGH or CRITICAL candidate finding needs independent confirmation
    -> skills/security-validate/SKILL.md

Sizing up a new project or a significant new feature before deciding
what to build
    -> skills/threat-model/SKILL.md

Checking third-party dependencies for known vulnerabilities
    -> skills/dependency-audit/SKILL.md

Checking for exposed credentials, keys, or tokens
    -> skills/secrets-scan/SKILL.md
```

## Before implementing a meaningful software change

Not just when asked to "review" or "audit" — an ordinary "add an
endpoint" / "fix this bug" request goes through this too, proportional
to how security-sensitive it turns out to be:

```text
1. classify security sensitivity   -> skills/security-change-detection
2. security design if HIGH          -> skills/security-design
3. implement
4. inspect the actual diff (incl. untracked files)
5. re-classify against what was actually built
6. proportional targeted review     -> skills/security-review (TARGETED mode)
7. validate important candidates    -> skills/security-validate
8. apply the Security Gate           -> skills/security-gate
9. remediate and re-validate if needed -> plays/security-remediation.md
```

Full workflow, proportionality rules, and why NONE/LOW changes get none
of this: `plays/secure-development-workflow.md`. Keep this list as the
routing summary — do not copy the detailed rules from that play into
this file.

## Non-negotiable rules

```text
Scanner output (Semgrep, Gitleaks, OSV-Scanner, Trivy) is candidate
evidence, never a confirmed vulnerability on its own.

The presence of a dangerous function or API (eval, Process.Start,
innerHTML, raw SQL, ...) is not itself a vulnerability. Confirm that
attacker-controlled data reaches it in an exploitable way.

Every HIGH/CRITICAL finding must show a concrete attack path:
attacker -> entry point -> controlled data -> sink -> impact.
If that path cannot be shown, downgrade confidence or mark
NEEDS_VERIFICATION instead of reporting it as confirmed.

Prefer more reliable findings over more findings.
```

## Running scans

```bash
# macOS / Linux
./scripts/macos/doctor.sh
./scripts/macos/scan.sh
```

```powershell
# Windows
.\scripts\windows\doctor.ps1
.\scripts\windows\scan.ps1
```

`doctor` checks what security tooling is installed. `scan` runs the
applicable scanners for the detected project and writes results under
`output/scans/<timestamp>/`.

See `README.md` for full usage, review modes (QUICK/STANDARD/DEEP/TARGETED),
and installation instructions.
