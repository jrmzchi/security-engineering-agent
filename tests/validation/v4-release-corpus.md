# V4 release validation corpus (`v4-release-corpus/3`)

The V4 release is validated against a versioned corpus with 39 rows, `RV-01` to `RV-39`.

- **Current version:** `v4-release-corpus/3`, `tests/validation/v4-release-corpus-v3-manifest.json`.
- **Earlier versions, kept as records:** `/1` (`v4-release-corpus-manifest.json`) and `/2`
  (`v4-release-corpus-v2-manifest.json`).

28 rows are the V3 corpus rows of `tests/validation/expected-results.md`, unchanged: same fixtures, members, forms
and expected results. **11 safe rows use V4-release fixtures**, listed below.

**This corpus is not a V3-versus-V4 comparison set.** Because 11 rows differ, a result on it cannot be compared
row-for-row with any historical V3 or Batch 5 figure. Nothing historical was changed:
- the V3 fixtures;
- `tests/validation/expected-results.md`;
- the historical results and all earlier validation stops.

The enterprise-identity set (`v4-enterprise-identity-expected-results.md`, 13 rows) is used unchanged.

## Why rows differ

A safe row ("no confirmed finding") must be a credible safe negative. Its security may not depend on middleware,
session configuration, a proxy or anything else the case does not contain. Two audits applied this; each case's
checklist is in `work/v4-release/safe-fixture-audit.md`.
- **First audit (revision 2).** Found real incidental weaknesses in 8 V3 safe fixtures.
- **Strict audit (revision 3).** Found 6 cases whose safety relied on something the case did not show. RV-15 is one
  of them: its missing session guard was confirmed by a review.

Suppressing a real weakness as out of scope, or editing a V3 fixture, was ruled out. Instead each affected row gets a
V4-release fixture that keeps the tested property and puts every control it relies on inside the case, or has a
genuinely public purpose with no sensitive data.

| Row | V3 fixture (unchanged) | Why the V3 fixture is not a safe negative | V4-release fixture (revision 3) | Tested property kept |
|---|---|---|---|---|
| RV-02 | `sql_injection_safe.py` | `/users` returns users' e-mail addresses to unauthenticated callers (CWE-306) | `tests/fixtures/v4_release/catalog_lookup_parameterized_safe.py` | a request value bound into a fixed parameterized query |
| RV-04 | `command_injection_safe.js` | the request value goes to ImageMagick `convert` unvalidated (CWE-88) | `tests/fixtures/v4_release/command_argument_array_bounded_safe.js` | argument array without a shell. Inputs come from a server-side fixed map and a range-checked integer (not an extension check; `execFile` is not relied on to stop option interpretation). **New in revision 3:** a concurrency bound on the unauthenticated work |
| RV-13 | `cookie_secure_safe.js` | `/login` issues a "logged in" session without checking any credential (CWE-287) | `tests/fixtures/v4_release/cookie_flags_anonymous_session_safe.js` | a random session cookie with HttpOnly, Secure, SameSite=Strict (anonymous cart; grants no identity) |
| RV-15 | `cors_restricted_safe.js` | `/api/account` reads `req.session.user` with no session middleware or guard in the case | `tests/fixtures/v4_release/cors_allowlist_session_guarded_safe.js` | credentialed CORS echoed only for an explicit allowlist (`Vary: Origin`). The session middleware (required secret, secure cookie) and a route guard (401 without a signed-in user) are in the case; the endpoint returns the caller's own display preferences |
| RV-20 | `redirect_local_safe.cs` | `Login` accepts credentials and, once its placeholder comment is stripped, verifies nothing | `tests/fixtures/v4_release/local_redirect_preferences_safe.cs` | `Url.IsLocalUrl` + `LocalRedirect` on a request-supplied return URL (language preference, allowlisted culture, antiforgery) |
| RV-22 | `ssrf_allowlist_safe.py` | the resolved IP is not pinned (DNS rebinding, admitted by the fixture); the response body is unbounded | `tests/fixtures/v4_release/ssrf_allowlist_pinned_safe.py` | scheme and host allowlist plus a public-address check, enforced on the pinned connection; no redirects; size cap |
| RV-24 | `path_traversal_safe.cs` | an "uploads" directory (user-supplied content) is served to unauthenticated callers (CWE-862) | `tests/fixtures/v4_release/public_document_download_nolinks_safe.cs` | `GetFullPath` containment with a trailing separator (published manuals). **New in revision 3:** no link or reparse point is followed on the file or on any directory below the base |
| RV-26 | `path_prefix_after_canonicalization_safe.cs` | links inside the base directory are left out of scope: an environment assumption the case does not show | `tests/fixtures/v4_release/path_prefix_canonicalized_nolinks_safe.cs` | the containment check on the canonicalized path with a trailing separator (the control-holds counterpart of the deceptive fixture), now with no link followed |
| RV-28 | `file_upload_safe.py` | anonymous uploads, with no access control or quota in the case | `tests/fixtures/v4_release/file_upload_authenticated_safe.py` | size cap, magic-byte type check, generated name, storage outside served paths. The signed-in guard, the session cookie (SameSite=Strict) and a per-user quota are in the case |
| RV-35 | `cross_file_sql_safe/` | an unauthenticated user search returns users' e-mail addresses (CWE-306/CWE-359) | `tests/fixtures/v4_release/cross_file_catalog_search_safe/` | a parameterized LIKE query reached across three files (public catalog fields, 50-row cap) |
| RV-37 | `cross_file_path_traversal_safe/` | a "reports" directory is served to unauthenticated callers; its sensitivity is not established by the code | `tests/fixtures/v4_release/cross_file_public_manual_download_nolinks_safe/` | canonicalized containment reached across three files (published manuals). **New in revision 3:** no link or reparse point is followed |

Every replacement row's expected result is **No confirmed finding**, with the same trap as its V3 row: a reviewer
flags the pattern the V3 row names without checking whether the control holds.

## Differences from revision 2

| Row | Revision 2 | Revision 3 | Why |
|---|---|---|---|
| RV-04 | `command_argument_array_allowlisted_safe.js` | `command_argument_array_bounded_safe.js` | the unauthenticated conversion work was unbounded |
| RV-15 | V3 `cors_restricted_safe.js` | `cors_allowlist_session_guarded_safe.js` | the session middleware and auth guard were not in the case |
| RV-24 | `public_document_download_safe.cs` | `public_document_download_nolinks_safe.cs` | links in directories below the base were assumed absent |
| RV-26 | V3 `path_prefix_after_canonicalization_safe.cs` | `path_prefix_canonicalized_nolinks_safe.cs` | the V3 fixture left links out of scope |
| RV-28 | V3 `file_upload_safe.py` | `file_upload_authenticated_safe.py` | anonymous uploads with no access control in the case |
| RV-37 | `cross_file_public_manual_download_safe/` | `cross_file_public_manual_download_nolinks_safe/` | as RV-24 |

The revision-2 files stay in the tree unchanged as the record of that corpus version.

`tools/context_manifest/tests/test_release_corpus.py` checks all three manifests deterministically:
- the mapping of every unchanged row against the V3 table;
- each current replacement fixture's tested property and visible controls;
- that no replacement fixture exposes user or account data it does not need.
