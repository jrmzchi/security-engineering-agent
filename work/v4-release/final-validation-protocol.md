# V4 final release validation — pre-registered protocol, revision 3 (2026-09-25)

Written and committed **before any model run** of this attempt. The user authorized a bounded audit of every
expected-safe case followed by one final validation. That authorizes no product change, no gate relaxation, no
rewriting of historical results, and no further audit or validation cycle.

**Earlier attempts, kept as records (neither is a pass):**
- **Revision 1** (`cf6fe8d`) stopped at RV-02. The V3 `sql_injection_safe.py` returns users' e-mail addresses without
  authentication, and the review CONFIRMED it (CWE-306).
- **Revision 2** (`868ef5d`, corpus `v4-release-corpus/1`) stopped at RV-04. The V3 `command_injection_safe.js`
  passes a request value to ImageMagick `convert`, and the review CONFIRMED it (CWE-88).

**The audit behind revision 3.** All 24 expected-safe cases (18 corpus rows and 6 enterprise-identity rows) were read
on their actual code; the details are in `tests/validation/v4-release-corpus.md`.
- **8 V3 fixtures have a real or evidence-supported incidental weakness:** RV-02, RV-04, RV-13, RV-20, RV-22, RV-24,
  RV-35 and RV-37. Each is replaced, for the V4 release corpus only, by a V4-release fixture that keeps the tested
  property.
