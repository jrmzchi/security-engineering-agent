# V4 final release validation — pre-registered protocol, revision 7 (2026-09-29)

Written and committed **before any model run** of this attempt. The user authorized:
- a fix of the confirmed RV-29 product miss in the kit's guidance;
- a local, reproducible investigation of RV-15;
- one independent review, one fix-only re-review;
- then one complete validation of all 39 corpus and 13 enterprise-identity cases, collect-all as in revision 6.

That authorizes no weaker grader, no change to RV-29's vulnerability facts or to any V3 fixture, expected result or
historical result, no stability measurement, no Jev call and no second repair or validation cycle.

**Release base:** the local `v3-slim-golden-baseline` tag, `f5502cdcd079a5589c39f667ebdfbb34e276aafd`.

**Earlier attempts, kept as records (none is a pass):**
- revisions 1–5 stopped at RV-02, RV-04, RV-15, RV-29 and RV-28;
- **revision 6** (`bc7abdc`, corpus `/5`, collect-all) ran all 52 cases: 50 passed and 2 failed.
  - RV-15: CONFIRMED LOW on express-session's default MemoryStore.
  - RV-29: stored XSS not reported.
  - The record is `work/v4-release/v4-release-report.md` §15, unchanged.

## What changed

- **RV-29 root cause:** the stored-XSS guidance already existed at `plays/file-security.md` ("Uploads"). The
  revision-6 RV-29 runner read only the case file and `skills/security-review/SKILL.md`, and never opened the play.
  Across the 52 revision-6 reviews, 16 read any play and 1 read `plays/file-security.md`. By the user's decision
  (2026-09-29), the fix covers both files. These are **product guidance** changes; no product code changed:
  - `skills/security-review/SKILL.md` step 5: reading `plays/<domain>.md` for every selected domain is mandatory
    before step 6, at every budget level.
  - `plays/file-security.md` "Uploads": four explicit checks for an upload written under a served directory:
    hosting, public URL, content type, and same-origin inline rendering. Stored XSS is CONFIRMED only when all four
    are established from code in scope. When the upload lands under a web-root-like directory but the hosting or URL
    mapping is not in scope, the result is NEEDS_VERIFICATION naming the missing evidence; hosting is never assumed.
  - Regression tests: `tools/context_manifest/tests/test_release_guidance_rv29.py`, plus one adapter test. The
    adapter test shows that the revision-6 RV-29 answer still FAILS on the missing `upload-stored-xss` finding, so
    no threshold was lowered. `caseval.py`, `caseresult.py` and `relman.py` are unchanged.
  - **What these tests protect, and what they do not.** They fail if the SKILL paragraph or the play block is
    removed (checked by removing each), and if the old answer would be let through. Their decision function is a
    fixture-bound proxy of the rule. That the miss was the reviewer not reading the play cannot be reproduced
    deterministically; whether a reviewer now applies the play is shown only by the validation run below.
