# V4 release validation corpus (`v4-release-corpus/5`)

The V4 release is validated against a versioned corpus with 39 rows, `RV-01` to `RV-39`.

- **Current version:** `v4-release-corpus/5`, `tests/validation/v4-release-corpus-v5-manifest.json`.
- **Earlier versions, kept as records:** `/1` (`v4-release-corpus-manifest.json`), `/2`
  (`v4-release-corpus-v2-manifest.json`), `/3` (`v4-release-corpus-v3-manifest.json`) and `/4`
  (`v4-release-corpus-v4-manifest.json`).

27 rows are the V3 corpus rows of `tests/validation/expected-results.md`, unchanged: same fixtures, members, forms
and expected results. **11 safe rows use V4-release fixtures**, listed below, and **one unsafe row, RV-29, uses a
V4-release fixture** (see "RV-29" below).

**This corpus is not a V3-versus-V4 comparison set.** Because 12 rows differ, a result on it cannot be compared
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
| RV-24 | `path_traversal_safe.cs` | an "uploads" directory (user-supplied content) is served to unauthenticated callers (CWE-862) | `tests/fixtures/v4_release/public_document_download_nolinks_safe.cs` | `GetFullPath` containment with a trailing separator (published manuals). **New in revision 3:** no Windows reparse point is followed on the file or on any directory below the base. A junction is rejected (verified); symbolic-link rejection was not verified on this machine; a Linux mount point is not a reparse point. Hard links: see "Hard links" below |
| RV-26 | `path_prefix_after_canonicalization_safe.cs` | links inside the base directory are left out of scope: an environment assumption the case does not show | `tests/fixtures/v4_release/path_prefix_canonicalized_nolinks_safe.cs` | the containment check on the canonicalized path with a trailing separator (the control-holds counterpart of the deceptive fixture), now with no link followed |
| RV-28 | `file_upload_safe.py` | anonymous uploads, with no access control or quota in the case | `tests/fixtures/v4_release/file_upload_authenticated_quota_atomic_safe.py` (revision 5) | size cap, magic-byte type check, generated name, storage outside served paths. The signed-in guard, the session cookie (SameSite=Strict) and a per-user quota are in the case. **New in revision 5:** the quota slot is reserved atomically (see "RV-28" below) |
| RV-35 | `cross_file_sql_safe/` | an unauthenticated user search returns users' e-mail addresses (CWE-306/CWE-359) | `tests/fixtures/v4_release/cross_file_catalog_search_safe/` | a parameterized LIKE query reached across three files (public catalog fields, 50-row cap) |
| RV-37 | `cross_file_path_traversal_safe/` | a "reports" directory is served to unauthenticated callers; its sensitivity is not established by the code | `tests/fixtures/v4_release/cross_file_public_manual_download_nolinks_safe/` | canonicalized containment reached across three files (published manuals). **New in revision 3:** no reparse point is followed. Hard links: see "Hard links" below |

Every safe replacement row's expected result is **No confirmed finding**, with the same trap as its V3 row: a reviewer
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

## RV-29 (revision 4): an unsafe row whose impact depended on code the case did not show

The same standard applies to an expected-**unsafe** row: a finding may be CONFIRMED only on what the case shows
(`plays/finding-validation.md`). A control or execution path the review scope does not contain is not assumed to
exist, and an impact that depends on it is not CONFIRMED.

- **V3 fixture (unchanged):** `upload_webroot_content_disposition_deceptive.cs`. Its expected impact, stored XSS,
  needs the upload directory to be served as static content. Only its comments say so (`UseStaticFiles()`); its code
  has no hosting configuration. With comments stripped, a review following the play leaves stored XSS at
  NEEDS_VERIFICATION. The revision-4 validation did exactly that at RV-29.
- **V4-release fixture:** `tests/fixtures/v4_release/upload_static_hosted_program_deceptive.cs`, a complete
  single-file ASP.NET Core app (a `Program.cs` with top-level statements), so the row keeps its single-file form.
  `UploadStorage.Directory` is both the directory `UploadController` writes into and the `PhysicalFileProvider` that
  `app.UseStaticFiles(...)` publishes under `UploadStorage.RequestPath` (`/uploads`), with the extension-based content
  types (`.html` is served as `text/html`). The deceptive part is kept: the download endpoint sets
  `Content-Disposition: attachment`, which a direct request to `/uploads/...` never reaches.
