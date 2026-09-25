# V4 final release validation — pre-registered protocol, revision 2 (2026-09-25)

Written and committed **before any model run** of this attempt. It is one final attempt, authorized by the user after
the RV-02 decision. It authorizes no product change and no further fixture, fix or review cycle.

**What changed from revision 1 (`cf6fe8d`, stopped at RV-02):** only the corpus.
- That attempt's RV-02 answer, a CONFIRMED missing-authentication finding on the V3 `sql_injection_safe.py`, is
  accepted as a real vulnerability in that fixture. It is not suppressed, and the "safe case: no CONFIRMED" rule is
  unchanged.
- The validation now uses the versioned corpus `v4-release-corpus/1`
  (`tests/validation/v4-release-corpus-manifest.json`). RV-02 maps to
  `tests/fixtures/v4_release/catalog_lookup_parameterized_safe.py`; the other 38 rows map to their unchanged V3
  fixtures and expected results.
- It is **not** a V3-versus-V4 comparison set (`tests/validation/v4-release-corpus.md`).
- Rules 1–9 are unchanged, apart from the reading of rule 4 and the addition of rule 10.

## Pins

| Item | Value |
|---|---|
| Tree validated | `ef8a9e471e18a74fe0186be3a1019f5e971240ed`: product code identical to `644d419`; adds only the RV-02 fixture, the corpus manifest and document, and `tools/context_manifest/tests/test_release_corpus.py` |
| Kit export | `git archive` of that commit (kit paths, package tests dropped); tree sha256 `989958851b518c4a6ba132120e94f7ca8b4fe12b5606158f4b1b22e86997d525`, identical to the `644d419` export |
| Corpus manifest | `v4-release-corpus/1`, sha256 `08cc741c8017f57766429240f9b845c7de6b7fac22a03a6513bac4854bf2ef5b`; the adapter reads it from the pinned commit (never the working tree) and stops if a row other than the recorded RV-02 replacement differs from the original 39-row mapping |
| Expected results | `expected-results.md` `2fac68d5…`, `v4-release-corpus.md` `3e55aad1…`, `v4-enterprise-identity-expected-results.md` `320581bc…` |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, tools Read/Grep/Glob + the result tool only, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, used read-only; package sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, outside the release tree, not shipped) | `caseval.py` `de7f62c627324fed0e986f946a5406108e8f96da75d2ffcaafd5e643ddd9aae7` (revision 1 plus the manifest-driven plan), `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `6e18acc02f8c847d3394d1374afc1e22c26df0aff82bd705af3fa6d47aa79d7d` (LF-normalized) |
| Manifests | built and validated by the release tree's own `tools/context_manifest` (no key) |
| Jev | not called |

The adapter's binding, grading and manifest handling were tested before dispatch with 20 synthetic cases. That
covers revision 1's 18, plus: the plan is taken from the pinned manifest, and a tampered manifest (changed row,
missing replacement record, other version, missing row) stops the run.

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

**Result rule.** All 52 cases (39 corpus rows + 13 enterprise-identity rows) must pass. Beyond that, the product unit tests, fallback checks, review gate and privacy
scan must still hold on `644d419` for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