- **RV-15:** not resolved (see "RV-15 local check" below). Its fixture and its expected result ("no confirmed
  finding") are unchanged.
- **Corpus, fixtures, grader, adapter:** unchanged from revision 6. Corpus `/5`; `caseval.py` is the same file as in
  revision 6 (only the adapter's tests gained the test above).
- **Review:** one independent review found no Blocker and no Major, and said READY. By the user's procedure a
  fix-only cycle applies to Blocker/Major only, so the reviewed guidance is committed unchanged. These Minors are
  recorded, not fixed:
  - The play's three "->" outcomes have no stated precedence. Case one: an upload under `wwwroot/` with a forced
    safe extension shown in code, but no hosting in scope, matches both "NEEDS_VERIFICATION" and "a check fails".
    Case two: a case where checks 1–2 are established but 3 or 4 is neither shown nor refuted (e.g. a custom
    content-type provider outside the scope) has no stated outcome. No `/5` row falls into either case.
  - The test proxy's limits, now stated in its docstring.
  - Wording in this protocol, now corrected.
- **Attribution caveat:** reading every selected domain's play now applies to every case. If a safe row gets a new
  CONFIRMED in this round, that change is a possible cause to weigh when classifying it.

## RV-15 local check (before any model run)

- **Question:** does express-session, configured as in the fixture, create or keep MemoryStore records for requests,
  when `saveUninitialized: false` is set and no route writes to the session?
- **What the fixture shows:**
  - it pins no version: there is no package manifest in the case, only `require('express-session')`;
  - the configuration is `name: 'sid'`, `resave: false`, `saveUninitialized: false`, cookie `httpOnly`, `secure`,
    `sameSite: 'lax'`, `maxAge: 30 min`, and **no `store`**;
  - the one route only reads `req.session.userId`.
- **Environment:** Node `v26.7.0` is installed (`node --version`). express-session is **not available locally**.
  The method, all read-only:
  - `which node npm`;
  - a listing of the global module directory, which holds only `@anthropic-ai`, and of the Node installation's
    `node_modules`, which holds only `npm`;
  - a fixed-string search for `express-session` in the npm cache index, with 0 hits (the only related tarball is
    `express-5.2.1.tgz`);
  - a `find` for a directory named `express-session` under the user's documents, the global npm directory and the
    npm `_npx` cache, with none found (the reviewer repeated a search of the user directory to depth 7, with none
    found).

  Installing express-session needs a network download, and network operations and package installation are not
  authorized in this round.
- **Result: NOT RESOLVED.** No store state was observed. The row is not re-graded, and its expectation is not
  changed.
- **What would resolve it:** an authorized install of a stated express-session version into a scratch directory, and
  then a local script that sends requests to the fixture's app and inspects the MemoryStore's contents.

## Pins

| Item | Value |
|---|---|
| Tree validated | `b92b1efe2d177fde258dd53a6d02f8a8581aadff`: relative to revision 6, the commit changes only `skills/security-review/SKILL.md` (step 5) and `plays/file-security.md` ("Uploads") and adds `tools/context_manifest/tests/test_release_guidance_rv29.py`. Product Python code is identical to `644d419` |
| Kit export | tree sha256 `60090969f012b763eed97f50f8cfc606fadba001c9e9885f4703a88b048372a9` (**new**: the kit contains the changed skill and play). It is checked at initialisation; a different value stops the run |
| Corpus manifest | `tests/validation/v4-release-corpus-v5-manifest.json`, `v4-release-corpus/5`, sha256 `ffab03e8ff549ca0214338f1beed743f83a9ea77a034e83a6e3e23e61432f741` (unchanged), read from the pinned commit |
| Expected results | `expected-results.md` `2fac68d5...`; `v4-release-corpus.md` `b6e6d6a9...`; `v4-enterprise-identity-expected-results.md` `320581bc...` (all unchanged) |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, Read/Grep/Glob + the result tool, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, read-only; sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, not shipped) | `caseval.py` `d5a9517b8dc87a320426cae6cdf58c3f255da4b33376cf52f6761d1ae4d4d564` (unchanged), `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `6e18acc02f8c847d3394d1374afc1e22c26df0aff82bd705af3fa6d47aa79d7d` (LF-normalized); run with `CASEVAL_CORPUS_MANIFEST=tests/validation/v4-release-corpus-v5-manifest.json` and `CASEVAL_CORPUS_VERSION=v4-release-corpus/5` |
| Jev | not called in this phase |

**Stop rule for this round (user, 2026-09-29):** the validation runs collect-all (rule 7). If any case fails, the
result is `V4_RELEASE_NOT_READY` and no further repair or rerun cycle is opened.

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
   graded under the wrong case; as a `BINDING` failure it is a hard stop (rule 7).
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
7. **Collect-all, with hard stops** (revision 6).
   - **Valid but incorrect:** a valid answer that does not meet its expectation is recorded as `FAILED` and **never
     re-run**. Validation then **continues** with the next case, so that every failure of the round is collected.
     Continuing does not soften a failure: any `FAILED` case makes the release gate `NOT_MET`.
   - **Technical failure:** a run whose invalid-reason classes are all technical may be retried **once**, and both
     records are kept. The technical classes are `CHANNEL`, `TRANSCRIPT`, `ANSWER_SCHEMA`, `ANSWER_FORMAT` and
     `MANIFEST`. A case still invalid after the retry is recorded as `NOT_OBTAINED`, the run continues, and the gate
     is `NOT_MET`.
   - **Hard stop** (immediately, no retry; the run ends and is **not resumed**). The run record is kept first. The
     triggers are:
     - isolation: `LEAKAGE`, `TOOLS`, `INPUT`, `CONTEXT`, and `ISOLATION`. `ISOLATION` means any read outside the
       run's own case workspace and the kit (answer material or not, a credential file included), or a transcript
       whose working directory or additional directories are not the run's own;
     - a pin mismatch: `CONTEXT_DRIFT`, `IDENTITY`, `MODEL_EFFORT`, and the kit, workspace, CLI-version and
       manifest-version checks;
     - a workspace containing answer material, or differing from its plan;
     - an earlier attempt that was interrupted: its run directory already exists. An adapter interrupted mid-run
       (Ctrl-C, crash) therefore ends this validation; it is not retried;
     - a review stage without a classification manifest;
     - an evidence-binding failure: `BINDING`;
     - a credential in the adapter's environment (`TYPESAFE_API_KEY`); a runner reading a credential file is covered
       by `ISOLATION`;
     - a record that does not read back identical after it is written;
     - an unexpected case outcome, or any reason class not listed here.
     Every one of these stops is written into the run state, and the driver refuses to continue a stopped
     validation. The manifest-version and manifest-shape checks run at initialisation, before any state exists; they
     prevent the run from starting.
   - **Isolation roots:**
     - Every session scratchpad of this project, and the adapter directory itself, are forbidden roots. That includes
       earlier bases and their records.
     - Only the runner's own case workspace and the kit are allowed. Any other read is a hard stop, as above.
     - For calibration: a transcript scan of all 114 revision-4 and revision-5 runs found no such read.
   - **Frozen during the run:** nothing may change mid-run — no fixture, product, prompt, grader, expected result,
     protocol or adapter.
   - **After the run:** every non-passing case is listed and classified as one of:
     - a product defect;
     - a fixture defect;
     - a grading or harness defect;
     - insufficient evidence.
     A classification that has not been checked against the code is marked **pending**, not guessed.
8. **No answer exposure.** Runners never see fixture names, expected results or other cases; the kit is the pinned
   export.
9. **Limit.** One run per case does not establish run-to-run stability.
10. **A finding on another safe fixture.** If any other safe case gets a valid, evidence-backed CONFIRMED finding,
    it is a `FAILED` case (rule 7: recorded, and the run continues). The finding is not dismissed, and the fixture
    is not reclassified or edited in this attempt.

**Result rule.** All 52 cases (39 rows of `v4-release-corpus/5` + 13 enterprise-identity rows) must pass. Any
`FAILED` or `NOT_OBTAINED` case, or a hard stop, makes the gate `NOT_MET`. Beyond that, the product unit tests, fallback checks, review gate and privacy
scan must still hold on the validated tree (product Python code identical to `644d419`; the skill and play changed as above) for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
