# Play: Dependency Security

Authoritative procedure for `skills/dependency-audit`.

## Tools

```text
OSV-Scanner    cross-ecosystem — prefer as the default
Trivy          dependency/container/filesystem/config/secrets scanning
```

Neither requires Docker for a filesystem/dependency scan — both ship as a
standalone binary. Trivy only needs a container runtime when scanning a
built container image, not for scanning source/dependencies directly.

Plus ecosystem-native tooling when useful:

```text
dotnet list package --vulnerable
npm audit
pip-audit
```

Run via `scripts/*/scan.*`, which detects the project's ecosystems and
invokes the applicable tools. See `plays/finding-validation.md`'s
failure-handling guidance for what to do when a tool is unavailable.

## Procedure

1. Run all applicable tools for the detected ecosystems.
2. **Deduplicate by CVE/advisory ID** across tools — the same
   vulnerability reported by both OSV-Scanner and a native tool is one
   finding, not two.
3. For each unique vulnerable component, determine:

   ```text
   Direct or transitive?
       direct    -> your manifest lists it explicitly
       transitive -> pulled in by another dependency

   Runtime or development-only?
       a vulnerable dev/test/build-only dependency that never ships or
       executes in production has materially lower real-world risk

   Reachable?
       is the vulnerable function/code path actually called by this
       application, or is only an unrelated part of the package used?
   ```

4. Prioritize: direct + runtime + reachable + high CVSS is the fix-first
   tier. Transitive + dev-only + unreachable + low CVSS can be tracked as
   informational rather than blocking.

## Reachability is a judgment call, not a guess

Where the tooling doesn't determine reachability automatically, check
whether the vulnerable function/class is actually imported and invoked
anywhere in the dependency chain your application exercises. If this
cannot be determined with reasonable confidence, mark the finding's
confidence as MEDIUM rather than asserting reachability either way.

## Supply chain beyond known-CVE scanning

```text
Abandoned dependencies    no maintenance activity, no response to
                          disclosed vulnerabilities — a growing-risk
                          finding even with zero current CVEs
Untrusted package sources  a dependency installed from a source other
                          than the ecosystem's standard registry
Dependency confusion       an internal/private package name that could
                          be shadowed by a public package of the same
                          name on the public registry
Unsafe install scripts     a package with an install/postinstall script
                          that runs arbitrary code at install time —
                          worth flagging for new/unfamiliar dependencies
                          especially
```

## Output

Use `templates/finding.md`. Include: package name, version, CVE/advisory
ID(s) (deduplicated), direct/transitive, runtime/dev, reachability
assessment, and the available fixed version.
