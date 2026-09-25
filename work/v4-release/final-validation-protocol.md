# V4 final release validation — pre-registered protocol (2026-09-25)

Written and committed **before any model run**. One attempt, authorized by the user, on the existing reviewed product
commit. It authorizes no product change and no further fix or review cycle.

## Pins

| Item | Value |
|---|---|
| Product commit validated | `644d4191dd9e69c69e207c5f93c535ac1e1b6ea9` (commits after it change only `work/v4-release/`) |
| Kit export | `git archive` of that commit: kit paths, package tests dropped; tree sha256 `989958851b518c4a6ba132120e94f7ca8b4fe12b5606158f4b1b22e86997d525` |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, tools Read/Grep/Glob + the result tool only, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, used read-only as a library (transcript, context and channel checks); package sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, outside the release tree, not shipped) | `caseval.py` `241738efa75f4594e0946f7441b22010bbf52d88abf2772b1fd1f0960cdd48a4`, `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `6e18acc02f8c847d3394d1374afc1e22c26df0aff82bd705af3fa6d47aa79d7d` (LF-normalized) |
| Manifests | built and validated by the release tree's own `tools/context_manifest` (identical at `644d419`), no key |
| Jev | not called |

The adapter's binding and grading were tested with 18 synthetic positive and negative cases before dispatch (another
case's file, `..` and absolute paths, lines outside the file, a wrong case or run id, a status the form forbids, an
unbound member, missing evidence; stored-XSS accounting, distinct findings, safe-case CONFIRMED, wrong class). The
server itself was also exercised over JSON-RPC: it rejected a foreign path, accepted a valid submission and refused
a duplicate.

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
4. **Grading** against the expected-results sources, per entry text (category and summary). Distinct expected findings
   need distinct entries:
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

**Result rule.** All 52 cases must pass. Beyond that, the product unit tests, fallback checks, review gate and privacy
scan must still hold on `644d419` for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
