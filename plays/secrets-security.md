# Play: Secrets Security

Authoritative procedure for `skills/secrets-scan`.

## Tool

```text
Gitleaks
```

Runs against the working tree and, where configured, git history (a
secret removed from the current file but still present in an earlier
commit is still exposed to anyone with repo access).

## Manual fallback

If Gitleaks is unavailable, search for common credential shapes and
inspect likely locations manually:

```text
AKIA[0-9A-Z]{16}                 AWS access key ID
sk-[A-Za-z0-9]{20,}               common API-key prefix pattern (varies by vendor)
-----BEGIN [A-Z ]*PRIVATE KEY-----   PEM private key header
[A-Za-z0-9+/]{40,}={0,2}          long base64 blob near a "key"/"secret"/"token" identifier
```

Also inspect: `.env` files (existence and key **names** only — never
print values, see the secrets rule below), CI configuration, Docker
images/layers, and connection strings in application config
(`appsettings.json`, `application.properties`, etc.).

## Before reporting a hit, determine

```text
Is it a real secret, or an example/test/placeholder value?
    (e.g. "sk-test-...", "xxxxxxxx", values inside files clearly named
    for tests/fixtures should be checked against that context)
Is it active, if this can be checked SAFELY?
    (a safe check is e.g. a scoped, read-only, non-destructive API call
    explicitly authorized for this purpose — never guess at this without
    authorization; see the "Safe testing and validation boundaries"
    section in plays/finding-validation.md)
Is the file actually tracked by git (staged/local-only untracked files
    are lower urgency, but still a finding — they can be committed
    accidentally later)?
What is the exposure history — how long has it been committed, is the
    repository public or has it ever been public/forked?
```

## Never print full secrets

Every report, log, or artifact must redact the value:

```text
sk-proj-abc...xyz
```

Never write a live secret value into a finding, a commit message, an
artifact, or any output surface. This holds even when the secret is
being reported as the finding itself.

## Remediation is not just deletion

Removing a secret from the current file does not remove it from git
history. For a confirmed, real, active secret:

1. **Rotate the credential immediately** — treat it as compromised from
   the moment it was committed, regardless of whether misuse has been
   observed.
2. Remove it from the current file/config, replaced with a reference to
   a secret store or environment variable.
3. Only after rotation, consider whether history rewriting (e.g.
   `git filter-repo`) is warranted — this is a repository-wide,
   coordination-heavy operation and requires explicit authorization
   before performing it (see "Safe testing and validation boundaries" in
   `plays/finding-validation.md`; do not rewrite shared history
   unilaterally).

## Output

Use `templates/finding.md`, redacted per above. Note whether rotation has
been confirmed as part of remediation status.
