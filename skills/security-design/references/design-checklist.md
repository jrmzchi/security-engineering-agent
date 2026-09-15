# Security Design Checklist (by feature type)

Condensed checklists for common feature types. Use `plays/security-design.md`
for the full reasoning process — this is a fast-lookup aid once you
already understand the pattern.

## Authentication

- [ ] Passwords hashed with a modern slow hash (bcrypt/scrypt/Argon2/PBKDF2 with adequate iterations — e.g. ASP.NET Core Identity's default), never reversible encryption
- [ ] Failed logins rate-limited / lockout does not enable account enumeration
- [ ] Session tokens generated with a CSPRNG, sufficient entropy
- [ ] Password reset tokens are single-use, time-limited, and invalidate prior sessions
- [ ] MFA available/required where the asset warrants it
- [ ] Logout invalidates the session server-side, not just client-side

## Authorization

- [ ] Every object-returning endpoint checks the caller owns/can access that object (not just that they are authenticated)
- [ ] Every privileged action checks role/permission server-side, not only hidden in the UI
- [ ] Every object-returning or object-acting endpoint has a server-side ownership/authorization check, regardless of whether the ID is sequential or a UUID — an unguessable ID is not a substitute for an authorization check

## APIs

- [ ] Authentication required by default; public endpoints are an explicit allowlist
- [ ] Object-level and function-level authorization both checked
- [ ] Rate limiting / resource consumption limits on expensive operations
- [ ] Response payloads exclude fields the caller should not see (no blanket entity serialization)
- [ ] Input bound to an explicit DTO, not the persistence model directly (mass assignment)

## File upload

- [ ] File type validated by content, not just extension or client-supplied MIME type
- [ ] Uploaded files stored outside the web root (or in a storage location/origin with no server-side script execution) so they cannot be directly requested and executed by the web server — a `Content-Disposition` header only affects browser-side rendering and does not stop server-side execution if the file is reachable under an executable path
- [ ] Filenames sanitized/regenerated; original name never used to build a filesystem path directly
- [ ] Size limits enforced

## File download / static serving

- [ ] Requested path is validated against a known base directory (no `..` traversal)
- [ ] Authorization checked per file, not assumed from the listing UI

## Database operations

- [ ] All queries parameterized or built through the ORM; no string-concatenated SQL
- [ ] Least-privilege DB credentials for the application's actual needs

## External HTTP requests / webhooks

- [ ] User-supplied URLs are not fetched directly (SSRF) — allowlist hosts/schemes, or resolve and check the target is not internal/link-local
- [ ] TLS certificate validation is not disabled

## Cryptography

- [ ] No hardcoded keys; keys come from a secret store or environment
- [ ] No static IV/nonce reuse
- [ ] CSPRNG (not `Random`/`Math.random()`/`random.random()`) for tokens, keys, IVs

## Session / cookies

- [ ] `HttpOnly`, `Secure`, and an explicit `SameSite` set appropriately
- [ ] Session identifier rotated on privilege change (login, elevation)

## CORS

- [ ] `Access-Control-Allow-Origin` is not `*` alongside credentialed requests
- [ ] Allowed origins are an explicit list, not reflected from the request

## Redirects

- [ ] User-controlled redirect targets validated against an allowlist or relative-path-only

## Background jobs / system commands

- [ ] No `shell=True` (or equivalent) with unsanitized input; arguments passed as an array, not a concatenated string
- [ ] Job inputs from untrusted sources treated with the same rigor as HTTP inputs

## Admin functionality

- [ ] Reachable only by an authenticated, authorized admin role
- [ ] Sensitive admin actions logged with actor identity
