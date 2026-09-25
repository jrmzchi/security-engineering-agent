# V4 release completion report (2026-09-25)

**Final status after the RV-29 correction and protocol revision 5: `V4_RELEASE_NOT_READY` (not pushed).**

- **RV-29 correction** (`d67a81c`, corpus `v4-release-corpus/4`): a self-contained V4-release fixture whose hosting
  path is code (`app.UseStaticFiles` publishes the upload directory). It is graded as three evidence-bound findings.
  One independent review found no Blocker or Major; the fix-only re-review said READY.
- **Validation** (`298fb31`, one attempt): RV-01 to RV-27 passed. It stopped at **RV-28**
  (`v4_release/file_upload_authenticated_safe.py`, expected safe), **before RV-29 was reached**.
  - The answer was valid and correctly bound: one CONFIRMED MEDIUM finding, a race condition (TOCTOU) upload-quota
    bypass (`case_25.py:55-62`).
  - The per-user cap is checked with `len(os.listdir(user_dir))` and the file is written afterwards, with no lock or
    atomic reservation. The code confirms it.
  - Per rule 10 it is reported, not dismissed; the fixture was not edited and the case was not rerun.
- **Own miss, recorded:** the independent review had named this exact weakness as an open doubt before the run. I did
  not change it, because that safe fixture was outside this batch. The revision-4 run of the same fixture had passed
  (NOT_CONFIRMED), which also shows the one-run-per-case limit.
- **Not reached:** RV-29 to RV-39 and all 13 enterprise-identity cases. The RV-29 fixture is therefore checked only
  deterministically and by running it locally, not by a model review.
- **Still holding on the final tree:** product tests (261 and 354 OK), fallbacks, feedback-record checks, consistency
  wrappers and the privacy scan.

Section 14 has the details; sections 1–13 are the earlier attempts, unchanged.

**Final status after the strict safe-fixture audit and protocol revision 4: `V4_RELEASE_NOT_READY` (not pushed).**

- **Audit** (`4e4e626`, corpus `v4-release-corpus/3`): all 24 expected-safe cases were re-read under a strict standard.
  A safe negative must contain the controls its safety depends on. 18 were safe as they were. 6 got a V4-release
  fixture with the needed controls inside the case: RV-04, RV-15, RV-24, RV-26, RV-28 and RV-37. Jev was not called.
- **Validation** (`cedcf19`, one attempt): RV-01 to RV-28 passed, including all 9 replaced rows reached (RV-02, 04, 13,
  15, 20, 22, 24, 26, 28). It stopped at **RV-29** (`upload_webroot_content_disposition_deceptive.cs`, an expected
  **unsafe** row).
  - The answer was valid and correctly bound. It CONFIRMED two path traversals (upload write, download read) but put
    **upload -> stored XSS** at NEEDS_VERIFICATION.
  - Its stated reason: the static-file serving of `wwwroot` (`UseStaticFiles`) is not in the reviewed file.
  - The pre-registered grading requires a CONFIRMED stored-XSS entry, so this is a failed case. It was not rerun, and
    the grader was not changed.
- **Recorded tension, not resolved here:** the fixture's code indeed contains no `UseStaticFiles()`; only the stripped
  header comments assert it. The strict standard applied in this audit (no middleware assumed that the case does not
  contain) was applied to safe cases only. Applied to this unsafe case, the runner's answer follows the same standard.
- **Not reached:** RV-30 to RV-39 and all 13 enterprise-identity cases.
- **Still holding on the final tree:** product tests (255 and 354 OK), fallbacks, feedback-record checks, consistency
  wrappers, the review gate and the privacy scan.

Section 13 has the details; sections 1–12 are the earlier attempts, unchanged.

**Final status after the safe-fixture audit and protocol revision 3: `V4_RELEASE_NOT_READY` (not pushed).**

- **Audit** (`53ef539`, corpus `v4-release-corpus/2`): all 24 expected-safe cases were read on their actual code. 8
  V3 safe fixtures with a real or evidence-supported incidental weakness got V4-release replacements; 16 cases were
  kept.
- **Validation** (`7d1a767`, one attempt): RV-01 to RV-14 passed, including the replaced RV-02, RV-04 and RV-13. It
  stopped at **RV-15** (`cors_restricted_safe.js`, a row the audit **kept**, with a residual note).
  - The answer was valid, correctly bound and evidence-backed, with one CONFIRMED MEDIUM finding: missing
    authentication/authorization check.
  - `/api/account` returns `req.session.user.email` and `.balance` with no session or login guard in the route or the
    file (`case_12.js:18-20`).
  - Per rule 10 it is reported, not dismissed, and the fixture was not reclassified or edited.
