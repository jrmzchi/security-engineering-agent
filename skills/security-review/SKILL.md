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
   level that workflow step already produced; for an explicitly
   requested QUICK/STANDARD/DEEP review (which never passes through
   that workflow step at all), invoke that play's "The single entry
   point" with the requested mode (no sensitivity input) — the same
   single computation the workflow step uses; this skill does not
   restate its tables or caps. Either way, the level controls how much
   material step 5 below actually loads within the domains this step
   selects, never which domains are selected (see that play's "Context
   budget" section for the depth rules this skill does not restate).

   **`[V4 Batch 0]`** Assemble this step's output into a Context
   Manifest and consume it at every step below, the same way "run
   applicable scanners per `scripts/*/scan.*`" (step 4) already means
   "the reviewing agent invokes that script" rather than something this
   kit triggers on its own — `tools/context_manifest/` is not a
   documented CLI for this purpose, it is a Python library the agent
   calls directly, but doing so is this step's normal way of working,
   not an optional enhancement. **Fallback**: `[CORRECTED, per a
   round-3 independent review Minor: an earlier revision's "or the call
   otherwise fails to run" clause was broader than intended, and
   conflicted with this same note's own "a validation failure is a bug,
   not a normal degraded case" statement below]` the ONLY fallback
   condition is no working Python 3 interpreter being available (see
   `scripts/*/doctor.*`'s `python-v4` check) — fall back to computing
   scope/sensitivity/domains/budget inline as V3 always did (budget: by
   hand from `plays/review-budget.md`'s "The single entry point" rule, not
   a separate computation), and record
   in the review's own notes that the manifest path was unavailable and
   why. Never silently skip this without a recorded reason; never let
   the MANIFEST's absence (Python unavailable) block completing the
   review (the no-Jev-token path's own "fully functional on its own"
   guarantee, one level further down: no-manifest must also degrade to
   something that still works, not stall). A manifest that IS built but
   then fails validation is a different situation (see below) — not
   this fallback path. Build one via `producer.build_manifest()` (see
   `work/v4-planning/context-manifest-schema.md` section 1 for the full
   shape), passing this step's own review mode/sensitivity/domains as
   the `classification` argument (or `baseline_facts` for DEEP, whose
   domain set `tools/context_manifest/domains.py`'s section 3a algorithm
   computes directly — the one genuinely new, code-implemented piece,
   see that module's own docstring; every other mode's
   classification/domain-implication reasoning is unchanged, still
   `skills/security-change-detection`'s own reasoning pass for
   TARGETED/QUICK, an architecture-discovery pass for STANDARD). **For
   DEEP specifically** `[FIXED, per a round-5 independent review
   Major]`: `context-manifest-schema.md` section 3a already required
   this and it was never actually wired — before building
   `baseline_facts`, build or refresh `.security/baseline.json` if it is
   missing or stale (`plays/project-security-baseline.md`'s "When to
   build one" guidance; a DEEP review is exactly the case that guidance
   already says justifies it), rather than deferring that to step 2's
   own "if it exists and is fresh" check below, which is written for
   the ordinary case where a manifest is consumed downstream of
   architecture discovery, not produced from it. `[CORRECTED, per
   round-6 and round-7 independent review: two successive revisions of
   this sentence each claimed a mechanical guarantee that turned out to
   be narrower than stated — round 6 found "regardless of what the
   calling step does" was false for the great majority of this
   algorithm's facts, and round 7 found the narrower "mechanically
   gates the [remaining] narrow case" claim was ALSO false, since
   `producer.build_manifest()` accepts already-built `Fact` objects,
   not raw baseline entries — nothing stops a caller from hand-building
   a Fact (silently dropping a `status` in the process) without ever
   calling the helper below. This revision stops drawing a
   code-enforced/prose-only line entirely, since no version of that
   line has survived a review round yet]` `domains.fact_from_baseline_entry()`
   is a safe conversion HELPER, not an enforcement mechanism: it
   downgrades a raw `.security/baseline.json` entry's `status: "STALE"`
   to `UNKNOWN_FACT` no matter what value it still carries, so USE it
   whenever a fact is grounded in a raw baseline record — but nothing
   in this batch's code verifies that it was actually called, that its
   output wasn't later reconstructed by hand, or that a fact derived
   through further reasoning (the great majority of what
   `compute_deep_domains` reads — `templates/project-security-baseline.md`
   is explicit there is no 1:1 field mapping between its own keys and
   this algorithm's fact vocabulary) correctly inherited the freshness
   of whatever baseline evidence it was reasoned from. Freshness
   discipline for every fact this algorithm reads — not just the ones
   with a directly-named baseline key — is fundamentally a requirement
   on the reviewing agent's own care, the same way item 0's sensitivity
   classification already is: if any baseline evidence a fact depends
   on is `STALE`, absent, or otherwise not confidently current, that
   fact must stay `UNKNOWN` (the `Fact()` default), never be asserted
   positive from it. A rushed or careless review can still get this
   wrong; the helper reduces one specific way of getting it wrong, it
   does not close the door on all of them. Then check it with
   `validator.validate_manifest()` before any later step consumes it. A manifest that fails is discarded WHOLE, never patched
   in place (see `tools/context_manifest/validator.py`'s own docstring
   for why) — for the built-in producer specifically this should never
   actually happen (its own output is the floor, by construction); a
   failure here means a bug in the producer or in how this step called
   it, not a normal degraded case to silently retry. **`[V4 Batch 2]`
   Build the manifest through `tools/context_manifest/orchestrator.py`'s
   `produce_manifest()` rather than calling `producer.build_manifest()`
   directly**: it runs the same built-in producer when no
   `TYPESAFE_API_KEY` is set (`degradation.jevOutcome: no_token`,
   `jevAttempted: false` — a fully supported, normal mode, not a
   degraded one), and otherwise makes one Jev call (a single attempt,
   no retry; its 10 s timeout applies to each socket operation, not to
   the call as a whole — see `jev_client.py`), validates
   Jev's candidate with the SAME `validator.validate_manifest()` against
   the SAME floor, and either accepts that manifest whole or discards it
   whole and runs the built-in producer, recording which of the six
   `jevOutcome` values applied and why in `degradation.fallbackReason`.
   Read `degradation` and surface any non-`success` outcome and its
   reason in the review's own notes. Two of those outcomes are easy to
   confuse: `incomplete_output` means Jev's OUTPUT could not be turned
   into a complete, well-formed candidate (unparseable, a missing
   answer, a wrong type, a Choice contradicting its own probabilities);
   `below_floor` means the candidate was complete but a sensitivity,
   domain, budget or activity result fell below the deterministic
   POLICY floor or the caller-adjusted budget. Jev is only ever asked about
   sensitivity (never below item 0's floor), additional domains (never
   fewer than the floor), review budget (within its legal range; it may
   raise the budget freely, but may lower it below the caller-adjusted
   budget — `compute_review_budget()` with this step's own
   `factor_adjustment` — only when both its budget answer and its named
   Factor have confidence ≥ 0.5; otherwise the whole candidate is
   discarded as `below_floor` — a complete answer below the effective
   floor, not an output defect — and the built-in manifest with the
   caller-adjusted budget is used), priority order, and which
   already-eligible Feedback records to consult — never about findings,
   exploitability, chains, remediation or the gate (see
   `work/v4-planning/v4-design.md` section 5); anything else in a Jev
   response is ignored and reported, never used. **What to put in the
   fields sent to Jev** — this is YOUR discipline, not something the code
   enforces (it only runs a secret-shape heuristic and refuses to send
   on a hit; there is no length or content limit):
   - `target_change_files`: repository-relative paths of the changed
     files, nothing else.
   - `diff_summary` / `change_summary`: one or two plain-language
     sentences on what the change does (e.g. "adds a report export
     endpoint"). Never diff hunks, source lines, string literals, config
     values, hostnames, or data samples.
   - `tech_stack`: language/framework names only.
   - `baseline_summary` / `attack_surface_summary`: short fact
     statements without values (e.g. "cookie session auth", "public
     POST /reports/export") — never config contents, connection
     strings, request bodies or user data.
   - `budget_factor_notes`: short Factor observations in words.
   - `reusable_records`: only records that already passed Batch 1's
     eligibility checks, and only their id, category and sink path.
   - `scanner_availability`: tool name → true/false.
   If a field would need more than that to be useful, leave it empty
   rather than paste raw material. The built-in path is
   still the product, not a fallback tier (section 4.1).
2. **Architecture discovery.** Identify languages/frameworks in play, entry
   points, trust boundaries, and which technology references apply
   (see "Progressive disclosure" below). If `.security/baseline.json`
   (`plays/project-security-baseline.md`) already exists for this
   repository and is fresh, consult it instead of rediscovering
   everything from scratch. **`[V4 Batch 0]`** When step 1 built a
   manifest, load domain(s) from its own `domains` field rather than
   recomputing them separately here. **`[V4 Batch 1]`** Also load
   `.security/feedback.json` here (`tools/feedback_store/store.py`),
   the same way as `.security/baseline.json`/`attack-surface.json` —
   apply Selective Invalidation (ordinary changed-files lookup, the
   central-component broader-invalidation extension, and non-file
   invalidation-condition resolution — see
   `plays/security-impact-analysis.md`'s own `[V4 Batch 1]` note) before
   step 7 ever tries to reuse anything from it. A missing or corrupted
   store degrades Evidence Reuse for this run only (every candidate
   just goes through full validation) — it never blocks or skips this
   step itself. **`[V4 release]`** The same applies when step 1's
   fallback applies (no working Python 3 interpreter): Evidence Reuse
   is then OFF for the whole run — do not read `.security/feedback.json`
   records and apply their checks by hand, do not reuse any record, do
   not write the store; every candidate goes through full validation
   in step 7, and the review's notes say why. Occurrence identity and
   path comparison are only defined by `tools/feedback_store/`'s code.
   Likewise, if a `tools/feedback_store/` call raises (for example a
   changed-files path it refuses), treat it as a degraded store: Evidence
   Reuse is off for the rest of the run. Never retry with the offending
   input filtered out or apply the checks by hand. **Reuse being off
   never excuses leaving a contradicted record reusable:** whenever full
   validation resolves a candidate CONFIRMED or NEEDS_VERIFICATION where
   a REJECTED record for the same occurrence exists
   (`plays/finding-validation.md` step 6), call
   `store.invalidate_contradicted()` — the one write allowed in a
   degraded or raising run. It marks the record STALE durably, or, if
   that cannot be guaranteed, quarantines the store (`load()` then
   reports it degraded and nothing is reused until
   `store.recover_quarantine()` has verified every listed record); if
   it raises, the store must be treated as unusable for reuse, and the
   review's notes say so. **`[ADDED, per a round-1 independent review Minor]`**
   When the store is reported degraded, do NOT write to
   `.security/feedback.json` this run (the sole exception is
   `store.invalidate_contradicted()` above, which never rewrites a store
   it cannot parse) — do not "auto-heal" by writing
   a fresh/empty store back over it, which would silently destroy
   every other rejection and human-confirmed miss record the degraded
   load couldn't parse alongside the one bad record. Surface the
   degradation and its reason in the review's own notes; fixing or
   intentionally rebuilding a corrupted store is a separate, explicit
   action, never an automatic side effect of this step.
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
   **`[V4 Batch 0]`** When step 1 built a manifest, its own
   `scannersSelected`/`scannersSkipped`/`coverageGaps` (already checked
   against `domains` by `tools/context_manifest/validator.py`'s
   scanner-domain consistency check) can be reused here instead of
   independently re-deriving the same selection.
5. **Manual semantic analysis.** Trace data flow for anything
   security-sensitive using the attack path model below. Open the
   relevant play(s) from the table, at the depth step 1's review budget
   level specifies — see `plays/review-budget.md`'s "Context budget"
   section for exactly what each level loads, not restated here. When a
   candidate's source and sink are in different files, use
   `plays/cross-file-data-flow.md`'s explicit multi-hop procedure rather
   than stopping at the file boundary. **`[V4 Batch 0]`** When step 1
   built a manifest, depth can be read directly from its own
   `reviewBudget` field (computed — or, for a Jev-produced manifest,
   bounded as step 1's Jev note states — by
   `tools/context_manifest/budget.py`'s `compute_review_budget()`, the
   executable form of `plays/review-budget.md`'s "The single entry
   point" — the one computation both step 1's explicit-mode path and
   `plays/secure-development-workflow.md`'s "Determine review budget"
   step use). When
   the manifest carries a `priorityOrder`, investigate in that order;
   `priorityOrder` is advisory only and its absence is not an error —
   fall back to the order `domains` itself lists. `priorityOrder` must
   never cause a domain listed in `domains` to be skipped entirely (see
   `work/v4-planning/context-manifest-schema.md` section 1's own note on
   this field) — this skill has no per-review time/token cap today, so
   this constraint is currently a no-op in practice, not yet an active
   truncation risk.
6. **Potential findings.** Draft findings using `templates/finding.md`.
7. **Validation.** Every HIGH/CRITICAL candidate MUST go through
   `skills/security-validate` before being reported as confirmed.
   **`[V4 Batch 1]`** Before invoking it for a given candidate, check
   Evidence Reuse eligibility against `.security/feedback.json` per
   `plays/finding-validation.md`'s own "Feedback Learning — reusing a
   REJECTED result" procedure — only when every one of that
   procedure's checks holds does this step skip re-invoking
   `skills/security-validate`; any check failing (or the candidate
   never matching an existing record's occurrence identity in the
   first place) means this step runs in full, exactly as if no
   Feedback record existed at all. A reused conclusion is never
   presented as freshly re-validated — the audit trail records which
   record ID was reused. Once
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
For a sink whose callers are outside the review scope, how the missing
link is resolved depends on the vulnerability class (injection vs.
authorization): see that play's "Rule — a sink whose callers are outside
the review scope".

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
| Enterprise identity integration (AD/SSO: OIDC/JWT from Entra ID or ADFS, direct LDAP/LDAPS, Windows Integrated Authentication) — still the `authentication` domain, loaded only when the play's "When this play applies" signals are present | `plays/enterprise-identity-security.md`, together with `plays/authentication.md` and `plays/authorization.md` | stack-specific reference; `references/iis-security.md` when hosted on IIS |
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
