# Classification Test Cases

Validates `skills/security-change-detection` / `plays/security-change-detection.md`.
See `tests/validation/README.md` for how to run a validation pass — the
same "run it, compare to the expected column, don't just read the
answer off this table" principle applies here.

## Baseline cases (from plays/security-change-detection.md's own examples and categories)

| Change description | Expected sensitivity | Why |
|---|---|---|
| Fix a typo in README.md | NONE | Documentation |
| Change a CSS color value | NONE | Non-security visual change |
| Refactor an internal calculation function, no behavior change | LOW | Ordinary internal logic |
| Add a new database query for an existing, already-authorized report | MODERATE | Database-query change |
| Add a new dependency to package.json | MODERATE | New dependency |
| Add a new, non-privileged read-only API endpoint | MODERATE | New API endpoint without obviously privileged behavior |
| Add an authenticated endpoint that downloads a file by user-supplied filename | HIGH | File download + user-controlled filesystem path + authorization |
| Remove `[Authorize]` from a controller | HIGH | Authorization |
| Change a CORS policy | HIGH | CORS |
| Add a call to `Process.Start` with data influenced by user input | HIGH | Command/process execution |

## This batch's fixture pairs

Each pair's `*_unsafe.*` member represents what a diff introducing
that pattern would look like — the change itself, not just a static
property of the file, is what should classify HIGH:

| Fixture | Expected sensitivity | Matched signal(s) |
|---|---|---|
| `authorization_removed_unsafe.cs` | HIGH | authorization |
| `cors_wildcard_credentials_unsafe.js` | HIGH | CORS |
| `ssrf_user_url_unsafe.py` | HIGH | SSRF-sensitive network behavior |
| `redirect_unvalidated_unsafe.cs` | HIGH | user-controlled redirects (listed under MODERATE) *escalated* — see note below |
| `cookie_insecure_unsafe.js` | HIGH | cookies |

**Note on `redirect_unvalidated_unsafe.cs`:** `plays/security-change-detection.md`
lists "user-controlled redirects" under MODERATE, not HIGH. This
fixture is chained with a login flow, which is what elevates it — the
same redirect pattern in a low-value context (e.g. a "share this page"
link) would reasonably classify MODERATE. The HIGH classification here
does not need the redirect signal at all: this is a `[HttpPost("login")]`
endpoint, and `plays/security-change-detection.md`'s HIGH list
separately covers "authentication, session management" changes — a
login flow is HIGH on that basis alone, with the redirect pattern
riding along as an additional MODERATE-tier signal in the same diff.

## Domain selection cases

Beyond the sensitivity level, `plays/scanner-selection.md`'s TARGETED
mode should load only the matching domain(s) — verify these don't
over-load:

| Change | Domains that SHOULD load | Domains that should NOT load |
|---|---|---|
| `authorization_removed_unsafe.cs` | `plays/authorization.md` | `plays/data-security.md`, `plays/file-security.md` |
| `cors_wildcard_credentials_unsafe.js` | `plays/web-security.md`, `references/browser-security.md` | `plays/dependency-security.md` |
| `ssrf_user_url_unsafe.py` | `plays/api-security.md` | `plays/authentication.md` |
| `redirect_unvalidated_unsafe.cs` | `plays/web-security.md` | `plays/secrets-security.md` |
| `cookie_insecure_unsafe.js` | `plays/authentication.md` or `plays/configuration-security.md` | `plays/file-security.md` |