- **Audit miss, recorded:** the audit judged this case "no confirmed weakness; relies on session middleware not
  shown". Jev (advisory) had raised scrutiny on it (0.79); on re-inspection it was kept anyway. The review shows that
  judgment was wrong: relying on an unshown guard is a finding a correct review can confirm.
- **Not reached:** 24 corpus cases and all 13 enterprise-identity cases.
- **Still holding on the final tree:** product tests (250 and 354 OK), fallbacks, feedback-record checks, consistency
  wrappers, the review gate and the privacy scan.

Section 12 has the details; sections 1–11 are the earlier attempts, unchanged.

**Final status after protocol revision 2 (corrected RV-02): `V4_RELEASE_NOT_READY` (not pushed).**

- **RV-02 correction:** the RV-02 finding from revision 1 was accepted as a real vulnerability in the V3 fixture.
  RV-02 now uses the public catalog fixture (`v4-release-corpus/1`, commit `ef8a9e4`), and that fixture passed:
  NOT_CONFIRMED.
- **New stop:** validation stopped at case 4 of 52 on another safe V3 fixture with a valid, correctly bound,
  evidence-backed finding.
  - `RV-04` (`command_injection_safe.js`, expected: no confirmed finding) came back CONFIRMED, HIGH: argument
    injection (CWE-88).
  - `req.body.filename` reaches `execFile('convert', [filename, 'output.png'])` with no validation (`case_04.js:7-12`).
    `execFile` avoids shell injection, but an option-like or coder/protocol-prefixed value (`msl:`, `https:`, ...) is
    still interpreted by ImageMagick itself.
  - Per rule 10 the finding is reported, not dismissed, and the fixture was not reclassified or edited.
- **Other cases:** `RV-01`–`RV-03` passed. The remaining 35 corpus cases and all 13 enterprise-identity cases were not
  run.
- **Still holding on the final tree:** product tests (244 and 354 OK), fallbacks, consistency wrappers, the review gate
  and the privacy scan.

Section 11 has the details.

**Final status after the pre-registered final validation: `V4_RELEASE_NOT_READY` (not pushed).**

- **Protocol:** `work/v4-release/final-validation-protocol.md`, committed before any run (`cf6fe8d`). It uses one
  isolated workspace and request per case, a case-bound result schema, a post-submission binding check, and one retry
  for a technical failure only.
- **Outcome:** validation stopped at case 2 of 52.
  - `RV-01` (`sql_injection_unsafe.py`) passed.
  - `RV-02` (`sql_injection_safe.py`, expected: no confirmed finding) returned a **valid, correctly bound** answer with
    one CONFIRMED entry. The runner did not flag the parameterized query, which is the fixture's trap. It confirmed
    "Missing Authentication / Unauthorized PII Disclosure (CWE-306), MEDIUM" for the isolated Flask route
    (`case_02.py:7-18`), which serves users' e-mail addresses with no authentication check.
  - Under the protocol a safe case with any CONFIRMED entry is a failed case; it was not re-run, and validation stopped.
- **Not reached:** the remaining 37 V3 cases and all 13 enterprise-identity cases.
- **Still holding on product tree `644d419`:** unit suites (235 and 354 OK), fallbacks, the review gate (section 9) and
  the privacy scan.

Section 10 has the details. Sections 1–9 are the earlier attempts, unchanged.

**Terminal status after the separately authorized fix cycle 2: `V4_RELEASE_NOT_READY` (not pushed).**

- **Review gate: passed.** The first cycle's open Major (out-of-scope-caller rule) and Minor (STALE write blocked
  by a raising store call) were fixed. Cycle 2's one review found no Blocker/Major; its findings were fixed once; the
  fix-only re-review adopted the change with one open Nit.
- **Functional gate: failed on the final head `644d419`.** V3 corpus 38/39, enterprise identity 13/13, caller-scope set
  3/3. The failing row is the safe case `hardcoded_secret_example_value.py`, graded CONFIRMED. In the same answer the
  runner shifted its entries by one case: it reported `case_06_before`'s SQL injection under `case_07`, `case_07`'s
  hardcoded AWS key and database URL under `case_08` (the documentation-example file, which contains neither), and gave
  the example file no entry of its own. So the kit was not shown to confirm the example keys, but the run's per-case
  answers are wrong. Under the pre-registered grading the row fails, and two expected findings were lost (the
  hardcoded-secret finding under its own case; the upload-into-static-root stored-XSS finding, reported only as path
  traversal). Nothing was regraded and no slot was re-run (re-runs were pre-registered for invalid runs only).

Section 9 has the cycle-2 details. Sections 1–8 are the first release attempt, unchanged.

