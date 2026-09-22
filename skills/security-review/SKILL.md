---
name: security-review
description: Perform evidence-based defensive security review of application source code, APIs, authentication, authorization, filesystem operations, dependencies, secrets and deployment configuration. Use when reviewing code, pull requests, repositories or security-sensitive changes.
---

# Security Review

Perform a comprehensive, evidence-based security review of application code.

## When to use

Reviewing code, pull requests, repositories, or security-sensitive
changes — explicitly requested (QUICK/STANDARD/DEEP, see
`plays/code-review.md`) or as the TARGETED step of
`plays/secure-development-workflow.md`.

## Workflow

```text
Scope
  |
Architecture discovery
  |
Attack surface identification
  |
Automated scanners
  |
Manual semantic analysis
  |
Potential findings
  |
Validation
  |
Final findings
```

1. **Scope.** Determine review mode (QUICK / STANDARD / DEEP / TARGETED
   — see `plays/code-review.md`; TARGETED is driven by
   `skills/security-change-detection`'s classification rather than
   picked directly, see `plays/secure-development-workflow.md`), and
   whether this is a diff-aware review (`git diff`) or a
   full-repository review. Also determine the review budget level
   (`plays/review-budget.md`) here — for a TARGETED review, record the
   level that workflow step already computed; for an explicitly
   requested QUICK/STANDARD/DEEP review (which never passes through
   that workflow step at all), compute it directly per that play's
   "Explicit mode" section. Either way, the level controls how much
   material step 5 below actually loads within the domains this step
   selects, never which domains are selected (see that play's "Context
   budget" section for the depth rules this skill does not restate).
2. **Architecture discovery.** Identify languages/frameworks in play, entry
   points, trust boundaries, and which technology references apply
   (see "Progressive disclosure" below). If `.security/baseline.json`
   (`plays/project-security-baseline.md`) already exists for this
   repository and is fresh, consult it instead of rediscovering
   everything from scratch.
3. **Attack surface identification.** Enumerate inputs an attacker
   controls: HTTP requests, query params, file uploads, headers, cookies,
   deserialized payloads, environment/config, third-party webhooks. If
   `.security/attack-surface.json` (`plays/attack-surface-mapping.md`)
   already exists and is fresh, consult it for known entry
   points/controls/sinks — same freshness caveat as step 2's baseline.
   At an `ELEVATED` review budget (step 1), also pull in
   directly-connected map neighbors of the changed node(s) here — this
   is the step that actually reads map data, see
   `plays/review-budget.md`'s "Context budget" for the ELEVATED
   definition and how to handle a neighbor that falls outside the
   domain(s) step 1 already selected.
4. **Automated scanners.** Run applicable scanners (Semgrep, Gitleaks,
   OSV-Scanner, Trivy, ecosystem-native tools) per `scripts/*/scan.*`.
   Treat every scanner hit as a **candidate**, never a confirmed finding.
5. **Manual semantic analysis.** Trace data flow for anything
   security-sensitive using the attack path model below. Open the
   relevant play(s) from the table, at the depth step 1's review budget
   level specifies — see `plays/review-budget.md`'s "Context budget"
   section for exactly what each level loads, not restated here. When a
   candidate's source and sink are in different files, use
   `plays/cross-file-data-flow.md`'s explicit multi-hop procedure rather
   than stopping at the file boundary.
6. **Potential findings.** Draft findings using `templates/finding.md`.
7. **Validation.** Every HIGH/CRITICAL candidate MUST go through
   `skills/security-validate` before being reported as confirmed. Once
   multiple findings are CONFIRMED, check
   `plays/attack-chain-analysis.md`'s concrete test for whether any of
   them combine into a more serious chain — do this before the next
   sentence, since a discovered chain is itself one of
   `plays/adversarial-validation.md`'s triggers. A confirmed CRITICAL
   finding, a confirmed HIGH finding with more than one control in its
   path, a chain's own inter-step controls, or any of the other cases
   that play's trigger list names additionally needs its bypass
   checklist, not just ordinary validation.
8. **Final findings.** Assemble the report per
   `templates/security-report.md`.

## Non-negotiable rules

- **Never treat scanner output as a confirmed vulnerability.** Semgrep,
  Gitleaks, OSV-Scanner and Trivy findings are leads to investigate, not
  conclusions.
- **Never report a vulnerability solely because a dangerous function or
  API exists.** `eval`, `Process.Start`, `innerHTML`, raw SQL, and file
  upload handlers are not vulnerabilities by themselves — see
  "Dangerous pattern ≠ vulnerability" in `plays/code-review.md`.
- **Every important (HIGH/CRITICAL) finding must include an attack path.**
  If you cannot trace one, downgrade confidence or mark
  `NEEDS_VERIFICATION` (see `plays/finding-validation.md`).

## Attack path model

Trace every candidate finding through this chain before treating it as
real:

```text
Attacker
  |
Input source          (where does attacker-controlled data enter?)
  |
Data transformation    (what happens to it before it is used?)
  |
Validation             (is it checked, encoded, escaped, parameterized?)
  |
Security controls      (authn/authz/framework protections in the way?)
  |
Sensitive sink          (SQL, filesystem, shell, DOM, deserializer, ...)
  |
Security impact
```

If any link in this chain cannot be demonstrated with evidence
(file/line, or a concrete traced value), the finding is not HIGH/CRITICAL
confidence — see the confidence model in `plays/finding-validation.md`.

## Where to look next (progressive disclosure)

Do not load every reference for every review. Pick the play(s) that match
what actually exists in the codebase, then the reference(s) that match the
stack:

| Concern | Play | Then reference (as applicable to the stack in use) |
|---|---|---|
| General review flow, modes, injection, diffs | `plays/code-review.md` | stack-specific reference (`dotnet`/`aspnet`/`python`/`javascript`/`node`) |
| Browser-side (XSS, CSRF, CORS, CSP, postMessage) | `plays/web-security.md` | `references/browser-security.md` |
| APIs, SSRF, deserialization, XXE, mass assignment | `plays/api-security.md` | stack-specific reference (`aspnet`/`python`/`node`), whichever serves the API |
| Authentication | `plays/authentication.md` | stack-specific reference |
| Authorization / IDOR / BOLA | `plays/authorization.md` | stack-specific reference |
| Cryptography, sensitive data | `plays/data-security.md` | stack-specific reference |
| File upload/download/paths | `plays/file-security.md` | stack-specific reference (e.g. `aspnet-security.md` for `IFormFile`/`StaticFiles`), plus `references/windows-security.md` or `references/macos-security.md` for the deployment OS |
| Dependencies / supply chain | `plays/dependency-security.md` | — |
| Secrets | `plays/secrets-security.md` | — |
| Deployment / configuration / IIS | `plays/configuration-security.md` | `references/iis-security.md` when deployed to IIS |

See `skills/security-review/references/quick-reference.md` for a flat
lookup table from symptom to play.

A .NET project should not pull in IIS or Windows-specific guidance unless
it is actually deployed there. A pure Python CLI should not load ASP.NET
or browser guidance at all.

## Confidence and severity

Use the confidence model (HIGH / MEDIUM / LOW) and severity model
(CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL) defined in
`plays/finding-validation.md`. Do not assign CRITICAL merely because a
CWE is traditionally dangerous — assess exploitability, privileges
required, user interaction, data sensitivity, blast radius, and exposure.

## Output

Use `templates/finding.md` per finding and `templates/security-report.md`
for the assembled report. Keep evidence minimal — file path, line number,
the relevant snippet, and the traced data flow. Do not dump large code
sections.
