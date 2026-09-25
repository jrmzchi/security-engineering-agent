# V4 final release validation — pre-registered protocol, revision 4 (2026-09-25)

Written and committed **before any model run** of this attempt. The user authorized one bounded audit of the safe
fixtures under a stricter standard, followed by one final validation. That authorizes no product change, no lowering
of the security standard, no rewriting of historical results, no Jev call, and no further audit or validation cycle.

**Earlier attempts, kept as records (none is a pass):**
- **Revision 1** (`cf6fe8d`) stopped at RV-02: CWE-306 on the V3 `sql_injection_safe.py`.
- **Revision 2** (`868ef5d`, corpus `/1`) stopped at RV-04: CWE-88 on the V3 `command_injection_safe.js`.
- **Revision 3** (`7d1a767`, corpus `/2`) stopped at RV-15: a missing auth guard on the V3 `cors_restricted_safe.js`,
  a row the previous audit had kept.

**The audit behind revision 4** (`work/v4-release/safe-fixture-audit.md`): every expected-safe case (18 corpus rows
and 6 enterprise-identity rows) was re-audited under a strict standard. A safe negative's security may not depend on
middleware, session setup, a proxy or anything else the case does not contain.
- **18 cases are safe as they are.**
- **6 needed context, now made verifiable inside a V4-release fixture:** RV-04, RV-15, RV-24, RV-26, RV-28 and RV-37.
- **No case had to be dropped or have its expected result changed**, so the audit found no stop.
- **Corpus:** `v4-release-corpus/3`, 11 replaced rows. It is **not** a V3-versus-V4 comparison set.

## Rows that differ from the V3 corpus

| Row | V3 fixture (unchanged) | V4-release fixture in `/3` (git blob) | New in `/3`? |
|---|---|---|---|
| RV-02 | `sql_injection_safe.py` | `v4_release/catalog_lookup_parameterized_safe.py` `35613a3d` | no |
| RV-04 | `command_injection_safe.js` | `v4_release/command_argument_array_bounded_safe.js` `71345e8d` | yes (was `...allowlisted_safe.js`) |
| RV-13 | `cookie_secure_safe.js` | `v4_release/cookie_flags_anonymous_session_safe.js` `eb52f3e4` | no |
| RV-15 | `cors_restricted_safe.js` | `v4_release/cors_allowlist_session_guarded_safe.js` `cb20c3a8` | yes |
| RV-20 | `redirect_local_safe.cs` | `v4_release/local_redirect_preferences_safe.cs` `5380fa8c` | no |
| RV-22 | `ssrf_allowlist_safe.py` | `v4_release/ssrf_allowlist_pinned_safe.py` `e853ca76` | no |
| RV-24 | `path_traversal_safe.cs` | `v4_release/public_document_download_nolinks_safe.cs` `7bfa688b` | yes (was `...download_safe.cs`) |
| RV-26 | `path_prefix_after_canonicalization_safe.cs` | `v4_release/path_prefix_canonicalized_nolinks_safe.cs` `bc501856` | yes |
| RV-28 | `file_upload_safe.py` | `v4_release/file_upload_authenticated_safe.py` `d71cad6a` | yes |
| RV-35 | `cross_file_sql_safe/` | `v4_release/cross_file_catalog_search_safe/` (`43a94310`, `b5ebbacd`, `0231c7be`) | no |
| RV-37 | `cross_file_path_traversal_safe/` | `v4_release/cross_file_public_manual_download_nolinks_safe/` (`ManualDownloadController.cs` `f88de47d`, `ManualFileService.cs` `c41b25d3`, `ManualPathHelper.cs` `66838cb2`) | yes (was `...download_safe/`) |

Reasons are in the manifest (`replaces.reason`, plus `previousV4Fixture` where a revision-2 fixture is superseded) and
in `tests/validation/v4-release-corpus.md`. Every replaced row keeps its V3 form, member and "no confirmed finding"
expectation. The adapter refuses a manifest in which any other row differs, or in which an expected-unsafe row is
replaced.

## Pins

| Item | Value |
|---|---|
| Tree validated | `4e4e6269202724911ca7b6ab34920191cbe988ee`: product code identical to `644d419`; adds only fixtures, manifests, documents and `tools/context_manifest/tests/test_release_corpus.py` |
| Kit export | tree sha256 `989958851b518c4a6ba132120e94f7ca8b4fe12b5606158f4b1b22e86997d525`, identical to the `644d419` export |
| Corpus manifest | `tests/validation/v4-release-corpus-v3-manifest.json`, `v4-release-corpus/3`, sha256 `10133e15fffb79ef83261add82d2811035cb5e0b84c00e777907e8b4860a8aea` (git blob `b78eed85`), read from the pinned commit |
| Expected results | `expected-results.md` `2fac68d5...` (unchanged); `v4-release-corpus.md` `63d2e34a...`; `v4-enterprise-identity-expected-results.md` `320581bc...` (unchanged) |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, Read/Grep/Glob + the result tool, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, read-only; sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, not shipped) | `caseval.py` `d3acdd90b0ffa7620e64e2b659f9bd13ec8bd169b7202221af64a7b45dcf4fef`, `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `6e18acc02f8c847d3394d1374afc1e22c26df0aff82bd705af3fa6d47aa79d7d` (LF-normalized) |
| Jev | not called in this phase |

**Change to the adapter in revision 4 (rule 5a below).**
- The review prompt tells the runner that a NEEDS_VERIFICATION entry must name what is missing. This matches the
  kit's own "say what evidence would resolve it" (`plays/finding-validation.md`).
- The grader rejects a safe case whose NEEDS_VERIFICATION entry does not name it.

The adapter was tested with 20 synthetic cases before dispatch. That covers the earlier revisions' binding, grading
and manifest checks, the `/3` plan, and the new rule: a vague NEEDS_VERIFICATION is rejected and a specific one is
accepted.

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
5a. **NEEDS_VERIFICATION on a safe case** (revision 4) is acceptable only when its summary names the specific
    missing control or evidence. The mechanical proxy is pre-registered: the summary is at least 40 characters and
    contains one of a fixed list of phrases ("not shown", "not included", "outside the", "cannot be confirmed",
    "depends on", "relies on", "missing", "would need", and others). It is a proxy: it can pass a vague sentence
    that uses such a phrase, and fail a specific one that does not. A failure under it is still a failed case.
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

**Result rule.** All 52 cases (39 rows of `v4-release-corpus/3` + 13 enterprise-identity rows) must pass. Beyond that, the product unit tests, fallback checks, review gate and privacy
scan must still hold on the validated tree (product code identical to `644d419`) for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
