# V4 release — safe-fixture audit, strict standard (2026-09-25)

Every expected-safe case of the V4 release corpus and of the enterprise-identity corpus was re-audited on its actual
code. That is 24 cases: 18 corpus rows, replaced and kept alike, plus 6 enterprise-identity rows.

**The standard.** File names, comments and expected labels were ignored. The review covered every entry point, data
source and output, sensitive data, and access control. A case is a safe negative only if:
- the controls it relies on are in the case itself; or
- the case fails closed when they are absent; or
- it has a genuinely public purpose with no sensitive data.

Middleware, session configuration, a proxy, or anything else the fixture does not contain was **not** assumed to
exist.

**Why this audit exists.** The previous audit kept RV-15 (`cors_restricted_safe.js`) on the grounds that it
"relies on session middleware not shown". The review then confirmed the missing guard. That judgment is corrected
here: RV-15 now gets a fixture whose middleware and guard are part of the case.

**Verdicts:**
- **SAFE:** a safe negative as it is.
- **CONTEXT:** needed context or an environment assumption made verifiable → a V4 fixture.
- **VULN:** a real vulnerability → a V4 fixture. Found in the previous audit; none new here.

Jev was not called in this phase.

| Row | Fixture used now (under `tests/fixtures/`) | Entry points | Input → sensitive operation | Data returned / changed | Controls in the case | Unprovided dependency / assumption | Verdict |
|---|---|---|---|---|---|---|---|
| RV-02 | `v4_release/catalog_lookup_parameterized_safe.py` | `GET /catalog/products` | `category` → bound SQL parameter | published catalog fields | parameterized query; public purpose | none | SAFE |
| RV-04 | `command_injection_safe.js` → **`v4_release/command_argument_array_bounded_safe.js`** | `POST /thumbnails` | asset key → fixed server map; size → range-checked int → `execFile` args | PNG of a public asset | no shell, no client value used as an argument, timeout, output cap, **concurrency cap (new)** | revision 2 had no bound on the unauthenticated conversion work | CONTEXT (rev 2: VULN CWE-88) |
| RV-06 | `ef_fromsqlraw_vs_interpolated.cs` (`FindByNameSafe`) | public data-access method, no endpoint | `name` → EF parameter | `User` rows | parameterization | callers (and their access control) are outside the unit; per the play that is NEEDS_VERIFICATION at most, never CONFIRMED | SAFE |
| RV-07 | `ef_fromsqlraw_vs_interpolated.cs` (`FindByNameSafeRawWithParams`) | as RV-06 | `name` → positional parameter | `User` rows | parameterization | as RV-06 | SAFE |
| RV-11 | `hardcoded_secret_example_value.py` | none (a documentation string) | none | none | documented placeholder values | none | SAFE |
| RV-13 | `v4_release/cookie_flags_anonymous_session_safe.js` | `POST /cart/session` | none (server-generated id) | sets an anonymous cart cookie | random 256-bit id; HttpOnly, Secure, SameSite=Strict; path and lifetime | none; the cookie grants no identity | SAFE |
| RV-15 | `cors_restricted_safe.js` → **`v4_release/cors_allowlist_session_guarded_safe.js`** | CORS middleware; `GET /api/preferences` | `Origin` → allowlist; session → guard | the caller's own display preferences | origin allowlist, `Vary: Origin`, session middleware (required secret, HttpOnly/Secure/SameSite=Lax, no uninitialized sessions), route guard (401 without a signed-in user id) | V3: `req.session.user` read with no middleware or guard in the case (confirmed in the last run) | CONTEXT (V3: confirmed missing guard) |
| RV-17 | `xss_safe.js` | page load (browser) | `?name` → `textContent` | text only | text sink | none | SAFE |
| RV-20 | `v4_release/local_redirect_preferences_safe.cs` | `POST /preferences/language` | `culture` → allowlist; `returnUrl` → `IsLocalUrl` → `LocalRedirect` | sets a culture cookie; redirects locally | allowlist, local-redirect check plus `LocalRedirect`, antiforgery attribute (fails closed if its services are missing) | none | SAFE |
| RV-22 | `v4_release/ssrf_allowlist_pinned_safe.py` | `POST /partner-images/preview` | URL → scheme/host allowlist → public-address check → pinned connection | size of a partner image | allowlist, `is_global` on every resolved address, pinned IP with TLS name check, no redirects, size cap, timeout | none; public preview of partner images | SAFE |
| RV-24 | `path_traversal_safe.cs` → **`v4_release/public_document_download_nolinks_safe.cs`** | `GET /manuals` | `fileName` → `GetFullPath` → containment → open | a published manual | canonical containment with separator, reparse points refused on the file **and every directory down from the base (new)** | revision 2 assumed no links inside the base directory | CONTEXT (rev 2 from V3: VULN, uploads served unauthenticated) |
| RV-26 | `path_prefix_after_canonicalization_safe.cs` → **`v4_release/path_prefix_canonicalized_nolinks_safe.cs`** | public helper method, no endpoint | `reportName` → `GetFullPath` → containment | a path or null | canonical containment with separator, **reparse points refused (new)** | V3 left links inside the base directory out of scope (an environment assumption) | CONTEXT |
| RV-28 | `file_upload_safe.py` → **`v4_release/file_upload_authenticated_safe.py`** | `POST /upload` | file → size cap → magic-byte check → generated name → per-user private directory | stores a file; returns its generated id | signed-in guard, required secret, HttpOnly/Secure/SameSite=Strict session cookie, size cap, content check, generated name, never served, per-user quota | V3: anonymous uploads with no access control or quota in the case | CONTEXT |
| RV-31 | `idor_safe.cs` | `GET /api/orders/{id}` | `orderId` → repository → ownership check | the caller's own order | `[Authorize]` (fails closed without an authentication scheme), ownership check | repository implementation (not security-relevant: the check is after the lookup) | SAFE |
| RV-33 | `authorization_preserved_safe.cs` (pair before-side) | `DELETE /admin/users/{id}` | `userId` → service | deletes a user (admin only) | `[Authorize(Roles = "Admin")]` (fails closed); a cross-site DELETE needs a CORS preflight | none | SAFE |
| RV-35 | `v4_release/cross_file_catalog_search_safe/` | `GET /api/catalog/search` | `q` (length-checked) → bound LIKE parameter (three files) | ≤ 50 published product rows | parameterized query, public purpose, row cap | none | SAFE |
| RV-37 | `cross_file_path_traversal_safe/` → **`v4_release/cross_file_public_manual_download_nolinks_safe/`** | `GET /manuals/download` | `manualName` → canonical containment (three files) | a published manual | canonical containment with separator, **reparse points refused on file and directories (new)**, download name from the resolved path | revision 2 assumed no links inside the base directory | CONTEXT (rev 2 from V3: reports served unauthenticated) |
| RV-39 | `cross_file_object_authz_safe/` | `GET /api/reports/{id}` | `reportId` → service ownership check → repository | the caller's own report | `[Authorize]`, ownership check in the service on the only path | none | SAFE |
| EI | `enterprise_identity/token_validation_safe.cs` | `GET /api/timesheets/mine` | bearer token → full validation | the caller's object id | issuer, audience, lifetime, signature, HTTPS metadata, endpoint `RequireAuthorization`; configuration required at start-up | none | SAFE |
| EI | `enterprise_identity/group_authorization_safe.cs` | `GET /admin/payroll/export` | groups claim → policy | payroll export | `[Authorize(Policy)]`, authenticated user, group check, overage denied (an unregistered policy fails closed) | none | SAFE |
| EI | `enterprise_identity/ldap_connection_safe.cs` | `GET /api/directory/people` | `name` → escaped LDAP filter over LDAPS | colleagues' mail and phone (≤ 25) | `[Authorize]`, LDAPS, injected bind credential required, RFC 4515 escaping, size limit | none; a corporate directory's intended function | SAFE |
| EI | `enterprise_identity/group_lookup_fail_closed_safe.cs` | authorization handler | user name → directory group lookup | grants or denies | denies on failure or timeout; unregistered → the requirement never succeeds | none | SAFE |
| EI | `enterprise_identity/windows_auth_negotiate_safe.cs` | `GET /whoami`, `POST /admin/reset-kiosk/{id}` | Windows identity → group SID policy; custom header | the caller's own name; a kiosk reset (admins) | fallback policy (authenticated), group policy, custom-header CSRF control, configuration required | none | SAFE |
| EI | `enterprise_identity/identity_config_missing_safe.cs` | `GET /hr/cases` | OIDC sign-in → groups claim | case ids | refuses to start without https/tenant/group configuration; group-restricted fallback policy | none | SAFE |

**Result:**

| Verdict | Count | Cases |
|---|---|---|
| SAFE | 18 | RV-02, 06, 07, 11, 13, 17, 20, 22, 31, 33, 35, 39 and the 6 EI cases |
| CONTEXT | 6 | RV-04, RV-15, RV-24, RV-26, RV-28, RV-37 |

Every CONTEXT case was made verifiable inside a V4-release fixture that keeps the row's tested property. No case had
to be dropped or have its expected result changed, so the audit found no stop.
