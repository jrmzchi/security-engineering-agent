# Security Engineering Agent

A portable, cross-platform security engineering kit for AI coding agents.
It supports security-by-design (before/during implementation) and
security review (after/during implementation), backed by deterministic
scanners (Semgrep, Gitleaks, OSV-Scanner, Trivy) and an independent
validation step that aggressively reduces false positives.

It is designed to be used the same way from OpenAI Codex or Claude Code,
on Windows or macOS, and does not depend on any Claude-specific feature
(subagents, skills, plugins, hooks) for its core security behavior — those
are optional accelerators layered on top.

## Release status and roadmap

- **V3 Final** is on `master` (`0ffd18e`). It is the complete V3 security
  capability baseline.
- **V3 Slim Golden Baseline** is on `v3-slim`, tagged
  `v3-slim-golden-baseline` (`f5502cd`). It preserves the validated V3
  behavior and includes workflow fixes and regression checks. It has **not**
  demonstrated an overall reduction in AI token use: the kit is 424 lines
  larger than V3 Final, and the one verified local reduction is a
  file-download review route that loads 509 rather than 519 lines.
- **V4 is planned, not implemented.** Its design is still under review;
  the features below are goals, not capabilities of the current release.

## Planned V4: Adaptive Security Intelligence & Orchestration

V4 aims to select the security work and context each task needs while
preserving V3's security findings, independent validation, and gate
behavior. It has two connected parts:

1. **Adaptive Security Orchestration.** A typed Context Manifest will
   describe the selected security domains, Skills, Plays, References,
   scanners, priorities, and review budget. When available, TypeSafe Jev
   may help make these routing decisions. Jev will not confirm a
   vulnerability, decide exploitability or remediation correctness, or
   issue a Security Gate result.
2. **Adaptive Project Security Intelligence.** Evidence-backed security
   facts and controls will record their scope, dependencies, confidence,
   freshness, and invalidation conditions. Reviews may reuse still-valid
   evidence and selectively revalidate what a change has affected.
   Feedback from rejected candidates and human-discovered misses will
   retain the supporting reasons and scope rather than become permanent
   ignore rules.

**A Jev token will be optional.** Without one, an included decision path
must produce the same Context Manifest format and run the same security
review, validation, and gate workflow. Missing or failed Jev calls must
fall back safely; essential security checks cannot depend on Jev.

A separate V4 capability is planned to review how an application uses
enterprise AD/SSO: trust and validation of login results, authorization
after login, safe directory connections and credentials, and failure
behavior. This is application integration review, not an audit of an
entire enterprise identity environment.

V4 will be assessed against the validated V3 baseline using security
regression cases and measured context, actual AI tokens, repeated
reasoning, unnecessary scans, latency, and cost. Jev routing and evidence
reuse will be measured separately. A later "V4 Slim" pass is only a
possibility if those measurements reveal specific remaining waste.
## What this project does

```text
Requirements -> Security Architecture -> Threat Modeling -> Implementation
   -> Security Review -> Automated Scanning -> Finding Validation
   -> Remediation -> Verification -> Security Report
```

It answers two different questions depending on when you use it:

- **Before/during implementation** — "What security requirements does this
  feature need?" (`skills/security-design`, `skills/threat-model`)
- **After/during implementation** — "What is actually wrong with this
  code, and can I prove it?" (`skills/security-review`,
  `skills/security-validate`, `skills/dependency-audit`, `skills/secrets-scan`)

Three layers, built up incrementally: **V1** is the review framework
above. **V2** makes security part of the normal development lifecycle
rather than something triggered only by an explicit review request —
`skills/security-change-detection` classifies how sensitive an ordinary
change is, `plays/secure-development-workflow.md` routes it
proportionally through design/review/gate/remediation, and
`skills/security-gate` makes the PASS/BLOCK decision deterministic.
**V3** adds project security intelligence on top: a persistent,
evidence-backed architecture baseline and attack-surface map for a
target repository (`skills/project-security-baseline`,
`skills/attack-surface-map`), reasoning that spans file and change
boundaries (`plays/cross-file-data-flow.md`,
`skills/security-impact-analysis`), proportional effort sizing
(`plays/review-budget.md`), multi-finding attack chains
(`skills/attack-chain-analysis`), and an active bypass-hunting pass for
the highest-risk findings and fixes (`skills/adversarial-validation`).
None of V3 is required for V1/V2 to keep working — see each skill's
own "When to use" section for when it actually applies.

## Architecture

```text
Agents        decide what work needs to be performed
  |
Skills        define a reusable security capability (entry point, concise)
  |
Plays         contain the detailed, authoritative step-by-step procedure
  |
References    contain technology/language-specific security knowledge
  |
Tools         perform deterministic scanning or analysis
```

Single source of truth: `plays/` is authoritative for procedures,
`references/` is authoritative for technology-specific guidance. `AGENTS.md`
and `CLAUDE.md` are thin entry points — they tell an agent where to look,
they do not duplicate the playbook.

## Repository layout

```text
skills/          SKILL.md entry points — V1/V2 (security-review,
                 security-design, threat-model, dependency-audit,
                 secrets-scan, security-validate,
                 security-change-detection, security-gate) and V3
                 (project-security-baseline, attack-surface-map,
                 security-impact-analysis, attack-chain-analysis,
                 adversarial-validation)
agents/          portable role definitions (team lead, architect, reviewer,
                 validator, dependency auditor, secrets reviewer)
plays/           authoritative step-by-step security procedures
references/      authoritative technology/platform security knowledge
templates/       output formats (finding, security report, threat model,
                 security design, project security baseline, attack
                 surface map, attack chain)
tools/           notes + wrappers for Semgrep, Gitleaks, OSV-Scanner, Trivy
scripts/         windows/ (.ps1) and macos/ (.sh) install / scan / doctor
integrations/    optional Codex- and Claude-specific accelerators
output/          scan results and generated reports (gitignored)
tests/           vulnerable/safe fixtures + validation checks
```

