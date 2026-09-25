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

**V4** makes the review's own routing executable and adds three
capabilities, all layered on V1–V3 rather than replacing them (details
in "V4 components" below):

- a **Context Manifest**: the scope, sensitivity, security domains and
  review budget of a review, produced by a deterministic, standard-library
  Python package (`tools/context_manifest/`) and checked by a validator
  that rejects an invalid manifest as a whole;
- **optional** Jev (TypeSafe) assistance for that manifest, which is held
  to the same deterministic floor and falls back to the built-in producer
  on any problem;
- an **experimental** Evidence Reuse store (`.security/feedback.json`,
  `tools/feedback_store/`) that lets a still-eligible REJECTED conclusion be
  reused only after every eligibility and freshness check passes;
- **enterprise identity** review guidance (AD/LDAP, SSO/OIDC/JWT from Entra
  ID or ADFS, Windows Integrated Authentication) in
  `plays/enterprise-identity-security.md`.

## V4 components

**Built-in operation is the default and needs no credential.** Every
review runs fully on the built-in path; nothing below requires Jev, a
network connection, or a `TYPESAFE_API_KEY`.

- **Context Manifest (stable default).** `skills/security-review` step 1
  builds the manifest through `tools/context_manifest/orchestrator.py`
  (`produce_manifest()`), which runs the built-in producer and
  `validator.validate_manifest()`. A manifest that fails validation is
  discarded whole, never patched. The review budget has one entry point
  (`plays/review-budget.md`'s "The single entry point", executed by
  `budget.compute_review_budget()`).
- **Without Python.** When no working Python 3.7+ interpreter is
  available, the review still runs: the agent computes scope, sensitivity,
  domains and budget inline, as V3 did, and records that the manifest path
  was unavailable (`skills/security-review` step 1). Only the kit's own
  consistency check needs Python; it stops with `ERROR` (exit code 2)
  rather than skipping its `SCOPE_COVERAGE` category. Evidence Reuse is
  off without Python: no record is reused or written, so every candidate
  gets full validation.
- **Jev (optional, experimental).** With `TYPESAFE_API_KEY` set in the
  environment, the orchestrator makes one HTTPS request to the TypeSafe
  System One API, with no retry and a per-socket-operation timeout. Jev may add domains, raise
  sensitivity, order domains and choose the review budget within its legal
  range (below the caller's own Factors conclusion only when both its
  budget answer and its named Factor have confidence of at least 0.5); it
  never removes a floor domain, never lowers sensitivity, and never decides findings,
  exploitability, chains, remediation or the gate. Its candidate is
  validated against the same deterministic floor. A missing or rejected
  key, a timeout, a transport or HTTP error, malformed or incomplete
  output, or a candidate below the floor each falls back to the built-in
  manifest, and the outcome is recorded in `degradation.jevOutcome`. The
  outbound request carries a fixed field set and is refused if any field
  looks like a secret; keeping those fields to short, value-free
  descriptions is the reviewing agent's job (`skills/security-review`
  step 1 lists what may go in each).
- **Evidence Reuse (experimental).** A REJECTED conclusion recorded in the
  target repository's `.security/feedback.json` is reused only when the
  candidate has the same occurrence identity (sink, category and exact
  ordered call path) and every eligibility check passes: pattern and scope
  re-inspected in the current code, no invalidation condition true or
  unknown, no dependency changed, every intermediate control re-confirmed,
  and the record not stale. Anything ineligible, stale, malformed or
  ambiguous means full validation. A record never changes which scanners
  run or which candidates are generated. A missing or corrupted store
  degrades reuse for that run only and is never overwritten automatically.
  Procedure: `plays/finding-validation.md`'s "Feedback Learning" sections;
  format: `templates/feedback-store.md`.
- **Enterprise identity.** Loaded only when the play's "When this play
  applies" signals are present (for example `AddOpenIdConnect`,
  `LdapConnection`, `AddNegotiate`); it stays within the `authentication`
  domain. It has not been validated against a live AD, Entra ID, ADFS or
  Kerberos environment.

**What V4 does not claim.** V4 makes no token-saving, cost or speed claim,
and no claim that Jev or Evidence Reuse improves review quality or
efficiency; neither has a demonstrated benefit, which is why both are
labelled optional/experimental. The design documents in
`work/v4-planning/` describe hypotheses of that kind; they are design
records, not release claims.

## Validating this kit

```text
python -m unittest discover -s tools/context_manifest/tests -t .
python -m unittest discover -s tools/feedback_store/tests -t .
```

Run both from the repository root; `-t .` is required. The tests use an
injected fake Jev client and never contact the network or need a key.

```powershell
.\scripts\windows\consistency-check.ps1      # Windows PowerShell 5.1 or PowerShell 7
```

```bash
./scripts/macos/consistency-check.sh
```

The consistency check reports `PASS`, `REVIEW_REQUIRED` (candidate places
to look, see `plays/repository-consistency.md`) or `ERROR`. The review
behaviour itself is validated by running a review over the fixtures:
`tests/validation/README.md` (the V3 corpus, expected results in
`tests/validation/expected-results.md`) and
`tests/validation/v4-enterprise-identity-test-cases.md` (the enterprise
identity set, expected results in
`tests/validation/v4-enterprise-identity-expected-results.md`).

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
                 surface map, attack chain, feedback store)
tools/           notes for Semgrep, Gitleaks, OSV-Scanner, Trivy; the V4
                 Python packages context_manifest/ and feedback_store/
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
- Jev assistance and Evidence Reuse are experimental (see "V4
  components"). Known Evidence Reuse limitations: a `qualifiedSymbol` of
  the form `(*T).Method` (Go pointer receiver) or `(anonymous
  namespace)::f` (C++) is refused as unqualified, so such records cannot be
  created (reuse simply does not happen); a path containing a Unicode
  format character is refused; a writer holding the store's lock longer
  than 30 seconds can be treated as crashed.
- The enterprise identity guidance has not been exercised against a live
  directory or identity provider.
