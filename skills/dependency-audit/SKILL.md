---
name: dependency-audit
description: Audit third-party dependencies for known vulnerabilities, deduplicate and prioritize by reachability. Use when reviewing dependency manifests/lockfiles, before a release, or when a new dependency is being added.
---

# Dependency Audit

Check third-party dependencies for known vulnerabilities and supply-chain
risk. Full procedure in `plays/dependency-security.md`.

## When to use

- Manifest/lockfile changed (`package.json`/lockfile, `requirements.txt`,
  `*.csproj`, `go.mod`, ...)
- Before a release or DEEP security review
- A new dependency is being proposed

## Tools

Prefer, in order of preference for a given ecosystem:

```text
OSV-Scanner       cross-ecosystem
Trivy             filesystem/dependency/container/secrets scanning
dotnet list package --vulnerable
npm audit
pip-audit
```

Neither OSV-Scanner nor Trivy requires Docker for a filesystem/dependency
scan — both ship as standalone binaries. Trivy only needs a container
runtime when scanning a built image.

Run via `scripts/*/scan.*`. If a tool is unavailable, report the coverage
gap explicitly (see `plays/finding-validation.md`'s failure-handling
guidance) rather than silently skipping it.

## Do not blindly combine results

Deduplicate by CVE across tools. Determine, for each vulnerable component,
whether it is:

```text
direct or transitive
runtime or development-only
actually reachable from application code
```

A HIGH-severity CVE in a transitive, dev-only, unreachable dependency is
not the same finding as a HIGH-severity CVE in a direct runtime
dependency whose vulnerable function is actually called.

## Output

Findings using `templates/finding.md`; supply-chain-specific fields
(direct/transitive, reachable) go in the Evidence/Impact sections.
