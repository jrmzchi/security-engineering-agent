# Play: Authentication

Authoritative procedure for authentication-related findings.

## Scope

```text
Authentication bypass
Weak password handling
Credential exposure
Session fixation
Session hijacking
Insecure password reset
Missing MFA where required
Unsafe persistent login ("remember me")
```

## Authentication bypass

Look for logic that can skip the authentication check entirely:
conditional middleware ordering (auth middleware registered after the
route it should protect), a debug/test backdoor left enabled, a default
or hardcoded credential, an authentication check that only runs
client-side, or a fallback branch that treats "identity check failed to
run" as "identity check passed" (fail-open).

## Weak password handling (CWE-256 / CWE-916)

```text
Passwords stored in plaintext or with reversible encryption
    -> always a finding, regardless of how unlikely a breach seems
Passwords hashed with a fast general-purpose hash (MD5, SHA-1, SHA-256
    alone, no work factor)
    -> should be bcrypt, scrypt, Argon2, or PBKDF2 with adequate iterations
No minimum complexity/length requirement at all
    -> lower severity; note as hardening unless the asset is high-value
```

## Credential exposure

Credentials logged in plaintext (request bodies logged verbatim on a
login endpoint), sent in query strings (query strings end up in server
logs, browser history, proxy logs, `Referer` headers), or a password
field that get-request bound in a way that lands in access logs.

## Session fixation (CWE-384)

Check that the session identifier is regenerated on privilege change
(login, and any elevation such as switching to an admin context). If a
pre-login session ID remains valid and is reused post-login without
regeneration, an attacker who fixes a victim's session ID before login
can hijack the authenticated session.

## Session hijacking

```text
Session token transmitted without Secure/HttpOnly cookie flags
Session token accepted from a URL query parameter
No session expiry / no idle timeout
Session token predictable (sequential, low entropy, derived from
    guessable data like timestamp + user ID)
```

See also `plays/configuration-security.md`'s "Insecure cookies" section
for the same cookie-flag checks from the general hardening angle.

## Insecure password reset

```text
Reset token is predictable or short
Reset token does not expire or is not single-use
Reset endpoint allows account enumeration (different response for
    "email exists" vs "email does not exist") at a severity matching the
    actual risk to this application
Reset does not invalidate existing sessions
Reset flow can be completed without confirming the requester controls
    the account's email/phone (e.g. a "reset without token" code path)
```

## Missing MFA

Only a finding where the asset actually warrants it (admin accounts,
financial actions, access to sensitive PII at scale). Do not flag every
application for lacking MFA — assess against the design requirements in
`plays/security-design.md` for this specific system, or note as a
hardening recommendation rather than a vulnerability if no requirement
was established.

## Unsafe persistent login

A "remember me" token that is just a longer-lived copy of the session
token (rather than a separate, revocable, rotating token per RFC-informed
persistent-login patterns) means a single stolen token grants indefinite
access with no way to revoke it without invalidating all sessions.
