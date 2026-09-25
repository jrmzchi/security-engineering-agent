# V4 release validation corpus (`v4-release-corpus/2`)

The V4 release is validated against a versioned corpus with 39 rows, `RV-01` to `RV-39`.

- **Current version:** `v4-release-corpus/2`, `tests/validation/v4-release-corpus-v2-manifest.json`.
- **Previous version, kept as a record:** `v4-release-corpus/1`, `tests/validation/v4-release-corpus-manifest.json`.

31 rows are the V3 corpus rows of `tests/validation/expected-results.md`, unchanged: same fixtures, members, forms
and expected results. **8 safe rows use V4-release replacement fixtures**, listed below.

**This corpus is not a V3-versus-V4 comparison set.** Because 8 rows differ, a result on it cannot be compared
row-for-row with any historical V3 or Batch 5 figure. Nothing historical was changed:
- the V3 fixtures;
- `tests/validation/expected-results.md`;
- the historical results.

The enterprise-identity set (`v4-enterprise-identity-expected-results.md`, 13 rows) is used unchanged.

## Why rows differ

Every row the corpus expects to be safe ("no confirmed finding") was audited on its actual code, not on its file
name, comments or label. That covers the 18 corpus rows and the 6 enterprise-identity rows.

The audit found that some V3 safe fixtures contain a real weakness outside the one property they were written to test.
A correct review reports such a weakness, so as a "no confirmed finding" fixture it punishes a correct answer. Two
things were ruled out:
- suppressing the weakness as out of scope, which would weaken the rule that a safe case has no CONFIRMED finding;
- editing the V3 fixture.

Instead, each affected row gets a V4-release fixture that keeps the tested property, drops the incidental weakness,
avoids personal or account data, and adds no pretend security layer. Where the problem was a "login" that verified
nothing, the replacement moves the tested property into a context that genuinely needs no login.

| Row | V3 fixture (unchanged) | Incidental weakness found | V4-release fixture | Tested property kept |
|---|---|---|---|---|
| RV-02 | `sql_injection_safe.py` | `/users` returns users' e-mail addresses to unauthenticated callers (CWE-306) | `tests/fixtures/v4_release/catalog_lookup_parameterized_safe.py` | a request value bound into a fixed parameterized query |
| RV-04 | `command_injection_safe.js` | the request value goes unvalidated to ImageMagick `convert`, so option and coder prefixes are interpreted (CWE-88; the fixture's own header admits it) | `tests/fixtures/v4_release/command_argument_array_allowlisted_safe.js` | argument array without a shell. ImageMagick's inputs come from a server-side fixed map and a range-checked integer, not from an extension check, and `execFile` is not relied on to stop option interpretation |
| RV-13 | `cookie_secure_safe.js` | `/login` answers "logged in" and issues a session without checking any credential (CWE-287) | `tests/fixtures/v4_release/cookie_flags_anonymous_session_safe.js` | a random session cookie with HttpOnly, Secure, SameSite=Strict (anonymous cart session; grants no identity) |
| RV-20 | `redirect_local_safe.cs` | `Login` accepts a username and password and, once its placeholder comment is stripped, verifies nothing | `tests/fixtures/v4_release/local_redirect_preferences_safe.cs` | `Url.IsLocalUrl` + `LocalRedirect` on a request-supplied return URL (language-preference action, allowlisted culture, antiforgery) |
| RV-22 | `ssrf_allowlist_safe.py` | the resolved IP is checked but not pinned (`requests.get` resolves again: a DNS-rebinding gap the fixture admits); the response body is unbounded | `tests/fixtures/v4_release/ssrf_allowlist_pinned_safe.py` | scheme and host allowlist plus a public-address check, now enforced on the connection itself (connect to the checked IP with TLS SNI/Host for the name), no redirects, size cap |
| RV-24 | `path_traversal_safe.cs` | an "uploads" directory (user-supplied content) is served to unauthenticated callers (CWE-862) | `tests/fixtures/v4_release/public_document_download_safe.cs` | `GetFullPath` containment with a trailing separator (published manuals; reparse points refused) |
| RV-35 | `cross_file_sql_safe/` | unauthenticated user search returns users' e-mail addresses (CWE-306/CWE-359) | `tests/fixtures/v4_release/cross_file_catalog_search_safe/` | a parameterized LIKE query reached across three files (public catalog fields, 50-row cap) |
| RV-37 | `cross_file_path_traversal_safe/` | a "reports" directory is served to unauthenticated callers; its sensitivity is not established by the code | `tests/fixtures/v4_release/cross_file_public_manual_download_safe/` | canonicalized containment reached across three files (published manuals; the download name comes from the resolved path) |

Every replacement row's expected result is **No confirmed finding**, with the same trap as its V3 row: a reviewer
flags the pattern the V3 row names without checking whether the control holds.

**Safe rows kept unchanged after the audit:** RV-06, RV-07, RV-11, RV-15, RV-17, RV-26, RV-28, RV-31, RV-33, RV-39,
and all 6 enterprise-identity safe rows. Three of them carry a residual note, not a confirmed weakness:
- RV-15 relies on session middleware the snippet does not show, and returns only the caller's own session data.
- RV-28 accepts anonymous uploads, size-capped and stored privately. Rate limiting is deployment policy.
- The enterprise-identity LDAP lookup returns colleagues' mail and phone to authenticated users, which is the intended
  function of a corporate directory.

`tools/context_manifest/tests/test_release_corpus.py` checks the manifests deterministically, including the mapping
of every unchanged row against the V3 table. It also checks each replacement fixture's tested property and that none
exposes user or account data.
