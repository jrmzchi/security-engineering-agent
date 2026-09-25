# V4 final release validation — pre-registered protocol, revision 5 (2026-09-25)

Written and committed **before any model run** of this attempt. The user authorized:
- one evidence-based, symmetric correction of RV-29;
- one independent review of it, one fix-only re-review;
- then one final validation.

That authorizes no product change, no product-guidance change, no weaker grader, no rewriting of historical results
or stops, no Jev call, and no further repair or validation cycle.

**Release base:** the local `v3-slim-golden-baseline` tag, `f5502cdcd079a5589c39f667ebdfbb34e276aafd`. It is not
`origin/v3-slim`, which was force-updated to an unrelated history (`39a7b0b`) and is handled separately.

**Earlier attempts, kept as records (none is a pass):**
- **Revision 1** (`cf6fe8d`) stopped at RV-02: CWE-306 on the V3 `sql_injection_safe.py`.
- **Revision 2** (`868ef5d`, corpus `/1`) stopped at RV-04: CWE-88 on the V3 `command_injection_safe.js`.
- **Revision 3** (`7d1a767`, corpus `/2`) stopped at RV-15: a missing auth guard on the V3 `cors_restricted_safe.js`.
- **Revision 4** (`cedcf19`, corpus `/3`) stopped at RV-29, an expected-**unsafe** row
  (`upload_webroot_content_disposition_deceptive.cs`). The runner confirmed both path traversals but left
  upload -> stored XSS at NEEDS_VERIFICATION: the static-file serving it depends on is asserted only in the fixture's
  stripped comments. The record is `work/v4-release/v4-release-report.md` §13, unchanged.

## The RV-29 correction (corpus `v4-release-corpus/4`)

The strict standard that revision 3 applied to safe rows now applies to this unsafe row as well. Per
`plays/finding-validation.md`, a control or execution path the review scope does not show is not assumed to exist,
and an impact that depends on it is not CONFIRMED.

- **Fixture:** `tests/fixtures/v4_release/upload_static_hosted_program_deceptive.cs` (git blob `9824286c`). It
  is a complete single-file ASP.NET Core app, so the row keeps its V3 `single` form. `UploadStorage.Directory` is
  both the upload destination and the `PhysicalFileProvider` that `app.UseStaticFiles(...)` publishes under
  `/uploads`. The V3 fixture, `expected-results.md` and every historical result are unchanged.
- **Expected result:** CONFIRMED, as three separately graded findings (rule 4a below). They are defined in the
  manifest row's `expectedFindings`.
- **Manifest:** only RV-29 differs from `/3`. The other 38 rows and the enterprise-identity set have the same parsed
  values as in `/3` (checked by `tools/context_manifest/tests/test_release_corpus.py`).
- **Adapter:**
  - RV-29 is the only expected-unsafe row that may be replaced, and only together with `expectedFindings`.
  - A manifest that puts `expectedFindings` on any other row, replaces RV-29 without them, carries malformed findings
    (including a non-string or duplicate `id`), or whose `rowId` (unchanged rows) or `replaces.rowId` (replaced rows)
    differs from the V3 mapping, stops the run.
  - **Recorded limit, not fixed** (fix-only re-review, Minor): a replaced row's own `rowId` is not checked for
    uniqueness. The pinned `/4` manifest has 39 distinct `rowId` values.
- **Review:** one independent review found no Blocker or Major. Its Minor findings were handled before this protocol
  was committed:
  - the `id` type check and the `rowId` cross-check were added, each with adapter tests and mutants;
  - the keyword-proxy limits were recorded in rule 4a;
  - the fixture was reordered so that `UseStaticFiles` and the `Upload` action fit one citation of at most 30 lines,
    with no change in meaning.
  One fix-only re-review followed.

## Pins

| Item | Value |
|---|---|
| Tree validated | `d67a81c4ede9356445c1dfe613dec64e64ecc006`: product code identical to `644d419`; the commit adds only the RV-29 fixture, the `/4` manifest, the corpus document and `test_release_corpus.py` changes |
| Kit export | tree sha256 `989958851b518c4a6ba132120e94f7ca8b4fe12b5606158f4b1b22e86997d525`, identical to the `644d419` export (checked at initialisation; a different value stops the run) |
| Corpus manifest | `tests/validation/v4-release-corpus-v4-manifest.json`, `v4-release-corpus/4`, sha256 `8ba55ec401bca54bfbe78354f43ee1e2e0803cc7fe1958aeb016b50cb29d0954` (git blob `0ce919b4`), read from the pinned commit |
| Expected results | `expected-results.md` `2fac68d5...` (unchanged); `v4-release-corpus.md` `ac2c7221...`; `v4-enterprise-identity-expected-results.md` `320581bc...` (unchanged) |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, Read/Grep/Glob + the result tool, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, read-only; sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, not shipped) | `caseval.py` `5e9c3432c95ea58fa8955b0d79f9fde48742a0e4d68cc1e11464e524029d3c38`, `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `6e18acc02f8c847d3394d1374afc1e22c26df0aff82bd705af3fa6d47aa79d7d` (LF-normalized); run with `CASEVAL_CORPUS_MANIFEST=tests/validation/v4-release-corpus-v4-manifest.json` and `CASEVAL_CORPUS_VERSION=v4-release-corpus/4` (a manifest whose version differs stops the run) |
| Jev | not called in this phase |

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
   class. The remediation after-row needs `STILL_VULNERABLE` for SQL injection. (In `/4`, RV-29 no longer uses the
   V3 upload fixture; rule 4a replaces its requirement.)
4a. **RV-29 in `/4`** (revision 5) is graded by the manifest row's `expectedFindings`, not by keywords alone:
    - **Three findings:** path traversal on upload (arbitrary write), path traversal on download (arbitrary read), and
      unrestricted upload -> stored XSS.
    - **What binds a finding:** a **CONFIRMED** entry whose category or summary contains at least one alternative
      from **each** keyword group of the manifest row, and whose evidence cites the case file with, for **every**
      anchor range of that finding, a range that overlaps it.
    - **Keywords are a proxy**, as in rule 5a: case-insensitive substring matching, without word boundaries. A
      sentence can match through an unrelated word (e.g. "script" inside "description"). An entry that cites a
      traversal action and happens to say "read" can also account for the other traversal in its group. This is
      recorded, not corrected, because the evidence binding and the separate stored-XSS entry remain required.
    - **Anchor ranges:** located on the comment-stripped file the runner sees, from the manifest's code anchors. The
      traversals need the `Upload` or the `Download` action respectively. Stored XSS needs **both** the
      `UseStaticFiles` configuration **and** the `Upload` action.
    - **Limits:** a cited range longer than 30 lines binds nothing. An anchor that does not resolve can never be met.
    - **Separate entries:** the two traversal findings may share one entry; the stored-XSS finding must be a
      different entry.
    - **Failure:** a finding left at NEEDS_VERIFICATION, or cited without the lines that prove it, is not accounted
      for, and the case fails.
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

**Result rule.** All 52 cases (39 rows of `v4-release-corpus/4` + 13 enterprise-identity rows) must pass. Beyond that, the product unit tests, fallback checks, review gate and privacy
scan must still hold on the validated tree (product code identical to `644d419`) for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
