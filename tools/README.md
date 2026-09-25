# Security Tools

This kit prefers mature, external, deterministic scanners over
recreating detection logic — see `plays/finding-validation.md` and the
project's overall philosophy of AI review + deterministic tooling
working together, neither replacing the other.

No dedicated per-tool configuration lives in this directory (no custom
Semgrep ruleset, Gitleaks allowlist, etc. as of this kit's initial
version) — `scripts/*/scan.*` invoke each tool with sensible defaults.
If a project later needs tool-specific configuration (a pinned Semgrep
ruleset, a Gitleaks baseline/allowlist), add it here and update the
relevant scan script to pass it in.

## Semgrep

Static analysis / pattern-based candidate detection across most of this
kit's supported languages.

- Install: `pip install semgrep` / `pipx install semgrep` / `brew install semgrep` (macOS) — no official winget package as of writing; see `scripts/windows/install.ps1`'s notes if using Windows
- Invoked by `scripts/*/scan.*` as: `semgrep scan --config auto --json`
- `--config auto` pulls a ruleset from the Semgrep Registry based on
  detected languages and requires network access on first run (cached
  afterward for the same environment)
- Output: candidate findings only — see `plays/code-review.md`

## Gitleaks

Secret detection in source and, optionally, git history.

- Install: `winget install Gitleaks.Gitleaks` / `brew install gitleaks`
- Invoked by `scripts/*/scan.*` as: `gitleaks detect --no-git --redact --source <repo> --report-format json --exit-code 0`
  (working-tree scan; git-history scanning is a heavier, separate pass —
  drop `--no-git` to include it)
- **`--redact` is gitleaks' own redaction, applied when the report is
  generated** — this is the primary control against a live secret ever
  reaching disk. Never invoke gitleaks for this kit without it.
- Output: candidate findings only — see `plays/secrets-security.md`

## OSV-Scanner

Cross-ecosystem dependency vulnerability scanning against the OSV
database. Prefer this as the default dependency scanner — no Docker
required.

- Install: `winget install Google.OSVScanner` / `brew install osv-scanner`
- Invoked by `scripts/*/scan.*` as: `osv-scanner --recursive --format json`
- Output: candidate findings only — see `plays/dependency-security.md`

## Trivy

Filesystem/dependency/config/secret/container scanning. Treated as an
optional enhancement in this kit (overlapping coverage with
OSV-Scanner/Gitleaks for dependencies/secrets) rather than a hard
requirement — see `scripts/*/doctor.*`'s classification.