This is a separate release-completion phase, not Batch 8. Batch 5 `CLOSED`, Batch 6 `COMPLETE_INCONCLUSIVE` and
Batch 7 `COMPLETE_NO_GO` are unchanged and are not reinterpreted here.

## 1. Assembly

- Branch `v4-release`, based on `v3-slim-golden-baseline` (`f5502cd`). Source: `v4-planning` at `72dadd1`.
- Tree-level, path-limited import (`git checkout 72dadd1 -- <paths>`); no cherry-pick, no merge. 0 `v4-planning`-only
  commits are reachable from `v4-release`.
- Imported: `AGENTS.md`, `plays/`, `skills/`, `templates/`, `scripts/`, `tools/context_manifest/`,
  `tools/feedback_store/`, `tools/secret_heuristic.py`, `tools/README.md`, `tests/fixtures/`, `tests/validation/`, and the
  two design specifications the code cites (`work/v4-planning/context-manifest-schema.md`, `v4-design.md`, each with a
  release banner).
- Not imported (192 paths): `tools/batch{25,5,6,7}_measurement/`, all raw results and planning reports, the measurement
  runner agent definitions, and the `.gitattributes` rule that only pinned them.
- The assembly first produced 6 new `BROKEN_REFERENCE` hits (references to planning files not imported); those passages
  were made self-contained and the consistency check is back to the baseline's 23 hits.

## 2. Release-blocker audit

| # | Item | Disposition | Action |
|---|---|---|---|
| 1 | Finding validation: sink whose attacker control depends on out-of-scope callers | MUST_FIX_FOR_RELEASE | rule added (`5233964`), rewritten in the fix cycle (`67908c0`); **the rewrite has the open Major, section 5** |
| 2 | Feedback-store stale-lock double acquisition | MUST_FIX_FOR_RELEASE | breaker marker + re-check under it (`eec0f3f`) |
| 3 | `hop_key` delimiter collision | MUST_FIX_FOR_RELEASE | JSON-encoded pair (`eec0f3f`) |
| 4 | Go pointer-receiver / C++ anonymous-namespace `qualifiedSymbol` refused | ACCEPTED_LIMITATION | fail-closed (record refused); documented in README |
| 5 | One record id in both collections | MUST_FIX_FOR_RELEASE | load degrades, write refuses (`eec0f3f`) |
| 6 | Unicode format characters in paths | MUST_FIX_FOR_RELEASE | any Cf character rejected (`eec0f3f`) |
| 7 | Unreproduced feedback-store test failure | ACCEPTED_LIMITATION | 13 verbose full runs (4 concurrent, 6 under model-run load): 13/13 OK, no recurrence; still unresolved, no assertion changed |
| 8 | AD/SSO functional and safety coverage | MUST_FIX_FOR_RELEASE (evidence gap) | enterprise-identity corpus run: 13/13 (section 4) |
| 9 | Operation without Python / without Jev key / after Jev failure | MUST_FIX_FOR_RELEASE | verified (section 4); Evidence Reuse had no no-Python rule and could be hand-applied (fail-open) → now off without Python (`26a0d62`) |
| 10 | Release-tree privacy and credential hygiene | MUST_FIX_FOR_RELEASE | five fixtures used a real user name → replaced in the import commit (`de2e7d4`); scans in section 7 |
| — | Batch 5/6/7 harness findings (N1–N5, AD/SSO path defect, routing-causality experiment, Batch 2.5 parser follow-ups) | MEASUREMENT_ONLY | not touched |
| — | V3 chaining-example wording; hand-maintained rule copies; planning-branch history paths | OUT_OF_SCOPE | unchanged (user decisions stand) |

Found during validation and fixed: the upload-into-static-root finding (CWE-434 + CWE-79) was reported only as path
traversal; `plays/file-security.md` now states it is its own finding and that a download handler's
`Content-Disposition` does not protect a file served directly from the static root (`1f9b411`).

## 3. Jev assistance (5 of 8 calls; sanitized)