## Supported agents

- OpenAI Codex — reads `AGENTS.md`
- Claude Code — reads `CLAUDE.md`, may optionally use the Claude-native
  subagents under `integrations/claude/agents/`
- Any other agent capable of reading Markdown files and running local
  commands (the core procedures make no agent-specific assumptions)

## Supported operating systems

- Windows (`scripts/windows/*.ps1`)
- macOS (`scripts/macos/*.sh`)

## Supported languages / frameworks (strong support today)

```text
ASP.NET Core, C#, .NET, IIS
Python
JavaScript, TypeScript, Node.js
HTML, CSS, browser JavaScript
REST / JSON APIs
SQL databases
```

The architecture (skill -> play -> reference) allows adding Java, Go, PHP,
Rust, Docker, Kubernetes, AWS/Azure/GCP, mobile, AI/MCP-specific security
guidance later without restructuring the project — add a new
`references/<tech>-security.md` and wire it up from the relevant play.

## Installation

```powershell
# Windows — check what's installed without installing anything
.\scripts\windows\doctor.ps1

# Windows — install missing tools (uses winget, falls back to choco/scoop)
.\scripts\windows\install.ps1
```

```bash
# macOS — check what's installed without installing anything
./scripts/macos/doctor.sh

# macOS — install missing tools (uses brew)
./scripts/macos/install.sh
```

Both `install` scripts explain what they are about to do before
installing anything, and support a report-only mode that installs
nothing: `-CheckOnly` on Windows, `--check-only` on macOS (the flag
spelling follows each platform's own convention rather than being
identical across both).

## Codex setup

Codex reads `AGENTS.md` at the repository root. No further setup is
required — point Codex at this repository and it will discover the skills
and plays on its own.

## Claude Code setup

Claude Code reads `CLAUDE.md` at the repository root. Optional
Claude-native subagents are documented in `integrations/claude/README.md`
and can be installed as project subagents if you want parallel review.
Sequential execution (one agent, reading the plain skills/plays) always
works and does not require the subagents.

## Running a security review

Ask the agent, in your own words:

```text
Review this repository using STANDARD security review.
```

```text
Perform a DEEP security assessment and generate a security report.
```

```text
Review the current Git diff for security regressions.
```

```text
Threat-model the proposed file upload API before implementing it.
```

## Review modes

- **QUICK** — small diffs / PR reviews. Focus on changed attack surface only.
- **STANDARD** — normal repository review. Relevant scanners + semantic review.
- **DEEP** — release review, security audit, internet-facing or high-value
  systems. Architecture analysis, threat model, full scanners, manual
  semantic review, validation, configuration and dependency review, and a
  full security report.

See `plays/code-review.md` for the full mode definitions.

## Running scanners directly

```powershell
.\scripts\windows\scan.ps1
```

```bash
./scripts/macos/scan.sh
```

Both scripts detect the project's languages, run the applicable scanners
(Semgrep, Gitleaks, OSV-Scanner, Trivy, plus ecosystem-native tools such as
`dotnet list package --vulnerable`, `npm audit`, `pip-audit`), and write:

```text
output/scans/<timestamp>/raw/           raw tool output, one file per tool
output/scans/<timestamp>/normalized/    summary.json - per-tool finding
                                         counts, ecosystem detection, and
                                         coverage gaps (not yet
                                         deduplicated findings - that
                                         cross-tool analysis is
                                         skills/security-review's job,
                                         reading the raw output above)
output/reports/                         generated security reports
```

An unavailable scanner, or one that ran but produced no usable output
(for example because a CLI flag it expects has changed since this kit
was written), does not stop the review — it is reported as a coverage
gap in `summary.json` (see `plays/finding-validation.md`) so you know
what was and was not actually checked, rather than being treated as a
clean scan.

## Security model

- Scanner output and candidate findings from an initial reviewer pass are
  never treated as confirmed vulnerabilities.
- Every HIGH/CRITICAL candidate finding is independently re-examined by
  the validator role (`skills/security-validate`), which reconstructs the
  attack path, confirms attacker control and reachability, and checks for
  existing sanitization, validation, authorization, and framework
  protections before confirming.
- Findings without a demonstrable attack path are downgraded to LOW
  confidence or marked `NEEDS_VERIFICATION` rather than reported as
  confirmed.
- Rejected candidates are kept for audit transparency (see
  `plays/finding-validation.md`) rather than silently discarded.
- This project is for **defensive** application security. It does not
  perform destructive testing, does not brute-force real accounts, and
  does not exploit uncontrolled remote targets. Active testing against a
  live target requires explicit, in-scope authorization from the user.

## Limitations

- Detection quality depends on the external scanners being installed; run
  `doctor` to see what is actually available in your environment.
- Strong language/framework support is currently limited to the stack
  listed above — other stacks will get a best-effort semantic review but
  without a dedicated `references/` file some framework-specific nuance
  will be missing until one is added.
- This kit reviews source code and configuration it can read locally. It
  does not perform network penetration testing against remote targets.
- AI-driven semantic review can still miss vulnerabilities or produce
  findings that need human judgment — treat `NEEDS_VERIFICATION` and LOW
  confidence findings as leads, not conclusions.