- Install: `winget install AquaSecurity.Trivy` / `brew install trivy`
- Invoked by `scripts/*/scan.*` as: `trivy fs --scanners vuln,misconfig --format json`
  (`misconfig` is current Trivy's scanner name — older versions used
  `config`; if the installed version rejects `misconfig`, the scan
  scripts report this as a coverage gap rather than a silent zero)
  (no Docker required for this filesystem-scan mode — Docker/a
  container runtime is only needed if scanning a built container image,
  which this kit's scripts do not do by default)
- Output: candidate findings only — see `plays/dependency-security.md`
  and `plays/configuration-security.md`

## Ecosystem-native tools

Not third-party scanners, but part of the same "run the tool, treat
output as candidate evidence" pipeline:

```text
dotnet list package --vulnerable --include-transitive     (.NET)
npm audit --json                                            (Node)
pip-audit --format json [-r requirements.txt]                (Python)
```

`pip-audit` scans a `requirements.txt` at the repo root directly when
one exists; otherwise it audits the current Python environment, which
may not exactly reflect this repository's declared dependencies. It is
a separate `pip install pip-audit`, not bundled with `pip` itself —
`scripts/*/install.*` offer to install it when Python is detected.

See `plays/dependency-security.md` for how these are deduplicated
against OSV-Scanner/Trivy results by CVE/advisory ID rather than
double-counted.

## Scan metadata (summary.json)

`output/scans/<timestamp>/normalized/summary.json` records, alongside
findings counts and coverage gaps:

```json
{
  "timestamp": "2026-01-01T120000",
  "repoRoot": "/path/to/repo",
  "gitCommit": "a1b2c3d...",
  "dirty": false,
  "mode": "TARGETED",
  "diffOnly": true,
  "diffBase": "main",
  "ecosystems": { "dotnet": false, "node": true, "python": false },
  "toolVersions": {
    "semgrep": "1.x.x", "gitleaks": "8.x.x",
    "osv-scanner": "1.x.x", "trivy": "0.x.x"
  },
  "toolSelection": {
    "domains": ["authorization"],
    "selectedTools": ["semgrep"],
    "skippedTools": {
      "gitleaks": "not relevant to current change (domains: authorization)",
      "osv-scanner": "not relevant to current change (domains: authorization)",
      "trivy": "not relevant to current change (domains: authorization)"
    }
  }
}
```

`gitCommit` is `null` when git is unavailable or the repository has no
commits yet (an unborn `HEAD`). `dirty` reflects `git status --short`
at scan time. `mode` records which review mode (see
`plays/code-review.md`) the scan was run under — pass it explicitly
(`-Mode`/`--mode`) when known; it otherwise defaults to `TARGETED` for
a diff-scoped scan or `STANDARD` for a full-tree one. `toolVersions`
entries are `null` for any tool not installed. `toolSelection` reflects
`-Domains`/`--domains` (see `plays/scanner-selection.md`'s "TARGETED
domain-driven tool selection"): `domains`/`selectedTools` are `null`
when the flag was omitted (every applicable tool ran, same as before
this field existed), and `skippedTools` is empty in that case.
`selectedTools` uses the group name `ecosystem-native` (matching the
mapping table), but a *skipped* native tool is recorded individually as
`dotnet-list-package`/`npm-audit`/`pip-audit` — only for whichever
ecosystem is actually present, so `ecosystem-native` itself never
appears as a `skippedTools` key. See
`plays/scanner-selection.md`'s "Reusing evidence instead of
re-scanning" for how `gitCommit`/`dirty` are meant to be used to decide
whether a prior scan is still applicable.

## A note on CLI flags and versions

The flags documented above are current as of this kit's initial
version, but external tools change their CLI over time (a scanner name,
subcommand, or flag can be renamed or removed between major versions).
`scripts/*/scan.*` are written defensively for this: if a tool runs but
produces no parseable output, that is recorded as a coverage gap rather
than reported as "zero findings" — so a rejected flag surfaces as a gap
to investigate, not a false all-clear. If you see a gap referencing a
CLI mismatch, check the installed tool's `--help`/`--version` against
the invocation shown above.

## Repository consistency checker

Unlike everything else on this page, this is not a security scanner
and does not run against a target repository under review — it checks
this kit's own `plays/`/`skills/`/`templates/`/`tests/` for internal
consistency (a stale "not wired yet" claim, a status word used in a
context it doesn't belong in, a dangling file reference, a tracked
generated artifact). See `plays/repository-consistency.md` for the
full procedure.

- Invoked as: `scripts/windows/consistency-check.ps1` /
  `scripts/macos/consistency-check.sh`
- Pattern source: `tools/consistency-patterns.txt` — read by both
  scripts, not duplicated in either
- Output: mechanical recall only, `PASS`/`REVIEW_REQUIRED`/`ERROR` —
  see `plays/repository-consistency.md`'s "Interpreting output" for
  why a hit is a place to look, not a confirmed defect

## Context Manifest runtime (V4 Batch 0)

`tools/context_manifest/` is a standard-library-only Python 3 package
— the first place this kit's OWN operation (not a target repository
under review) depends on executable code beyond
`scripts/*/consistency-check.*`. It implements the deterministic logic
named in `work/v4-planning/context-manifest-schema.md` and
`work/v4-planning/v4-design.md`: the DEEP domain-applicability
algorithm (`domains.py`, section 3a), the Group 3 Scope coverage check
(`scope_coverage.py`, the Group 3 Scope coverage check),
the manifest schema/validator (`schema.py`/`validator.py`), the merged
`computeReviewBudget` entry point (`budget.py`), and the built-in
manifest producer (`producer.py`).

**Python 3 is a hard prerequisite for this package**, not an optional
enhancement the way Trivy or an ecosystem-native tool is (see
"Ecosystem-native tools" above) — `scripts/*/doctor.*` reports it as a
required V4 runtime tool distinct from the pre-existing, target-
ecosystem-driven `python`/`pip`/`pip-audit` checks, and
`scripts/*/consistency-check.*` fail closed (`ERROR`, exit code `2`)
rather than silently skipping the `SCOPE_COVERAGE` category when no
working interpreter is found on PATH.

Entry point (consistency-check only): `python -m
tools.context_manifest.cli <command>` — see `cli.py`'s own docstring
for the current command list and exit codes.
`scripts/windows/consistency-check.ps1` and
`scripts/macos/consistency-check.sh` are the only two callers of that
CLI; both invoke this exact entry point as a subprocess and relay its
output/exit code rather than reimplementing any of its logic — see
`scope_coverage.py`'s module docstring for why.

Modules (the reviewing agent imports and calls these directly, per
`skills/security-review`'s own `[V4 Batch 0]` notes -- like every other
step in that skill, this is a required step performed by the agent's
own code execution, not something a non-agent mechanism in this kit
triggers on its own, and not invoked via the CLI above; falls back to
V3's inline computation only when no working Python 3 interpreter is
available):

```text
domains.py     Group 1/2/3 DEEP domain-applicability algorithm
               (context-manifest-schema.md section 3a)
budget.py      the single computeReviewBudget entry point
               (v4-design.md section 7, Option B)
schema.py      manifest field contract -- required/optional fields,
               enums, degradation-record helpers
validator.py   the manifest validity checker (context-manifest-schema.md
               section 3) -- discards a failing manifest whole, never
               repairs one field in place
producer.py    the built-in (non-Jev) manifest producer
               (v4-design.md section 4.1) -- "the product, not a
               fallback tier"; runs for every non-success Jev outcome
orchestrator.py  [V4 Batch 2] the two-producer entry point
               (`produce_manifest()`): token check -> minimum-data
               request -> redaction gate -> ONE Jev call (single
               attempt, per-socket-operation timeout) ->
               strict parse -> the SAME validator -> accept the whole
               Jev manifest or discard it whole and run producer.py,
               recording one of the fixed six `degradation.jevOutcome`
               values; never mixes partial results, never fabricates
jev_client.py  [V4 Batch 2] transport only -- standard-library POST to
               https://api.typesafe.ai/v1/systemone with an explicit
               per-socket-operation timeout (NOT a wall-clock deadline;
               see its docstring), no automatic retry; typed results, never
               raises, never exposes the token
jev_adapter.py [V4 Batch 2] the typed Choice/Score/Noul questions Jev
               is asked (only the surface v4-design.md section 4.2 lets
               it influence) and the strict response -> candidate parse
redaction.py   [V4 Batch 2] outbound request gate (keys and values,
               all depths) using ../secret_heuristic.py -- a hit means
               the request is never sent
scope_coverage.py / cli.py   criterion 7's coverage check (see above)
```

**Jev is optional and experimental**: it has no demonstrated benefit, and
every review is complete without it.

**Jev / TypeSafe credential (V4 Batch 2)**: the orchestrator reads the
`TYPESAFE_API_KEY` environment variable and nothing else (no file, no
config, no prompt). **Absent or blank is a fully supported, normal
mode** — every review runs to completion on the built-in producer with
`degradation.jevOutcome: no_token` recorded honestly — not an
installation error. The value is never written to a manifest, log,
error message, report, test fixture or commit; tests use an injected
fake client and consume no token. With a token present the Jev path
adds ONE HTTPS request per review carrying the fields of
`jev_adapter.AllowedInput`. What this package itself enforces is
narrow: the request has a fixed field set (no field for file contents
or Feedback-record evidence text exists), and the redaction gate refuses
to send anything matching the shared secret-shape heuristic. It does
NOT limit the length or content of the free-text fields — keeping those
to minimum decision data (never raw diff hunks, source, config values
or secrets) is the caller's responsibility; the allowed content of each
field is defined in `skills/security-review/SKILL.md` step 1.
[CORRECTED, Batch 2 independent review #6: this paragraph used to read
as a program-enforced guarantee.]

Tests (run from the repository root): `python -m unittest discover -s
tools/context_manifest/tests -t .` — the `-t .` (top-level directory)
is required, not optional, so the test modules' relative imports
resolve; `python -m unittest tools.context_manifest.tests.test_domains`
also works directly.

## Feedback store runtime (V4 Batch 1)

**Evidence Reuse is experimental**: it has no demonstrated benefit, and a
review never depends on it (a missing, corrupted or ineligible store only
means full validation).

`tools/feedback_store/` is a second, standard-library-only Python 3
package, deliberately separate from `tools/context_manifest/` (it has
zero import dependency on it — see `tools/feedback_store/tests/test_negative_control.py`'s
import-graph check) implementing
`work/v4-planning/context-manifest-schema.md` sections 4/5/5.1/5.2 and
`work/v4-planning/v4-design.md` section 3's four named Adaptive
Project Security Intelligence mechanisms against a new,
separate-from-baseline/attack-surface `.security/feedback.json` store:

```text
paths.py        repository-relative path normalization/validation and
                the ordered {path, symbol} reachabilityPath comparison
schema.py       feedback_rejection / feedback_miss record shapes,
                build-time and load-time validation, the
                HIGH-confidence-trace-only creation gate, a disclosed
                heuristic secret-detection backstop
store.py        .security/feedback.json load/append/mark_stale/
                mark_revalidated/write -- corruption/unknown-schema-
                version handling (degrades the WHOLE store, never
                partially trusts a parseable fragment), an exclusive
                lockfile serializing concurrent writers around an
                atomic temp-file + os.replace write (an earlier
                lock-free, hash-check-only version was found, during
                independent review, to silently lose updates under
                genuinely simultaneous writers -- fixed by adding the
                lock rather than only improving the detection), a
                symlink/reparse-point escape guard
identity.py     occurrence identity PRECONDITION (schema section 5.1's
                (i)/(ii)/(iii): sink + category + exact ordered
                reachabilityPath) -- a candidate failing this is a
                DIFFERENT occurrence and is never compared against a
                record's eligibility at all
eligibility.py  reuse eligibility checks (a)-(d) -- (b)/(c) are
                mechanical (a caller-supplied condition-state map; a
                changed-files diff); (a)/(d) require re-inspecting
                actual code against a natural-language description,
                which this module cannot do itself -- they take an
                explicit caller verdict and fail closed on `None`
invalidation.py Selective Invalidation -- the ordinary freshnessOf-
                style direct lookup, PLUS a bounded central-component
                broader-invalidation extension (explicit,
                caller-supplied categories/path-prefixes only, never
                "the whole store"; see this module's own docstring for
                a disclosed correction to a schema-doc passage that
                conflated two different Play lists), PLUS non-file
                invalidation-condition resolution (UNKNOWN fails
                closed)
attribution.py  the four-layer (routing/attack_surface/cross_file_flow/
                reasoning) root-cause attribution for a human-
                discovered false negative -- walks the layers in
                dependency order but REFUSES (raises) rather than
                guesses when a gate has no evidence, so it cannot
                degenerate into defaulting to any one layer
```

No Jev runtime call exists anywhere in this package (matching
`tools/context_manifest/`'s own Batch 0 guarantee) --
`schema.VALIDATED_BY_VALUES` does not include "jev" as a legal
`lastValidation.validatedBy` value, enforcing
`work/v4-planning/v4-design.md` section 5's permission boundary at the
schema level, not just in prose.

Tests: `python -m unittest discover -s tools/feedback_store/tests -t .`
(same `-t .` requirement as `tools/context_manifest/tests`). Includes
the six discriminable acceptance cases against the actual, already-
existing `tests/fixtures/cross_file_object_authz_safe/` and
`cross_file_sql_safe/`/`cross_file_sql_unsafe/` fixtures (not new
ones), a negative control proving a Feedback record cannot suppress
scanner execution or candidate generation by construction, four
root-cause-layer fixtures, and an explicit mutation suite.

## Planning references in comments

Docstrings and comments in `tools/context_manifest/` and
`tools/feedback_store/` (and their tests) sometimes cite V4 planning
records by name -- `implementation-batches.md`, `measurement-plan.md`,
the batch verification logs, and review-round labels. Those records
are not part of this release; they explain where a rule came from and
never define current behaviour. The two design specifications the code
is built from, `work/v4-planning/context-manifest-schema.md` and
`work/v4-planning/v4-design.md`, are included.

## Adding a tool later

If a future addition (Java/Go/PHP/Rust/Docker/Kubernetes/cloud
scanners — see `README.md`'s roadmap) needs its own configuration file,
add a subdirectory here (`tools/<name>/`) rather than growing this
README indefinitely, and link to it from the relevant `plays/*.md`.
