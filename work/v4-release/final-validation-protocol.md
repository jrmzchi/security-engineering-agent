# V4 final release validation — pre-registered protocol, revision 8 (2026-09-29)

Written and committed **before any model run** of this attempt. The user authorized:
- root-cause fixes for RV-18 and RE-08, with deterministic tests;
- one independent review, one concentrated fix, one fix-only re-review;
- then one complete validation of all 39 corpus and 13 enterprise-identity cases, collect-all as in revision 6.

That authorizes no weaker grader, no change to any V3 fixture, expected result or historical result, no package
installation or network operation, no stability measurement, no Jev call, and no further repair or rerun cycle.

**Release base:** the local `v3-slim-golden-baseline` tag, `f5502cdcd079a5589c39f667ebdfbb34e276aafd`.

**Earlier attempts, kept as records (none is a pass):**
- revisions 1–5 stopped at RV-02, RV-04, RV-15, RV-29 and RV-28;
- revision 6 ran 50 passed and 2 failed (RV-15, RV-29);
- **revision 7** (`92af53c`) ran 50 passed and 2 failed: RV-18 and RE-08. Its record is
  `work/v4-release/v4-release-report.md` §16, unchanged.

**RV-15 stays NOT RESOLVED.** Its revision-7 pass is not a resolution. No express-session was installed. See revision
7's "RV-15 local check" in this file at commit `92af53c`.

## RV-18: root cause and fix

**Root cause.**
- Outside DEEP, `domains` is chosen by item 0 — the classification is a reasoning pass, and no deterministic rule sits
  under it. The DEEP algorithm (`tools/context_manifest/domains.py`) does keep web-security for CSRF unless "never
  uses a cookie or ambient auth for a state change" is positively confirmed, but nothing applied that rule outside
  DEEP.
- In revisions 6 and 7, item 0 left out `web-security` for RV-18: a cookie-authenticated account deletion reached by
  GET, with `SameSite=Lax`.
- Revision 6's runner read `plays/web-security.md` anyway and CONFIRMED. Revision 7's runner read only the listed
  domains' plays and stayed "within the reviewed domains".
- The documents allowed that reading: `plays/review-budget.md` said the domain set was "fixed", and nothing said
  whether `domains` bounds the findings.

**Decision (user, 2026-09-29).** `domains` is the **minimum** set whose plays must be read, **not a boundary** on
findings.
- A concrete candidate of another domain, shown by the code in scope, brings that one domain's play in.
- A budget level never does.
- No review loads every play.

**Fix.**
- **New product module** `tools/context_manifest/signal_floor.py`, a deterministic floor. Today it has one rule,
  CSRF-AMBIENT: an ambient browser credential plus a state-changing endpoint, both in scope, requires web-security.
  - An ambient credential is cookie authentication, a server session cookie, or Windows Integrated Authentication.
  - A state-changing endpoint is POST/PUT/PATCH/DELETE, or a GET whose route names a state-changing action.
  - It only adds a domain. Its patterns are a stated proxy.
- `orchestrator.produce_manifest(scope_texts=...)` applies the floor to item 0's classification. The widened
  classification is the floor for both producers, so the validator rejects any candidate without it.
- SKILL step 1 says to pass `scope_texts`. SKILL step 5 states the minimum-not-boundary rule.
  `plays/review-budget.md` and `plays/security-change-detection.md` ("Domains a signal pair requires") agree with it.
- **Adapter:** `relman.py` now passes the case workspace's file texts as `scope_texts`, as the kit's step 1 does in
  real use. `caseval.py` passes the workspace path and records the floor's reason per classification run. Grading is
  unchanged.

**Where the floor fires in this corpus.** Checked by a test. It fires on 5 of the 52 cases:
- RV-18;
- RV-28 (a Flask session and an upload POST, expected safe);
- RE-09, RE-10 and RE-11. RE-10 is expected safe; its state-changing POST requires a custom header.

That is by design: each of these has both halves of the signal pair.

**Attribution caveat.** This round's changes can move any row, not only the floor rows:
- the floor makes RV-28 and RE-10, both expected safe, read `plays/web-security.md`;
- step 5's minimum-not-boundary rule applies to every case: a candidate of another domain brings one more play in;
- the rewritten stable-identifier rule applies to every enterprise-identity group-mapping row.
A result that changes relative to revision 7 is to be weighed against all three.

## RE-08: trust boundary and guidance

Full record: `work/v4-release/re08-group-identifier-evidence.md`.
- **The fixture:**
  - the group DN is a compile-time constant;
  - the identity is the host's authenticated principal;
  - success is granted only on membership;
  - a lookup failure denies.
- **Who can change what the DN names:** only a directory writer, by rename, move, or delete and recreate. A rename or
  move fails closed. A second object with the same DN cannot exist. No request value reaches the DN.
- **Classification:** no untrusted-attacker path, so it is not a security vulnerability. It leaves an
  availability/configuration risk and an environment assumption.
