# Security Review Quick Reference

Flat lookup: symptom / code pattern observed -> which play to open. This is
a fast triage aid, not a substitute for reading the play.

| If you see... | Open |
|---|---|
| String-concatenated SQL, `FromSqlRaw`/`ExecuteSqlRaw`, raw query building | `plays/code-review.md` (injection section), then stack reference |
| `subprocess`/`os.system`/`Process.Start`/`child_process` with dynamic input | `plays/code-review.md` (injection section), then stack reference |
| Template rendering with attacker-controlled template string | `plays/code-review.md` (injection section) |
| `innerHTML`/`outerHTML`/`document.write`/`insertAdjacentHTML`/React `dangerouslySetInnerHTML` | `plays/web-security.md` |
| CORS config, cookie flags, CSP headers | `plays/web-security.md` or `plays/configuration-security.md` |
| `postMessage` handlers or `postMessage(..., '*')` calls | `plays/web-security.md` |
| Any redirect built from user input | `plays/web-security.md` |
| Sensitive-action page missing `X-Frame-Options`/`frame-ancestors` | `plays/web-security.md` |
| XML parsing of attacker-supplied XML (external entities/DTD not disabled) | `plays/api-security.md` |
| HTTP client fetching a user-supplied URL (webhooks, image proxies, link previews) | `plays/api-security.md` (SSRF) |
| Deserialization of untrusted data (`pickle`, `yaml.load`, `BinaryFormatter`, Java `ObjectInputStream`) | `plays/api-security.md` |
| Request body bound directly onto a persistence model | `plays/api-security.md` (mass assignment) |
| `GET/DELETE /resource/{id}` style routes | `plays/authorization.md` (IDOR/BOLA) |
| Login, password reset, session/cookie/JWT handling | `plays/authentication.md` |
| `[Authorize]`/role/policy checks, or their absence | `plays/authorization.md` |
| Hardcoded keys, static IV/nonce, weak hash for passwords, `Random`/`Math.random()`/`random.random()` for security tokens | `plays/data-security.md` |
| File upload/download, ZIP/archive extraction, path building from user input | `plays/file-security.md` |
| `package.json`/`requirements.txt`/`*.csproj`/lockfiles changed | `plays/dependency-security.md` |
| API keys, tokens, connection strings, private keys in code or config | `plays/secrets-security.md` |
| `DEBUG=true`, verbose error pages, directory browsing, exposed backups | `plays/configuration-security.md` |
| A candidate is HIGH/CRITICAL and needs independent confirmation | `plays/finding-validation.md` |