| # | Question category | Candidates | Jev outcome | Claude decision | Accepted? |
|---|---|---|---|---|---|
| 1 | Release-blocker classification (16 items) | MUST_FIX / ACCEPTED_LIMITATION / MEASUREMENT_ONLY / OUT_OF_SCOPE | ok; 11 agree | as in section 2 | item 6: Jev ACCEPTED_LIMITATION (0.75) **rejected** (would lower scrutiny); items 7, 13, 14 low confidence (0.24–0.40) → fallback to Claude |
| 2 | Adversarial case selection (16 cases) | yes / no per case | ok; no additions | all 15 "yes" cases implemented | `hop_forms` "no" (0.44, unsure) **rejected** (cannot remove a test) |
| 3 | Product path, valid key | — | success; floor kept, 4 domains added | Jev manifest accepted by the validator | yes (scrutiny raised only) |
| 4 | Product path, synthetic invalid key | — | invalid_token (HTTP 401) | built-in fallback | yes |
| 5 | Release evidence coverage (9 criteria) | COVERED / PARTIALLY / NOT_COVERED | ok | c08 review gate NOT_COVERED (agree, 0.94) | c02 corpus and c09 privacy raised to PARTIALLY (0.79 / 0.57) **accepted** (single run; inherited path); c01 low confidence → fallback |

The credential was read only inside the calling process and passed only to the Jev client; it appears in no file,
log, prompt, commit or output. Jev never waived or lowered a gate.

## 4. Tests and validation

| Gate | Result |
|---|---|
| `tools/context_manifest/tests` | 221 OK |
| `tools/feedback_store/tests` | 332 OK (2 skipped), incl. 16 new release tests that fail against the pre-release modules |
| V3 validation corpus, final head `67908c0` | **39/39 PASS**, 16/16 model runs valid, every row a valid per-form status, 0 expected unsafe findings lost, 0 safe cases CONFIRMED, every expected defect class named |
| Enterprise-identity corpus, final head | **13/13 PASS**, same checks |
| No key / valid key / rejected key / malformed answers / non-JSON body / secret-shaped field | built-in / Jev accepted / built-in / built-in / built-in / never sent |
| Fresh / stale / malformed / ambiguous records | only the fully confirmed fresh record is reusable; 8 other cases → full validation |
| Review-budget single entry point | one function, both producers and both procedures use it |
| Consistency wrappers | PS 5.1 (5.1.26100), PS 7 (7.6.6), Bash on Windows: 23 hits each, twice, idempotent; without Python: `ERROR`, exit 2. **The Bash run on Windows is not a macOS validation.** |

Validation channel: the restricted `claude -p` runner (`claude-sonnet-5`, effort high, CLI 2.1.282) with a result tool
enforcing the per-case-form status contract (`batch5/status-form-1`); the kit is a `git archive` export of the release
head; manifests are built and validated by the release tree's own producer (no key). The runner lives outside the
repository and is not part of the release. Differences from the pre-review pass (on `fa3dfa4`, 39/39 and 13/13 on
status, 2 category misses): the enterprise-identity fixtures' trailing answer comments are stripped, and each recall
prompt asks for one entry per distinct defect. Both were fixed before the final run. Single run per group; run-to-run
variance is not measured.

## 5. Review

- One independent review (6 commits): 1 Major, 1 Minor, 2 Nits, 2 open questions. The Major was that an in-scope safe
  caller could make a real public sink REJECTED.