- **Root cause of the finding:** the play's stable-identifier rule named "display name / sAMAccountName" and "can be
  renamed", with no rule for a unique-but-mutable name. By the user's decision (2026-09-29) the rule now separates the
  cases:
  - a display name is not a security identity key, so keying on one is a finding;
  - sAMAccountName and DNs are decided by the case's trust boundary and attacker privilege:
    - a fail-closed rename, move or delete is an availability/configuration risk;
    - control over the directory object is an environment assumption;
    - a security finding needs an ambiguous match across scopes, a wrong identity mapping, an authorization bypass,
      or a breach of an explicit policy to be shown.
- **General authorization rules are unchanged.** The test file checks that "any signed-in user", group-claim overage
  and the fail-open lookup rules are still present.

## Tests

- `tools/context_manifest/tests/test_release_rv18_re08.py`, 16 tests. They cover:
  - the floor on RV-18;
  - that both halves are needed;
  - that the halves may sit in different files;
  - general, non-RV-18 cases, positive and negative;
  - the exact set of corpus cases where the floor fires;
  - input checks;
  - `produce_manifest` with and without `scope_texts`;
  - that the floor never removes a domain;
  - that a manifest without the floor domain fails validation;
  - the SKILL, budget, change-detection and web-security play text;
  - RE-08's trust-boundary facts in the fixture;
  - the new identity-rule text, with the unchanged rules still present.
- **Mutants killed:** floor union removed from the orchestrator; rule firing on one half; SKILL minimum paragraph
  removed; play rule reverted.
- **Adapter tests:** relman passes the workspace (a CSRF pair reaches the manifest; an empty workspace is a
  manifest problem).
- **What the tests do not show:** that a reviewer now reads `plays/web-security.md` and confirms RV-18. The manifest
  now carries web-security, and step 5 makes its play mandatory, but whether the reviewer then confirms it is shown
  only by the validation run.

## Review

One independent review found no Blocker and no Major, and said READY.

**Fixed in the one concentrated fix:**
- **Docs that still read `domains` as a boundary:** `plays/secure-development-workflow.md` "Targeted review",
  `plays/scanner-selection.md` and the bold sentence in `plays/review-budget.md` now point to step 5's
  minimum-not-boundary rule.
- **The attribution caveat above** now covers every row.
- **Smaller wording fixes:**
  - SKILL step 1's pronoun;
  - the RE-08 record now marks the out-of-case `IDirectoryGroups` behaviour after a rename as an environment
    assumption;
  - the RV-15 pointer now names commit `92af53c`.

**Recorded, not fixed:**
- A caller that passes `scanner_selection` must account for the floor's domain, otherwise production fails loudly.
  This is documented in `signal_floor.py`; the harness passes none.
- The floor's known misses and false fires are listed in its docstring, including the Django half that never pairs.
  The patterns were not widened, because that would change the pinned fire set.
- The audit cannot tell "floor not evaluated" from "evaluated, nothing added".
- **Open question for the user, not changed:** in TARGETED mode with NONE sensitivity, the floor scans whole files
  and can add web-security, bypassing the "nothing to decide" shortcut. This round runs STANDARD.

One fix-only re-review followed.

## Pins

| Item | Value |
|---|---|
| Tree validated | `315af46758de82381b70a14b2be945d2c9aec9bc` |
| Product code changed relative to revision 7 | `tools/context_manifest/signal_floor.py` (new), `tools/context_manifest/orchestrator.py` (the optional `scope_texts`) |
| Guidance changed relative to revision 7 | `skills/security-review/SKILL.md`, `plays/review-budget.md`, `plays/security-change-detection.md`, `plays/enterprise-identity-security.md`, `tools/README.md` |
| Kit export | tree sha256 `b90751e370dee58eab8ca4a8690219aa371f6c8b71b64c9ecbeacb428b9b00d7` (new). It is checked at initialisation; a different value stops the run |
| Corpus manifest | `tests/validation/v4-release-corpus-v5-manifest.json`, `v4-release-corpus/5`, sha256 `ffab03e8ff549ca0214338f1beed743f83a9ea77a034e83a6e3e23e61432f741` (unchanged) |
| Expected results | `expected-results.md` `2fac68d5...`; `v4-release-corpus.md` `b6e6d6a9...`; `v4-enterprise-identity-expected-results.md` `320581bc...` (all unchanged) |
| Fixtures | unchanged since revision 6 (corpus `/5`) |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, Read/Grep/Glob + the result tool, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, read-only; sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, not shipped) | `caseval.py` `15e0dbb14b3ce953311c8132d4895d0b95327dc6fa65b8a2542684081ca6dea2`, `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00` (unchanged), `relman.py` `55c307b741ed7985cdee659798082a576613ec0f04ebe96e3fd3628415596f23` (LF-normalized); run with `CASEVAL_CORPUS_MANIFEST=tests/validation/v4-release-corpus-v5-manifest.json` and `CASEVAL_CORPUS_VERSION=v4-release-corpus/5` |
| Jev | not called in this phase |

**Stop rule for this round (user, 2026-09-29):**
- The validation runs collect-all (rule 7).
- If any case fails, the result is `V4_RELEASE_NOT_READY`, the results are kept, and no further repair or rerun cycle
  is opened.
- RV-15's unknown status is not reported as resolved, whatever its outcome.

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
scan must still hold on the validated tree (product code as listed under Pins) for `V4_RELEASE_READY`. Anything else is `V4_RELEASE_NOT_READY`, with no further
repair or validation cycle.
