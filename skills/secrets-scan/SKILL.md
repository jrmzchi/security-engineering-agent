---
name: secrets-scan
description: Scan for exposed secrets — API keys, passwords, tokens, private keys, connection strings, cloud/database credentials — in source, config, and git history. Use when reviewing code, before a commit/PR, or when a leak is suspected.
---

# Secrets Scan

Detect exposed credentials. Full procedure in `plays/secrets-security.md`.

## When to use

- Any security review (it is part of `security-review`'s standard scope)
- Before committing/pushing, when a leak is suspected
- Reviewing configuration files, `.env` files (existence/keys only, never
  values — see the secrets rule below), CI config, container images

## Tool

```text
Gitleaks
```

If unavailable, fall back to manual review: grep for common credential
shapes (`AKIA[0-9A-Z]{16}`, `sk-[A-Za-z0-9]{20,}`, PEM private key
headers, JDBC/ADO connection strings with embedded passwords) and inspect
config files and git history for anything that looks like a live secret.

## Before reporting a hit

Scanner output is candidate evidence. Determine:

```text
Is it a real secret, or an example/test placeholder?
Is it active, if this can be checked safely?
Is the file actually tracked by git (or only staged/local)?
What is the exposure history (how long has it been committed, is it public)?
```

## Never print full secrets

Redact in every report:

```text
sk-proj-abc...xyz
```

Never write live secret values into a report, a commit, or an artifact.

## Output

Findings using `templates/finding.md`, redacted. If a real, active secret
is confirmed, remediation must include rotation, not just removal from
the current file (git history retains it until purged).