- One fix cycle (`67908c0`): all items addressed.
- One fix-only re-review: items 1–5 closed, but **new**:
  - **Major (open):** the rewritten out-of-scope-caller rule (`plays/finding-validation.md`) has no category limit and
    forbids an in-scope caller from making a candidate REJECTED. An authorization sink whose control sits in the caller
    by design (e.g. `tests/fixtures/cross_file_object_authz_safe/`, expected no confirmed finding) can therefore be
    read as CONFIRMED. The final corpus run did not show it (that case stayed NOT_CONFIRMED), but one run does not close a
    rule-text defect.
  - **Minor (open):** "a raising `tools/feedback_store` call = degraded store, no write" (`skills/security-review` step 2,
    the play's reuse section) also blocks step 6's `mark_stale` of a record the new validation contradicts.
- No further round was started.

## 6. Safe defaults

- Built-in manifest is the default.
- Jev is optional and fails closed; Jev and Evidence Reuse are labelled experimental.
- An invalid manifest is rejected whole.
- Evidence is reused only after every check, and is off without Python or after a raising call.
- Reuse cannot change scanners or candidates.
- Enterprise identity loads only on its signals.
- No token, cost or speed claim appears in the release documentation.

## 7. Privacy and credential scan

- All 7 release commits and the final tree were scanned:
  - credential value: 0;
  - local paths or personal names in new content: 0;
  - raw model output: 0;
  - monetary data: 0;
  - secret-shaped lines: all synthetic test values or the intentionally vulnerable fixture's fake password.
- Commit identity is the GitHub noreply address already used by the published baseline.
- **Inherited (not rewritten):** `work/v3-slim/phase0-baseline-record.md` line 5 contains a local path with a user
  name. It is byte-identical in the published `v3-slim-golden-baseline`.
- `master`, `v3-slim`, `v4-planning` and the baseline tag are unchanged.

## 8. Next

A separately authorized fix cycle would need to:
- limit the out-of-scope-caller rule to injection-type sinks, keeping caller tracing for authorization;
- keep the STALE write when a call raises;
- rerun one review and the corpus.

Only then could the branch be pushed.

## 9. Fix cycle 2 (separately authorized, 2026-09-25)

**Fixes.**

- `4b1cb17`, out-of-scope-caller rule, split by vulnerability class:
  - Injection presumption: kept only for an exhaustive injection list, and only when the parameter flows into a sink
    whose unsafe behaviour is evidenced at the sink.
  - Authorization: never CONFIRMED from "public" or "unseen caller". Every in-scope path is traced; object-level
    authorization needs an ownership or tenant check (a role check alone does not satisfy it). An undecidable caller or
    control gives NEEDS_VERIFICATION.
  - Any class: an unsafe in-scope path is never erased by unseen or safe callers.
- `4b1cb17`, new caller-scope set: `tests/fixtures/caller_scope/`, 3 cases, its own figure outside the 39-row corpus.
- `4b1cb17`, `store.invalidate_contradicted()`:
  - marks a contradicted record STALE with the locked, atomic write, or quarantines the store;
  - a quarantined store loads as degraded and nothing is reused until `store.recover_quarantine()` verifies the
    record;
  - if the quarantine marker cannot be written either, it raises.
- `644d419`: the marker has its own lock (both races the reviewer reproduced are now tested), plus
  `store.load_for_invalidation()` for quarantined runs, the injection list marked exhaustive, and wording fixes.

**Required cases.**

| Required case | Covered by |
|---|---|
| 1, 2 | V3 `cross_file_object_authz_safe/` / `_unsafe/` |
| 3 | `ef_fromsqlraw_vs_interpolated.cs` + `sqli_public_method_safe_in_scope_caller/` |
| 4 | `authz_callerless_repository_unverified.cs` |
| 5 | `authz_unsafe_in_scope_path/` |

On the final head:
- all authorization cases are correct: `idor`, both `cross_file_object_authz` cases, CS 1 NOT_CONFIRMED, CS 2
  CONFIRMED;
- CS 3 and `ef-unsafe` are CONFIRMED.

**Tests.**

| Suite | Result |
|---|---|
| `context_manifest` | 235 OK |
| `feedback_store` (verbose) | 354 OK, 2 skipped |
| New tests against the pre-fix code | fail |
| Race tests with the marker lock stubbed out | fail |

**Other checks.**

- Consistency: PS 5.1, PS 7 and Bash on Windows give 23 hits each, twice; without Python all three exit 2. The Bash
  run on Windows is not a macOS validation.
- Fallbacks: no key → built-in; malformed and non-JSON output → built-in; a secret-shaped field is never sent; a real
  HTTP 401 → `invalid_token` → built-in.
- Feedback records: fresh, stale, malformed and ambiguous cases all behave as before.

**Review.**

- One review of `c3782a3..4b1cb17`: 0 Blocker/Major, 3 Minor, 2 Nit, 2 notes; all fixed in `644d419`.
- Fix-only re-review: adopted.
- Open Nit (not fixed; no further cycle): `load_for_invalidation()` reports `quarantined=False` on a quarantined store,
  so a caller that ignores its docstring could misread the flag. `load()`, the only entry point for reuse, is
  unaffected.

**Corpus of record on `644d419`.**

- 18 of 18 model runs valid.
- 2 result-tool calls rejected and corrected by the runner.
- V3 38/39 (the failing row is described above), enterprise identity 13/13, caller-scope 3/3.
- Single run per group.
- The final head is unchanged, so the earlier heads' passes (`fa3dfa4` 39/39, `67908c0` 39/39) are context only; they
  do not validate `644d419`.

**Jev.** 7 of 8 calls in this phase.

- Cycle-2 case selection: Jev raised scrutiny on two cases, and both were added as tests; it also exposed the
  role-versus-ownership wording gap.
- One real rejected-key fallback check.
- No gate was waived or lowered.

**Accepted limitations added.**

- A store that cannot be parsed cannot name a contradicted record; the review's notes carry the finding and whoever
  repairs the store must re-validate it.
- A leftover marker lock makes a doubly failing invalidation raise, which is loud.
- XSS, SSRF and open redirect get no unseen-caller presumption (a result of the narrow class rule).
- The open Nit above.

**Next.** A release needs a pre-registered replication protocol for the corpus. Two examples:
- repeated runs, with every run required to pass;
- a per-case consistency check that rejects answers whose evidence cites another case's file.

It then needs a fresh final validation on this head. That is a separate decision.

## 10. Final pre-registered validation (2026-09-25)

Authorized as one final attempt on product commit `644d419`, with no product change and no further fix or review cycle.

- **Run:** 4 model runs, all valid (2 classification, 2 review); 0 rejected tool calls; 0 binding failures; kit tree
  `98995885…` (the same export as the fix-cycle-2 run); Jev not called.
- **RV-01:** PASS.
- **RV-02:** FAILED. The runner reported one CONFIRMED MEDIUM finding, CWE-306 missing authentication exposing e-mail
  addresses, on the safe SQL fixture. Its evidence cites only that case's file and lines. It did not report SQL
  injection; it reported a different weakness that the fixture's expected result does not list.
- **What this shows:** isolated, case-bound review removes the answer-shifting seen before. It also shows that on a
  bare snippet the kit can confirm a weakness outside a fixture's intended scope (here, an unauthenticated route),
  which the corpus counts as a false CONFIRMED on a safe case.
- **What it does not show:** whether that finding is "wrong", since the route really has no authentication check in
  the snippet; how the other 50 cases would have scored; or run-to-run stability.
- **Next:** whichever of these you choose would need a new, separately authorized decision:
  - decide whether a corpus safe case may carry out-of-scope findings (grade only the fixture's target weakness), or
    whether the fixture needs its missing context;
  - or change the kit's severity/confirmation behaviour for out-of-scope observations;
  - then re-validate.

  None of that was done here.

## 11. Final validation, protocol revision 2 (2026-09-25)

- **Protocol:** revision 2 (`868ef5d`), committed before any run. The tree validated was `ef8a9e4`: product code
  identical to `644d419` and kit export `98995885…`. The corpus was `v4-release-corpus/1`, manifest `08cc741c…`.
- **Runs:** 8 model runs, all valid; 0 rejected tool calls; 0 binding failures; Jev not called.
- **Results:**
  - RV-01: PASS.
  - RV-02 (catalog fixture): PASS, NOT_CONFIRMED.
  - RV-03 (`command_injection_unsafe.js`): PASS.
  - RV-04 (`command_injection_safe.js`): FAILED. The answer was valid, bound to its own file and lines, and
    evidence-backed: CWE-88 argument injection into ImageMagick `convert` through an unvalidated request value.
- **Stop rule:** per the stop rule and rule 10, the finding is reported as a real, evidence-backed observation about
  the fixture as written. It is not dismissed, and neither the fixture nor its expected result was changed.
- **What this shows (together with revision 1):** at least two V3 "safe" fixtures (`sql_injection_safe.py` and
  `command_injection_safe.js`) contain real weaknesses outside the single property each was written to test, and an
  isolated, case-bound V4 review reports them. The remaining safe fixtures were not reached, so there may be more.
- **Next (needs a new authorization):** a pass over every safe corpus fixture, before any further validation, to find
  and correct such incidental weaknesses; for this fixture, for example, an allow-listed file name. Then a single new
  validation attempt.

## 12. Safe-fixture audit and final validation, protocol revision 3 (2026-09-25)

**Audit (no model run).** All 24 expected-safe cases were read on their code: 18 rows of the corpus and 6 rows of the
enterprise-identity set. The results, reasons and replacement fixtures are in `tests/validation/v4-release-corpus.md`.

- **Replaced**, for the V4 release corpus only; V3 fixtures and results unchanged:

  | Row | Incidental weakness in the V3 fixture |
  |---|---|
  | RV-02 | CWE-306, users' e-mail addresses |
  | RV-04 | CWE-88, ImageMagick option and coder injection |
  | RV-13 | a login issuing a session without credentials |
  | RV-20 | a login that verifies nothing |
  | RV-22 | a DNS-rebinding gap and an unbounded response body |
  | RV-24 | unauthenticated access to user uploads |
  | RV-35 | an unauthenticated user search returning e-mail addresses |
  | RV-37 | unauthenticated report download |

- **Kept:** RV-06, RV-07, RV-11, RV-15, RV-17, RV-26, RV-28, RV-31, RV-33, RV-39, and the 6 enterprise-identity rows.
- **Jev:** one call, the phase's last (8 of 8). It raised scrutiny on 7 kept cases, including RV-15; after
  re-inspection none was changed.
- **Deterministic checks:** `tools/context_manifest/tests/test_release_corpus.py`, 15 tests. Its key assertions fail
  against the original V3 fixtures.

**Validation.**

- **Pins:** tree `53ef539` (product code identical to `644d419`), kit export `98995885…`, manifest `cd6f8e96…`.
- **Runs:** 30 model runs, all valid; 2 result-tool calls were rejected and then corrected by the runner; 0 binding
  failures.
- **Outcomes:**
  - RV-01–RV-14: PASS. The replaced RV-02, RV-04 and RV-13 each came back NOT_CONFIRMED.
  - RV-15: FAILED. The answer is quoted above, and its evidence cites only its own file and lines.
- **Stop rule:** validation stopped at RV-15. No run was repeated or replaced.

**What this shows.**

- The V3 corpus's "safe" snippets repeatedly contain weaknesses that sit outside the property each was written to
  test. An isolated, case-bound V4 review reports them. A code-reading audit caught 8 of them, but not RV-15, where a
  missing guard is implied rather than visible.
- The replaced fixtures reached so far behaved as intended.

**What it does not show.**

- how the remaining 37 cases would have scored;
- run-to-run stability (one run per case);
- whether any other kept case has a similar issue.

**Next (needs a new authorization).** Either of these would require it:
- a stricter fixture standard for "safe" (every entry point self-contained, with an explicit and visible guard or an
  explicitly public purpose), applied to every remaining safe case;
- or a decision on how the corpus should treat findings about controls a snippet does not show.

Either would be followed by a new validation. None of it was started here.

## 13. Strict safe-fixture audit and final validation, protocol revision 4 (2026-09-25)

**Audit (no model run, no Jev call).** Every expected-safe case (18 corpus rows, 6 enterprise-identity rows) was
checked for its entry points, data sources, outputs, sensitive data and access control. Controls outside the case
(middleware, session setup, proxy) were not assumed to exist. The per-case checklist is
`work/v4-release/safe-fixture-audit.md`.

- **Safe as they were:** 18 (RV-02, 06, 07, 11, 13, 17, 20, 22, 31, 33, 35, 39 and the 6 enterprise-identity rows).
- **Needed context, made verifiable in a V4-release fixture:** 6 cases, in corpus `v4-release-corpus/3`, 11 replaced
  rows. V3 fixtures and results unchanged:

  | Row | What the V4-release fixture now contains |
  |---|---|
  | RV-04 | a concurrency bound (429) and a 1 kB body limit around the argument-array `execFile` |
  | RV-15 | session middleware with a required 32+ character secret, cookie flags, a `requireSignedIn` guard, and a single non-sensitive route |
  | RV-24, RV-26, RV-37 | a reparse-point (link) check on the file and on every ancestor directory up to the base |
  | RV-28 | a required secret key, cookie flags, a size limit, a sign-in decorator, and a per-user directory with a file cap |

- **Deterministic checks:** `tools/context_manifest/tests/test_release_corpus.py`, 20 tests. The `/3` assertions fail
  against the superseded fixtures.

**Validation.**

- **Pre-registered:** protocol revision 4 (`cedcf19`), committed before any model run. It adds rule 5a: a
  NEEDS_VERIFICATION on a safe case must name the missing control or evidence, checked by a stated mechanical proxy.
- **Pins:** tree `4e4e626`, kit export `98995885…`, manifest `10133e15…`, adapter `d3acdd90…`.
- **Runs:** 58 model runs, all valid; 0 rejected result-tool calls; 0 binding failures; `claude-sonnet-5`, effort
  `high` on every run.
- **Outcomes:**
  - RV-01–RV-28: PASS.
  - Replaced rows: NOT_CONFIRMED except RV-04, RV-13 and RV-26, which were NEEDS_VERIFICATION. Each of those names its
    missing evidence, as rule 5a requires. For example, RV-04 says no authentication is visible and the file only
    exports the app.
  - RV-29: FAILED. The upload -> stored-XSS finding is NEEDS_VERIFICATION, not CONFIRMED. Both path traversals are
    CONFIRMED.
- **Stop rule:** validation stopped at RV-29. No run was repeated or replaced.

**What this shows.**

- The strict audit's replacements behaved as intended on every replaced row reached: none drew a CONFIRMED finding.
- The stop is on the other side of the same question: an **unsafe** V3 fixture whose exploitability depends on a
  control outside the case, here static-file serving of `wwwroot`. The fixture asserts that control in comments only.
- A kit review that follows `plays/finding-validation.md` and refuses to assume unshown middleware can give exactly
  this answer.

**What it does not show.**

- how RV-30 to RV-39 and the 13 enterprise-identity cases would have scored;
- run-to-run stability (one run per case);
- whether the kit's own guidance should confirm stored XSS for an upload under `wwwroot` without the hosting code
  (`plays/file-security.md` covers uploads under "a directory the app serves statically (e.g. ASP.NET Core wwwroot/
  via StaticFiles ...)", but does not say whether that serving must be visible in the reviewed code). That is a
  product question, not decided here.

**Next (needs a new authorization).** Either of these would require it:
- applying the same "contains what it depends on" standard to the **unsafe** fixtures, starting with RV-29 (e.g. a
  V4-release variant that includes `UseStaticFiles()`);
- or deciding that the kit should confirm upload -> stored XSS under `wwwroot` without seeing the hosting code, and
  changing the product guidance accordingly.

Either would be followed by a new validation. None of it was started here.

## 14. RV-29 correction and final validation, protocol revision 5 (2026-09-25)

**Starting state (checked before any change).**
- `v4-release` HEAD `526fef5`, clean working tree.
- Local `v3-slim` and the golden-baseline tag both at `f5502cd`.
- `origin/v3-slim` was force-updated to `39a7b0b`, a rewritten, unrelated history: no common ancestor with
  `f5502cd`, authorship changed. By the user's decision the release base stays the local tag. The remote is handled
  separately; no push or history change was made.

**RV-29 correction (`d67a81c`).**
- **Fixture:** `tests/fixtures/v4_release/upload_static_hosted_program_deceptive.cs`, a single-file ASP.NET Core
  `Program.cs`. `UploadStorage.Directory` is both the upload destination and the `PhysicalFileProvider` that
  `app.UseStaticFiles` publishes at `/uploads`.
- **Checked by running it:** built with .NET 8 (0 warnings, 0 errors) and run on localhost:
  - an uploaded `x.html` is served as `text/html` with no `Content-Disposition`;
  - the upload file name `../../escaped.txt` is written outside the directory;
  - `/download?name=../../...` reads outside it.
- **Manifest `/4`:** only RV-29 differs from `/3`. Its `expectedFindings` are:
  - upload-write traversal (bound to the `Upload` action);
  - download-read traversal (bound to the `Download` action);
  - stored XSS (bound to both the `UseStaticFiles` block and the `Upload` action, as a separate entry).
- **Deterministic tests:**
  - release repo: `test_release_corpus.py`; its RV-29 hosting tests fail 4 of 5 against the V3 fixture, which has no
    hosting code;
  - external adapter: 33 synthetic tests, including one where the revision-4 RV-29 answer still fails;
  - adapter mutants (binding, groups, span cap, `id` type, `rowId`, `replaces.rowId`) are all killed.

**Review.**
- **One independent review:** no Blocker or Major.
  - Fixed: `expectedFindings` ids must be strings; every row's `rowId` / `replaces.rowId` is cross-checked against
    the V3 mapping.
  - Recorded: the keyword-proxy limits.
  - The fixture was reordered, with no change in meaning, so that the hosting block and the `Upload` action fit
    one citation of at most 30 lines. The grader was not loosened.
- **Fix-only re-review:** READY. One residual Minor was recorded and not fixed, per the bounded cycle: a replaced
  row's own `rowId` is not checked for uniqueness; the pinned manifest has 39 distinct values.
- **Reviewer doubt 2, not acted on:** the RV-28 quota check is not atomic, and hard links are not detected in
  RV-24/26/37. Those were safe fixtures outside this batch, so they were left unchanged.

**Validation (protocol revision 5, `298fb31`).**
- **Pins:** tree `d67a81c` (product code identical to `644d419`), kit export `98995885…`, manifest `8ba55ec4…`,
  adapter `5e9c3432…`, all confirmed at initialisation.
- **Runs:** 56 model runs, all valid; 5 result-tool calls rejected and then corrected by the runner; 0 binding
  failures; `claude-sonnet-5`, effort `high`.
- **Outcomes:**
  - RV-01–RV-27: PASS.
  - RV-28: FAILED. CONFIRMED MEDIUM, race condition (TOCTOU) upload-quota bypass, evidence `case_25.py:55-62`. The
    code shows the check-then-write with no lock.
- **Stop rule:** validation stopped at RV-28. No run was repeated or replaced, and no further repair cycle was
  started.

**What this shows.**
- The same failure mode again, on a different axis. A safe fixture carried a control — the upload quota — whose
  implementation is itself a weakness a strict review can confirm.
- The revision-4 run passed this fixture; this one did not. That is run-to-run variation on a borderline finding with
  bounded impact.

**What it does not show.**
- how RV-29, with the corrected fixture, and the remaining cases would score under a model review;
- run-to-run stability.

**Next (needs a new authorization).**
- Make the RV-28 quota atomic, or remove the quota claim. The candidates are a per-user lock, or an atomic
  reservation such as a counter file opened with `O_EXCL` per slot.
- Make the link checks in RV-24/26/37 cover hard links, or state them as out of the tested property with the matching
  control.

Either would be followed by a new validation. None of it was started here.
