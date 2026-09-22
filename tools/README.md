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

## Adding a tool later

If a future addition (Java/Go/PHP/Rust/Docker/Kubernetes/cloud
scanners — see `README.md`'s roadmap) needs its own configuration file,
add a subdirectory here (`tools/<name>/`) rather than growing this
README indefinitely, and link to it from the relevant `plays/*.md`.
