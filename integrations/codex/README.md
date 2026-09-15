# Codex Integration

Codex needs no files beyond the repository root. It reads `AGENTS.md`
automatically, which points to `skills/`, `plays/`, and `references/` —
the same portable content every other agent uses. There is nothing
Codex-specific to install here; this file exists so the `integrations/`
directory documents both supported agents symmetrically (see
`integrations/claude/README.md` for the other one).

## Things worth knowing when running this kit under Codex

**Sandboxing and network access.** `scripts/*/scan.*` invoke `semgrep
scan --config auto`, which fetches a ruleset from the Semgrep Registry
over the network on first use (cached afterward for that environment).
If Codex is running in a sandbox with network access disabled, this
call will fail — the scan scripts treat that as a coverage gap (see
`plays/finding-validation.md`'s failure-handling guidance) rather than
crashing, so the rest of the review still completes; the coverage gap
in `output/scans/<timestamp>/normalized/summary.json` will say so.
`gitleaks`, `osv-scanner`, and `trivy` do not require network access
for the invocations this kit uses (OSV-Scanner does query the OSV API
by default for vulnerability data — if that is also blocked, expect a
coverage gap there too).

**Installing the scanners.** If Codex's environment can install
packages, `scripts/windows/install.ps1` / `scripts/macos/install.sh`
will do so with your confirmation — see `README.md`'s installation
section. If it cannot (a locked-down sandbox), run `doctor` to see
what's missing and either skip automated scanning for that session
(the AI-driven semantic review in `skills/security-review` still
works without any scanner installed — see that skill's non-negotiable
rules for how it handles scanner output either way) or ask the user to
provide raw scanner output some other way for you to analyze.

**A normal coding task, not just an explicit review request, may also
route through this kit.** `AGENTS.md`'s "Before implementing a
meaningful software change" section applies to Codex the same as any
other agent — classify via `skills/security-change-detection`, and for
anything beyond NONE/LOW sensitivity, follow
`plays/secure-development-workflow.md` proportionally rather than
treating security as something only triggered by an explicit "review
this" request.

**Everything else** — which skill to use when, the review workflow, the
confidence/severity models — is identical to any other agent using this
kit. See `AGENTS.md` at the repository root.
