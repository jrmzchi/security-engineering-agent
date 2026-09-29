# V4 final release validation — pre-registered protocol, revision 9 (2026-09-29)

Written and committed **before any model run** of this attempt. The user authorized:
- one local, isolated express-session check for RV-15;
- the decision that the CSRF signal floor also applies in TARGETED mode at NONE sensitivity, with tests;
- one independent review, and a fix-only re-review if it finds a Blocker/Major;
- then, because the kit hash changes, one complete validation of all 39 corpus and 13 enterprise-identity cases,
  collect-all as in revision 6.

That authorizes no push, no merge, no tag, no history rewrite, no other network use, no stability measurement, no
Jev call, and no further repair or rerun cycle.

**Release base:** the local `v3-slim-golden-baseline` tag, `f5502cdcd079a5589c39f667ebdfbb34e276aafd`. Remote history
is not handled in this round.

**Earlier attempts, kept as records:**
- revisions 1–5 stopped at RV-02, RV-04, RV-15, RV-29 and RV-28;
- revisions 6 and 7 each passed 50 of 52;
- **revision 8** (`b561c4c`) passed 52 of 52: gate MET, `V4_RELEASE_READY` by its result rule. Its record is
  `work/v4-release/v4-release-report.md` §17, unchanged.

## What changed

**RV-15 — local check done:** `work/v4-release/rv15-local-check.md`.
- **Versions:** express-session **1.19.0** (pinned exactly) and express 5.2.1, installed with `--ignore-scripts` in
  an isolated scratch directory outside the repository, on Node v26.7.0.
- **Input:** the fixture, unchanged: blob `cb20c3a8`, the same as the committed file.
- **Result:** 515 requests per transport (plain HTTP, and simulated TLS for the fixture's `secure` cookie) created or
  kept **0** MemoryStore records. There were no `set`, `touch` or `destroy` calls and 0 Set-Cookie headers.
  - 50 of the requests carried a cookie validly signed with the fixture's own secret, for a session that does not
    exist. Each caused one `get` on the fixture's own store; still nothing was saved.
  - Two positive controls stored 50 of 50, showing the instrumentation works.
- **Conclusion, for that version only:** RV-15's revision-6 "session flooding" finding does not reproduce, so it was a
  review false positive. No fixture or expectation changed, and no historical result is rewritten.

**Signal floor at TARGETED / NONE** (user decision, 2026-09-29).
- **Checked:** the floor already applies. The orchestrator's step 0a widens item 0's classification before the NONE
  shortcut (1a) and before both producers and the validator. So a NONE change with both signals gets web-security,
  and the shortcut is not taken.
- **No product code behaviour changed.** Edited: a comment in `orchestrator.py`, the `signal_floor.py` docstring,
  `plays/review-budget.md` (the NONE note after the Applicability matrix) and `plays/security-change-detection.md`
  ("whatever the sensitivity, NONE included").
- **Workflow reachability** (review Major, fixed): the workflow's NONE stop came before the manifest step, so the floor
  was unreachable from the workflow. `plays/secure-development-workflow.md` ("NONE -> stop here") and
  `plays/security-change-detection.md`'s NONE action now carry one exception: when the scope shows both halves of the
  signal pair, the manifest is built as TARGETED and only that domain is reviewed (its play read), at MINIMAL budget.
  `AGENTS.md` and `CLAUDE.md` point to that exception. Sensitivity is not raised, no design step runs, and no other
  play is loaded.
- **New tests** in `tools/context_manifest/tests/test_release_rv18_re08.py`:
  - **positive:** TARGETED/NONE with both signals gives web-security, with and without a token. With a token, the
    NONE shortcut is not taken; without one, the no-token path is reached first;
  - **negative:** missing either signal adds nothing, and the shortcut is still taken;
  - **document assertions,** including the NONE exception in all four documents.
  The mutant "floor skipped at NONE" is killed.
- `domains` stays a minimum, not a boundary (SKILL step 5). The floor still adds only web-security, and only on the
  signal pair.

**Corpus, fixtures, grader, adapter:** unchanged from revision 8.

## Review

- **Independent review:** one Major, fixed in the one concentrated fix — the NONE exception above.
- **Also fixed:**
  - the RV-15 record's signer version (express-session's own cookie-signature is 1.0.7);
  - a validly-signed-cookie scenario added to the RV-15 check (above);
  - the Result rule's pointer (the product-code row below);
  - the positive test's wording;
  - the orchestrator comment's `scope_texts` condition.
- **Recorded:** the RV-15 conclusion also follows from the code alone (`saveUninitialized: false`, no route writes the
  session); the behavioural check confirms it for the tested versions.
- **Fix-only re-review:** READY, with no new Blocker/Major. Recorded, not fixed, per the bounded cycle; both Minors
  concern only the TARGETED/NONE path, which this STANDARD validation does not exercise:
  - **Minor:** the NONE exception is triggered when "the scope shows" the pair. It does not yet require running
    `signal_floor.required_domains()` on the scope, so an agent that misses the pair still stops at NONE.
  - **Minor:** the NONE exception does not say how it relates to the NONE row's "no scanner / no summary". The
    exception's manifest selects semgrep, and "No security theater" has no outlet for a finding from that review.
  - **Nit:** `CLAUDE.md` says "that play's" after naming the skill.

## Pins

| Item | Value |
|---|---|
| Tree validated | `fe3f6462d9835f00446f1a23f6c2904979e6c08c`: relative to revision 8, only the comment/docstring/guidance edits and tests above, plus the RV-15 record |
| Product code changed relative to revision 8 | none in behaviour: a comment in `tools/context_manifest/orchestrator.py` and the `tools/context_manifest/signal_floor.py` docstring. Guidance changed: `plays/review-budget.md`, `plays/security-change-detection.md`, `plays/secure-development-workflow.md`, `AGENTS.md`, `CLAUDE.md`. Code otherwise as in revision 8 (`315af46`) |
| Kit export | tree sha256 `812115b5d6bee4e525d50ae16d80278d776a5668322fd43a29fc6b9ae35137f2` (changed only because of the guidance and comment text). It is checked at initialisation; a different value stops the run |
| Corpus manifest | `tests/validation/v4-release-corpus-v5-manifest.json`, `v4-release-corpus/5`, sha256 `ffab03e8ff549ca0214338f1beed743f83a9ea77a034e83a6e3e23e61432f741` (unchanged) |
| Expected results | `expected-results.md` `2fac68d5...`; `v4-release-corpus.md` `b6e6d6a9...`; `v4-enterprise-identity-expected-results.md` `320581bc...` (all unchanged) |
| Runner | restricted `claude -p` (CLI `2.1.282`), `--model sonnet` (`claude-sonnet-5`), effort `high`, Read/Grep/Glob + the result tool, no shell |
| Structured-channel library | `v4-planning` at `72dadd1`, read-only; sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| External adapter (local, not shipped) | `caseval.py` `15e0dbb14b3ce953311c8132d4895d0b95327dc6fa65b8a2542684081ca6dea2`, `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`, `relman.py` `55c307b741ed7985cdee659798082a576613ec0f04ebe96e3fd3628415596f23` (all unchanged, LF-normalized); run with `CASEVAL_CORPUS_MANIFEST=tests/validation/v4-release-corpus-v5-manifest.json` and `CASEVAL_CORPUS_VERSION=v4-release-corpus/5` |
| Jev | not called in this phase |

**Stop rule for this round (user, 2026-09-29):** the validation runs collect-all (rule 7). If any case fails, the
result is `V4_RELEASE_NOT_READY`, the results are kept, and no second repair or stability cycle is started.

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