- **16 cases are kept unchanged:** the other 10 corpus rows and all 6 enterprise-identity rows.
- **Every case could be fixed without changing its tested property,** so the audit found no stop.
- **Jev** (the phase's last call) was advisory only.
- **Rules 1–10 below are unchanged.**
- **Revision 3 corpus:** `v4-release-corpus/2`. It is **not** a V3-versus-V4 comparison set.

## Rows that differ from the V3 corpus

| Row | V3 fixture (unchanged) | V4-release fixture (git blob at the validated commit) |
|---|---|---|
| RV-02 | `sql_injection_safe.py` | `v4_release/catalog_lookup_parameterized_safe.py` `35613a3d` |
| RV-04 | `command_injection_safe.js` | `v4_release/command_argument_array_allowlisted_safe.js` `08de10ed` |
| RV-13 | `cookie_secure_safe.js` | `v4_release/cookie_flags_anonymous_session_safe.js` `eb52f3e4` |
| RV-20 | `redirect_local_safe.cs` | `v4_release/local_redirect_preferences_safe.cs` `5380fa8c` |
| RV-22 | `ssrf_allowlist_safe.py` | `v4_release/ssrf_allowlist_pinned_safe.py` `e853ca76` |
| RV-24 | `path_traversal_safe.cs` | `v4_release/public_document_download_safe.cs` `6288fd9b` |
| RV-35 | `cross_file_sql_safe/` | `v4_release/cross_file_catalog_search_safe/` (`ProductRepository.cs` `43a94310`, `ProductSearchService.cs` `b5ebbacd`, `ProductsController.cs` `0231c7be`) |
| RV-37 | `cross_file_path_traversal_safe/` | `v4_release/cross_file_public_manual_download_safe/` (`ManualDownloadController.cs` `1a8357be`, `ManualFileService.cs` `ca00bb18`, `ManualPathHelper.cs` `4226eeef`) |

The reason for each replacement is in the manifest's `replaces.reason` field and in `v4-release-corpus.md`. Every
replaced row keeps its V3 form, member and "no confirmed finding" expectation. The adapter refuses a manifest in which
any other row differs, or in which an expected-unsafe row is replaced.

## Pins

| Item | Value |
|---|---|
| Tree validated | `53ef5397e091fa784ef3049f9b41dcacce3c469e`: product code identical to `644d419`; adds only fixtures, corpus manifests and documents, and `tools/context_manifest/tests/test_release_corpus.py` |
| Kit export | `git archive` of that commit (kit paths, package tests dropped); tree sha256 `989958851b518c4a6ba132120e94f7ca8b4fe12b5606158f4b1b22e86997d525`, identical to the `644d419` export |
| Corpus manifest | `tests/validation/v4-release-corpus-v2-manifest.json`, `v4-release-corpus/2`, sha256 `cd6f8e96f11163a8a9cfdf171a1e2a08ebe8269bb5b4d68fbc62fec7df6f510e` (git blob `52668972`); read from the pinned commit, never the working tree |
| Expected results | `expected-results.md` `2fac68d5…` (unchanged); `v4-release-corpus.md` `0051c4dc…`; `v4-enterprise-identity-expected-results.md` `320581bc…` (unchanged) |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, tools Read/Grep/Glob + the result tool only, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, used read-only; package sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, outside the release tree, not shipped) | `caseval.py` `8f4a9767714032fc3e103c0dc996959ed08a9742e23f6654ba09728350eed8db`, `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `6e18acc02f8c847d3394d1374afc1e22c26df0aff82bd705af3fa6d47aa79d7d` (LF-normalized) |
| Manifests | built and validated by the release tree's own `tools/context_manifest` (no key) |
| Jev | not called during validation |

The adapter was tested with 20 synthetic cases before dispatch:
- the binding, grading and plan checks of the earlier revisions;
- the v2 plan read from the pinned manifest;
- the refusal of a tampered manifest: a changed row, a missing replacement record, a changed expected result or form,
  a replacement naming the wrong original, a replacement of an expected-unsafe row, the wrong version, or a missing
  row.

## Rules

1. **One case, one workspace, one request.** Each of the 39 V3 corpus rows (`tests/validation/expected-results.md`)
   and each of the 13 enterprise-identity rows (`tests/validation/v4-enterprise-identity-expected-results.md`) gets
   its own workspace, containing only that row's files with neutral names and the header and answer comments
   stripped. No sibling case is visible.
   - Rows that share a file (the three `ef_fromsqlraw_vs_interpolated.cs` methods) each get their own copy, bound to
     one method.
   - A pair's before row sees only the before file. The pair-diff after row sees before, after and diff. The
     version-pair after row sees before and after.

   Each case has two requests: classification, then a review with the manifest built from it. Both are bound to the
   same case.
2. **Binding.**
   - The result tool's schema is built per case: a fixed harness case id (`RV-nn` / `RE-nn`), the evidence file
     enumerated as exactly that case's files, the member fixed to the bound method or side, and the status set fixed
     by the case form.
   - Every entry carries status, category, severity, evidence (file plus start and end line) and a summary.
   - Line ranges must lie inside the cited file.
3. **Post-submission re-check.** The harness re-validates the accepted submission: case id, members, that every cited
   path belongs to the case, and line ranges. A response that cites another case's files is **invalid** and is never
   graded under the wrong case.
4. **Grading** against the expected-results sources of the pinned corpus (per row, as the manifest's
   `expectationSource` names), per entry text (category and summary). Distinct expected findings need distinct
   entries:
   - `hardcoded_secret_unsafe.py`: the AWS key pair and the database connection string;
   - `ldap_connection_unsafe.cs`: cleartext bind, hardcoded password, and LDAP filter injection.

   `upload_webroot_content_disposition_deceptive.cs` passes only if an entry separately accounts for **upload → stored
   XSS**; reporting only path traversal is incomplete. `file_upload_unsafe.py` must account for both unrestricted
   upload and path traversal via the file name. Every other CONFIRMED row needs a CONFIRMED entry naming its weakness
   class. The remediation after-row needs `STILL_VULNERABLE` for SQL injection.
5. **Per-case-form status contract** (enforced by the schema): standalone forms allow CONFIRMED / NOT_CONFIRMED /
   NEEDS_VERIFICATION; the version-pair after side allows STILL_VULNERABLE / RESOLVED / NOT_APPLICABLE. No safe case
   may have any CONFIRMED entry (NEEDS_VERIFICATION is acceptable). No expected unsafe finding may be lost.
6. **Enterprise identity:** same product tree, same isolation and binding rules.
7. **Technical versus incorrect.**
   - A technical or schema-invalid run may be retried **once**, and both records are kept. That covers: no accepted
     submission, channel, transcript or context check failure, binding failure, or manifest production failure.
   - A **valid but incorrect** answer is a failed case and is never re-run.
   - Validation stops at the first failed or not-obtained case, and the result is `V4_RELEASE_NOT_READY`.
8. **No answer exposure.** Runners never see fixture names, expected results or other cases; the kit is the pinned
   export.
9. **Limit.** One run per case does not establish run-to-run stability.
10. **A finding on another safe fixture.** If any other safe case gets a valid, evidence-backed CONFIRMED finding,
    validation stops and reports it as a failed case. The finding is not dismissed, and the fixture is not
    reclassified or edited in this attempt.

**Result rule.** All 52 cases (39 rows of `v4-release-corpus/2` + 13 enterprise-identity rows) must pass. Beyond that, the product unit tests, fallback checks, review gate and privacy
scan must still hold on `644d419` for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