- **Expected result: CONFIRMED, graded as three separate findings.** Each finding needs a CONFIRMED entry that names
  its class and cites the lines of the case file that prove it. The manifest row's `expectedFindings` holds the
  keywords and the code anchors from which those lines are located:

  | Finding | Must cite | Group |
  |---|---|---|
  | path traversal on upload (arbitrary file write, CWE-22) | the `Upload` action | traversal |
  | path traversal on download (arbitrary file read, CWE-22) | the `Download` action | traversal |
  | unrestricted upload -> stored XSS (CWE-434 + CWE-79) | the `UseStaticFiles` configuration **and** the `Upload` action | stored-xss |

  The two traversal findings may share one entry. The stored-XSS finding must be a separate entry. A citation longer
  than 30 lines binds no finding.
- **Checked by running it** (2026-09-25, scratchpad build, localhost only, not part of the corpus):
  - the file compiles against .NET 8;
  - an uploaded `x.html` is served at `/uploads/x.html` as `text/html` with no `Content-Disposition`;
  - the upload file name `../../escaped.txt` is written outside the directory;
  - `/download?name=../../...` reads a file outside the directory.

## RV-28 (revision 5): an atomic per-user quota

The revision-5 validation CONFIRMED a race condition (TOCTOU) in the revision-3 RV-28 fixture
`tests/fixtures/v4_release/file_upload_authenticated_safe.py`: it counts the user's directory and writes the file
afterwards, so concurrent requests can all pass the count. That file is kept unchanged as the **regression input**.
It is no longer a corpus row.

- **Replacement:** `tests/fixtures/v4_release/file_upload_authenticated_quota_atomic_safe.py`. Every other control of
  the previous fixture is kept.
- **The quota:** before anything is written, the request takes one of `MAX_FILES_PER_USER` numbered slot files with
  `os.open(..., O_CREAT | O_EXCL)`.
  - That is one atomic filesystem operation, so it holds across threads and across worker processes that use the
    same `UPLOAD_ROOT` on a local filesystem.
  - It is not a lock inside one process, and no protection across hosts is claimed.
  - A failed write deletes only the file the request created and releases its slot.
  - A worker that dies after reserving leaves its slot taken, so the quota errs towards refusing uploads.
- **Checked by** `tools/context_manifest/tests/test_release_fixture_quota.py`. The fixture's own code runs against a
  minimal stand-in for Flask, which the kit does not depend on. Interleavings are forced with barriers, not sleeps:
  - the regression input stores 4 files under a quota of 1 when every request passes the count before any writes;
  - the replacement stores exactly the quota: across threads, with every request forced to reserve at the same moment
    (1 of 4, 3 of 8); and across 6 spawned processes started together behind one barrier (2 of 6);
  - a failed write and a name collision each release the slot and leave no file of their own (and not someone
    else's);
  - removing `O_EXCL`, or the release on failure, makes these tests fail.

## Hard links (RV-24, RV-26, RV-37)

The reparse-point check in these three fixtures does not detect hard links. This was verified by a mechanism test: a
hard link already inside the base directory is accepted by all three, and RV-24 was seen serving its outside content. None of the three cases has any write path into its base
directory, so no attacker of the case can create one. The attack is **not established**, and the fixtures are
unchanged.

The per-case evidence, the prerequisites (write access to the base, the same filesystem, Linux
`protected_hardlinks`) and what was not verified are in `work/v4-release/hard-link-threat-model.md`.

`tools/context_manifest/tests/test_release_corpus.py` checks all five manifests deterministically:
- the mapping of every unchanged row against the V3 table;
- each current replacement fixture's tested property and visible controls;
- that no safe replacement fixture exposes user or account data it does not need;
- that RV-29's anchors exist in the V4-release fixture, and that the V3 fixture has no hosting code for the stored-XSS
  finding to bind to;
- that RV-28's replacement keeps the previous fixture's controls and reserves its quota with an exclusive create.
