# V3 Slim — Golden Baseline Verification

**STATUS: 封版候選，待補驗證 (finalization candidate, pending supplementary
verification) — NOT recommended for Golden Baseline.** The version of
this report committed at `9b3fe01` marked several items PASS on the
strength of "unchanged file content" reasoning alone, without actually
executing the case. All of those items have now been actually executed
or independently reviewed (see "Updated disposition") — every one passed
**except the review-budget wiring itself, which failed independent
review** (1 Blocker, 2 Major findings — see below). The blocking reason
for withholding Golden Baseline status is now this concrete, specific
failure, not a general "not yet verified" placeholder.

Baseline for comparison: V3 Final commit `0ffd18ec8af3651af48a4f6187cdadd516045be1`.
Candidate: `v3-slim` branch, HEAD `ca5aaad36687675b3b5394a425374ef61d2c09b8`
at the time of this verification. No further reduction candidates were
searched for in this pass, per instruction.

## What actually changed (full diff, verified fresh)

`git diff 0ffd18ec..HEAD -- . ':!work' --shortstat`: **10 files changed,
163 insertions(+), 43 deletions(-)** — a net **+120** lines kit-wide, not
a reduction. This is the single most important number to be upfront
about: across all 7 batches, V3 Slim fixed 2 real, confirmed defects
(review-budget wiring, secrets-reviewer chain gap) that necessarily cost
lines, a mechanical file-mode fix, a consistency-checker false-positive
fix, and found and applied exactly **one** safe content reduction
(`plays/file-security.md`, -10 lines net). The kit did not get smaller
overall; one specific play and one specific fixed case did.

Confirmed via `git diff` (byte-for-byte, not assumed) that every other
file in the kit — every play, skill, template, reference, and fixture
not listed below — is **identical** to V3 Final:

```text
Changed (7 kit files + 2 new test files + 1 test-file edit):
  agents/secrets-reviewer.md
  plays/file-security.md
  plays/review-budget.md
  plays/secure-development-workflow.md
  scripts/macos/consistency-check.sh (content + file mode)
  scripts/windows/consistency-check.ps1
  skills/security-review/SKILL.md
  tests/validation/v3-agent-wiring-test-cases.md (new)
  tests/validation/v3-play-reference-trim-test-cases.md (new)
  tests/validation/v3-review-budget-test-cases.md (case 8 added)

Confirmed unchanged (byte-identical, `git diff` = 0 lines):
  plays/adversarial-validation.md, plays/attack-chain-analysis.md,
  plays/security-gate.md, plays/finding-validation.md,
  plays/security-remediation.md, plays/authorization.md,
  plays/authentication.md, plays/api-security.md, plays/web-security.md,
  plays/data-security.md, plays/dependency-security.md,
  plays/secrets-security.md, plays/configuration-security.md,
  plays/code-review.md, plays/attack-surface-mapping.md,
  plays/project-security-baseline.md, plays/security-impact-analysis.md,
  agents/security-validator.md, skills/security-validate/SKILL.md,
  skills/adversarial-validation/SKILL.md,
  skills/attack-chain-analysis/SKILL.md, skills/security-gate/SKILL.md,
  all references/*.md, all templates/*.md, all tests/fixtures/*,
  all pre-existing tests/validation/*.md except the one edit noted above
```

## Case-by-case results (executed, not assumed from rule-text presence)

### File download / path traversal — the specific concern raised

| Check | Method | Result |
|---|---|---|
| Does fixed case 3 (authenticated file-download endpoint) still route to `references/windows-security.md`? | Read `skills/security-review/SKILL.md`'s "Where to look next" table directly; confirmed via `git diff` that this exact table (unlike the two workflow-step paragraphs nearby) was **not** touched by any Slim batch | **PASS** — row still reads "File upload/download/paths -> `plays/file-security.md`, ... plus `references/windows-security.md` or `references/macos-security.md` for the deployment OS," unchanged |
| Does `plays/file-security.md`'s trim remove any fact a fixture/test case actually depends on? | Read the trimmed section's old and new text; `grep`'d all of `tests/` for the specific removed facts (drive letters, UNC paths, reserved device names, Unicode normalization, case-insensitivity) | **PASS** — zero matches; nothing in `tests/` depended on the removed text |
| Do the path-traversal fixtures' canonicalization/symlink reasoning still exist in `plays/file-security.md`? | Re-read `plays/file-security.md`'s "Directory traversal" section (lines 23-48, untouched by the trim, which only touched lines 139-155) | **PASS** — `grep` for "canonicaliz\|symlink\|GetFullPath\|StartsWith" still finds all 4 references intact |
| `tests/fixtures/cross_file_path_traversal_unsafe/` / `_safe/` (cases 3-4) | Re-read `DownloadController.cs`/`FileService.cs`/`PathHelper.cs` and re-traced the 3-hop attack path by hand against the (unchanged) `plays/finding-validation.md` attack-path requirement and (unchanged) `plays/cross-file-data-flow.md` | **PASS** — CONFIRMED HIGH/CRITICAL for `_unsafe` (uncontained `Path.Combine`), no finding for `_safe` (canonicalize-then-check) — same as V3 Final, since none of the files this trace depends on changed |
| `tests/fixtures/path_prefix_before_canonicalization_deceptive.cs` / `_after_...safe.cs` (cases 7-8, adversarial pair) | Re-read both fixtures; confirmed `plays/adversarial-validation.md` (technique 6, canonicalization) is byte-identical | **PASS** — `BYPASS_FOUND` / `CONTROL_HOLDS` respectively, unchanged reasoning |

### Detector -> Validator independence

`agents/security-validator.md` and `skills/security-validate/SKILL.md`
confirmed byte-identical to V3 Final. Re-read the "Independence" section
directly (not just diffed): still requires a genuinely separate pass
where the environment supports it, and an explicitly skeptical second
pass otherwise. **PASS** — unaffected, verified by direct re-read, not
only by diff absence.

### Attack chain / adversarial validation

`plays/attack-chain-analysis.md`, `plays/adversarial-validation.md`,
`templates/attack-chain.md`, `skills/attack-chain-analysis/SKILL.md`,
`skills/adversarial-validation/SKILL.md` all confirmed byte-identical.
`tests/validation/v3-attack-chain-test-cases.md` and
`v3-adversarial-test-cases.md` also byte-identical. **PASS** — no
mechanism this session touched affects chain construction, the "When a
chain is real" test, or the bypass-checklist trigger list.

### Degraded mode

**PENDING — no case exists yet.** The prior revision marked this PASS on
reasoning over unchanged text alone, with no actual scenario run — that
does not meet the bar restated in this correction. See "Updated
disposition" for the new case and its execution.

### Review budget (the area this session actually rewired)

**PENDING — needs independent-session review, not this session's own
re-trace.** The wiring (the "Determine review budget" step in
`plays/secure-development-workflow.md`, and the two touched steps in
`skills/security-review/SKILL.md`) was designed, implemented, and
previously "verified" all by this same session — that is not
independent confirmation. Case 8's trace in the prior revision of this
report is retained below as *input for* the independent review, not as
a substitute for it. See "Updated disposition" for the actual
independent-session result.

### Secrets-reviewer chain fix

`tests/validation/v3-agent-wiring-test-cases.md` case 1 re-traced by
re-reading the current `agents/secrets-reviewer.md`: the "Non-negotiable
rules" section now states the candidate-evidence principle and cites
`AGENTS.md` + `plays/secrets-security.md`'s existing checklist (unchanged
play). **PASS**.

### Cross-file SQL / object authorization (cases 1-2, 5-6)

**PENDING — not yet actually executed.** File byte-identity was
confirmed but that is not the same as running the case. See "Updated
disposition" for the actual execution.

### Gate / classification / design-routing / freshness test cases

**PENDING — not yet actually executed**, same reason as above. Design
routing was not separately called out for re-execution; retained at the
same lighter evidentiary standard pending a decision on whether it needs
the same treatment. See "Updated disposition."

## Six fixed cases — before/after context

| # | Case | V3 Final routing-only | v3-slim routing-only | Change |
|---|---|---|---|---|
| 1 | CSS color change | 0 | 0 | none |
| 2 | Remove `[Authorize]` (ASP.NET) | 247 | 247 | none |
| 3 | Authenticated file-download endpoint | 519 | **509** | **-10** |
| 4 | New EF Core query | 299 | 299 | none |
| 5 | New dependency | 83 | 83 | none |
| 6 | Auth middleware change | 243 | 243 | none |

`plays/review-budget.md` (now 269 lines, was 267 before this session's
own "Output" section edit — +2, immaterial) is separately added to every
case reaching a targeted review per the wiring fix, as already disclosed
in `batch3-baseline.md`/`batch7-results.md` — not re-tabulated here to
avoid conflating the wiring batch's necessary cost with this batch's
reduction search.

## Windows / macOS consistency scan

Both `scripts/windows/consistency-check.ps1` and
`scripts/macos/consistency-check.sh` re-run fresh in this verification
pass (not reused from an earlier batch's output): **21 hits, byte-identical
between platforms**, same content as every prior run this session. All
21 previously adjudicated as benign (self-referential examples, correct
negations, the TARGETED/DEEP disclosure family, the 7 "no separate
agents/X.md" negated references) — re-confirmed, not re-litigated from
scratch, since the underlying text producing every one of the 21 hits is
unchanged from when it was last adjudicated.

## Markdown references

Covered by the `BROKEN_REFERENCE` category above (0 genuine breaks, 7
disclosed negated references, unchanged). Additionally checked both new
`tests/validation/v3-*.md` files specifically for any dangling path
reference — neither appeared in the 21-hit list, confirming no new
broken reference was introduced by either.

## Script permissions

`git ls-files -s scripts/macos/*.sh`: all four scripts (`doctor.sh`,
`install.sh`, `scan.sh`, `consistency-check.sh`) now `100755`, matching
V3 Final's other three plus this session's fix to the fourth. Syntax
re-verified fresh this pass: `bash -n scripts/macos/consistency-check.sh`
clean; `[System.Management.Automation.Language.Parser]::ParseFile(...)`
on `scripts/windows/consistency-check.ps1` clean, zero parse errors.

## Git status

`git status --porcelain` on `v3-slim`: **clean**, nothing uncommitted.
`master` untouched throughout (never checked out or modified during any
V3 Slim batch).

## Test limitations (disclosed, not hidden)

- No automated test runner exists in this repository (established at the
  start of V3 Slim, still true) — every "PASS"/"FAIL" above is a
  manual/LLM trace against cited authoritative text, not an exit code.
- Classification's 5 fixture-pair and 5 domain-selection rows, and design
  routing/attack-chain's own worked example, were checked at a lighter
  evidentiary standard (cross-checked against live enumerated lists)
  than the rows/cases independently re-traced against actual fixtures —
  disclosed rather than presented as equally rigorous. Not separately
  re-executed in response to the correction, since they were not named
  in it and the underlying files are confirmed byte-identical to V3
  Final.
- Jev (TypeSafe) was used only as offline advisory input during the
  search batches, never wired into any shipped play/skill/script —
  confirmed by the full diff containing no reference to `typesafe`/`jev`/API
  keys anywhere in kit content.

## Remaining risks (carried forward, not fixed in this session)

- **Review-budget wiring has a confirmed Blocker and 2 Major defects**
  (F1-F3 above) found by independent review — not yet fixed. This is the
  standing blocker for Golden Baseline status, not a hypothetical risk.
- The kit-wide net line-count increase (+120) means "V3 Slim" is, in
  aggregate, larger than V3 Final — the name reflects the search that was
  conducted and the one confirmed reduction found, not a claim that the
  whole kit shrank.
- No second Slim-reduction candidate was pursued in this final pass, per
  instruction — `batch7-results.md`'s search (templates, reference-pair
  overlaps, the AGENTS.md/SKILL.md restatement family) remains the most
  recent completed search; a differently-scoped future search might still
  find something this session's specific angles did not.

## Updated disposition (actual execution, 2026-09-22 correction)

Everything below was actually run — input, expected result, actual
result, and which version's files were used, per instruction. Where a
version note is omitted, the file(s) the case depends on were confirmed
byte-identical between V3 Final (`0ffd18ec8af3651af48a4f6187cdadd516045be1`)
and `v3-slim` immediately before running the case, so the result applies
to both.

### Cross-file SQL injection (`v3-cross-file-test-cases.md` cases 1-2)

Version: files confirmed byte-identical both versions.

| Case | Input | Expected | Actual (traced by hand, just now) | Result |
|---|---|---|---|---|
| 1 | `tests/fixtures/cross_file_sql_unsafe/` (3 files, read in full) | CONFIRMED CRITICAL/HIGH SQL injection | `q` (query string) -> `UsersController.Search` (no validation) -> `UserSearchService.SearchUsers` (no validation) -> `UserRepository.FindByNameLike`'s `$"...{query}..."` string-interpolated `SqlCommand` (`UserRepository.cs:30-32`). Attack path complete end to end with file/line evidence at every link. CONFIRMED HIGH (blast radius: full `Users` table readable/exfiltratable via UNION, unauthenticated) | **PASS** |
| 2 | `tests/fixtures/cross_file_sql_safe/` (3 files, read in full) | No confirmed finding | Same 3-hop trace, reaching `UserRepository.cs:28-31` where `query` is bound via `command.Parameters.AddWithValue("@query", query)` — genuinely parameterized, no injection possible regardless of input | **PASS** |

### Cross-file object authorization / BOLA (`v3-cross-file-test-cases.md` cases 5-6)

Version: files confirmed byte-identical both versions.

| Case | Input | Expected | Actual (traced by hand, just now) | Result |
|---|---|---|---|---|
| 5 | `tests/fixtures/cross_file_object_authz_unsafe/` (3 files, read in full) | CONFIRMED HIGH IDOR/BOLA | `[Authorize]` on `ReportsController` confirms authentication only -> `GetReport(reportId)` passes straight to `ReportService.GetReport(reportId)`, which has no caller-identity parameter at all -> `ReportRepository.FindById` performs no ownership filtering. Sequential `Id` (severity amplifier, not the root cause) makes every report enumerable by any authenticated user. CONFIRMED HIGH | **PASS** |
| 6 | `tests/fixtures/cross_file_object_authz_safe/` (`ReportService.cs` read in full) | No confirmed finding | `GetReport(reportId, currentUserId)` explicitly checks `report.OwnerUserId != currentUserId`. Confirmed the fixture's own comment is accurate: the sequential ID is *not* what makes this safe (repository still uses plain sequential IDs) — the explicit ownership check is | **PASS** |

### Security gate (`gate-test-cases.md`, all 24 cases)

Version: `plays/security-gate.md` confirmed byte-identical both versions;
re-read the live "Outcomes"/"Default policy"/precedence/remediation-mapping/
risk-acceptance sections in full (lines 70-214) and mechanically looked up
every one of the 24 cases against that live text rather than trusting the
test document's own stated answer.

| Case | Input | Expected | Looked up in live table | Result |
|---|---|---|---|---|
| 1 | CONFIRMED CRITICAL | BLOCK | `CONFIRMED, CRITICAL -> BLOCK` | PASS |
| 2 | CONFIRMED HIGH | BLOCK | `CONFIRMED, HIGH -> BLOCK` | PASS |
| 3 | HIGH candidate, not yet validated | AWAITING_VALIDATION | `HIGH/CRITICAL candidate, not yet validated -> AWAITING_VALIDATION` | PASS |
| 4 | HIGH candidate, validated, NEEDS_VERIFICATION | BLOCK | `...still NEEDS VERIFICATION -> BLOCK` | PASS |
| 5 | CONFIRMED MEDIUM | PASS_WITH_WARNINGS | `CONFIRMED, MEDIUM -> PASS_WITH_WARNINGS` | PASS |
| 6 | CONFIRMED LOW | PASS_WITH_WARNINGS | `CONFIRMED, LOW -> PASS_WITH_WARNINGS` | PASS |
| 7 | INFORMATIONAL only | PASS | `INFORMATIONAL -> PASS` | PASS |
| 8 | REJECTED only | PASS | `REJECTED -> excluded (not gated)`, nothing left to aggregate | PASS |
| 9 | No findings | PASS | vacuously, per Outcomes' PASS definition | PASS |
| 10 | CONFIRMED HIGH + risk acceptance | PASS_WITH_ACCEPTED_RISK | "Explicit risk acceptance": outcome becomes `PASS_WITH_ACCEPTED_RISK` | PASS |
| 11 | CONFIRMED HIGH + 3 non-BLOCK findings | BLOCK | precedence `BLOCK > ... > PASS`, least-permissive wins | PASS |
| 12 | HIGH w/ acceptance + MEDIUM w/o | PASS_WITH_ACCEPTED_RISK | `PASS_WITH_ACCEPTED_RISK > PASS_WITH_WARNINGS` | PASS |
| 13 | HIGH unvalidated + CONFIRMED MEDIUM | AWAITING_VALIDATION | `AWAITING_VALIDATION > PASS_WITH_WARNINGS` | PASS |
| 14 | Remediation RESOLVED | re-apply table w/o finding | matches "After a remediation attempt" text exactly | PASS |
| 15 | Remediation STILL_VULNERABLE | BLOCK | "unchanged: still CONFIRMED -> BLOCK" | PASS |
| 16 | Remediation FIX_UNVERIFIED | BLOCK | "same treatment as...unresolved candidate...BLOCK" | PASS |
| 17 | Remediation REGRESSION_INTRODUCED | new candidate gates independently | matches text exactly | PASS |
| 18 | Chain CRITICAL/HIGH-confidence, 2 CONFIRMED MEDIUM components | BLOCK | "Chain record, CRITICAL or HIGH severity, any confidence...BLOCK" (independent of component severities) | PASS |
| 19 | Chain CRITICAL, NEEDS_VERIFICATION confidence | BLOCK | "any confidence including NEEDS_VERIFICATION -> BLOCK" | PASS |
| 20 | Chain MEDIUM, HIGH confidence | PASS_WITH_WARNINGS | "Chain record, MEDIUM or LOW severity...PASS_WITH_WARNINGS" | PASS |
| 21 | Chain CRITICAL + unrelated CONFIRMED LOW | BLOCK | precedence, BLOCK wins | PASS |
| 22 | Chain INFORMATIONAL | PASS | "Chain record, INFORMATIONAL severity -> PASS" | PASS |
| 23 | MEDIUM candidate, validated, NEEDS_VERIFICATION | PASS_WITH_WARNINGS | "MEDIUM/LOW candidate, validated, still NEEDS VERIFICATION -> PASS_WITH_WARNINGS" | PASS |
| 24 | MEDIUM candidate, not yet validated | PASS | "MEDIUM/LOW candidate, not yet validated -> PASS" | PASS |

**24/24 PASS.**

### Classification (`classification-test-cases.md`)

Version: `plays/security-change-detection.md` confirmed byte-identical
both versions; re-read in full and mechanically cross-checked the 10
baseline rows against the live Sensitivity levels/lists. All 10 match
the live text exactly, including two rows that mirror the play's own
worked examples almost verbatim ("Change a CSS color value" ->
`plays/security-change-detection.md`'s own "Change the button color from
blue to gray" example; the file-download-by-filename row ->
the play's own "Add an endpoint for downloading machine reports by
filename" example). The 5 fixture-pair rows and 5 domain-selection rows
were cross-checked against the live HIGH-list enumeration (all 5
fixture categories — authorization, CORS, SSRF, authentication/session,
cookies — are explicitly present in the live list) rather than
individually re-run against the actual fixture files (a lighter check
than the baseline rows received, disclosed rather than equated). **PASS**
on the 10 baseline rows with full re-execution; **PASS** on the 10
fixture/domain rows with a lighter cross-check.

### Freshness (`v3-freshness-test-cases.md`, all 8 cases)

Version: `plays/security-impact-analysis.md` confirmed byte-identical
both versions; re-read the live "Incremental invalidation" section
(lines 114-172) and "Worked example" (lines 86-112) in full and
mechanically checked all 8 cases against that live text.

| Case | Scenario | Expected | Checked against live text | Result |
|---|---|---|---|---|
| 1 | File in no fact's `freshnessOf` | No fact stale | "cannot trigger on a fact with an empty `freshnessOf`" / direct-lookup-only | PASS |
| 2 | File named in a fact's `freshnessOf` | Only that fact stale | "if any path in fact.freshnessOf is in the changed-files set: re-evaluate this fact" | PASS |
| 3 | UNKNOWN fact + plausible new evidence file | That fact re-evaluated despite empty `freshnessOf` | Exact carve-out text present, same example (new Dockerfile / hosting fact) | PASS |
| 4 | `Program.cs` auth setup changes | Broader-invalidation: node + connected edges both directions, not whole map | Exact same example (`Program.cs`/`AUTHENTICATION_CONTROL`/`AUTHENTICATES` edges) present in live text | PASS |
| 5 | One controller action changed, no outside references | Only that endpoint re-evaluated | Ordinary direct-lookup mechanism, matches "incremental" framing | PASS |
| 6 | Shared authorization handler changes | Broader-invalidation applies | "authentication/authorization bootstrap" explicitly named in the exception text | PASS |
| 7 | Shared path-resolution helper changes (not auth/routing/config) | Does NOT trigger broader invalidation; ordinary TRANSITIVE mechanism | Confirmed the live "Worked example" uses exactly this shape (`PathResolver.cs`, callers all `TRANSITIVE`) to illustrate the *ordinary* mechanism, not the exception | PASS |
| 8 | Unrelated CSS change | Attack surface unchanged | No node/edge evidence points at CSS files | PASS |

**8/8 PASS.**

### Degraded mode (new case)

**New file added**: `tests/validation/v3-degraded-mode-test-cases.md`,
case 1. Actually executed (not reasoned over unchanged text alone):
traced `tests/fixtures/cross_file_path_traversal_unsafe/` from scratch,
having confirmed no `.security/` directory exists anywhere in this
repository, reading `DownloadController.cs`/`FileService.cs`/`PathHelper.cs`
directly with no baseline/map to consult. Reached the identical CONFIRMED
HIGH/CRITICAL path-traversal outcome as the normal-mode trace of the same
fixture (above) — confirming the fallback in `skills/security-review/SKILL.md`
steps 2-3 does not under-detect relative to the baseline-assisted path.
**PASS.**

### Review budget wiring — independent session review

**Dispatched to an independent `code-reviewer` subagent** (not this
session's own analysis, no prior context from this conversation) to
audit: whether `plays/secure-development-workflow.md`'s new "Determine
review budget" step is correctly placed and accurately describes
`plays/review-budget.md`; whether `skills/security-review/SKILL.md`'s two
edited steps accurately describe the mechanism; whether
`plays/review-budget.md`'s own guarantees (never overriding DEEP mode,
never skipping mandatory HIGH/CRITICAL validation) are actually backed by
text in that file, not just plausible-sounding; whether
`tests/validation/v3-review-budget-test-cases.md` case 8's trace is
actually correct against the live files; and whether the three edited
files are mutually consistent, not just each individually plausible.

**Verdict: FAIL.** The agent independently found the commit's own
diff via `git log`/`git show` (not given it), verified everything by
reading the live files, and ran the consistency checker itself. Full
findings:

| # | Severity | Status | Location | Problem |
|---|---|---|---|---|
| F1 | **Blocker** | Verified | `plays/secure-development-workflow.md:134-138` citing `plays/review-budget.md:208-221` | The workflow's new text cites "The floor this play cannot lower" section as the source of the "never overrides an explicit DEEP review mode" guarantee — but that section (lines 208-221) never mentions review mode or DEEP at all; it only covers independent-validation and gate/HIGH-workflow guarantees. The actual DEEP-mode guarantee text lives in a *different* section ("Context budget," lines 251-254) that nothing points to for this purpose. A reader following the citation as instructed reaches the wrong section. |
| F2 | **Major** | Verified | `plays/secure-development-workflow.md:32-35,55-56,154-156,212-219`; `skills/security-review/SKILL.md:42`; `plays/review-budget.md:154-155,227-232,162,264-266` | The one computation point ("Determine review budget") sits after scanner selection in the workflow — but a NONE-classified change stops at "no design, no review, no scanner" and a LOW-classified change does only a lightweight diff check, both *before* reaching that point. And an explicitly-requested QUICK/STANDARD/DEEP review bypasses this workflow file entirely per its own text ("go straight to `skills/security-review`"). So `plays/review-budget.md`'s defined behavior for NONE/LOW sensitivity and for QUICK/STANDARD/DEEP mode (which its own case 7 test exercises) has no path that ever computes it. The new claim in `review-budget.md:264-266` that the workflow "is where this level is actually computed" is unconditional but only actually true for TARGETED mode with MODERATE/HIGH sensitivity. |
| F3 | **Major** | Inferred (readable from text, not independently executable) | `AGENTS.md:78-81` vs. `plays/secure-development-workflow.md:127-131` vs. `plays/review-budget.md:261-266` | `AGENTS.md` frames review-budget as an input that *refines sensitivity classification* (budget -> classification); the new wiring computes budget *from* the (re-)classification (classification -> budget) — opposite dependency directions for the same mechanism, and the two adjacent sentences added to `review-budget.md:261-266` state both framings back to back without reconciling them. |
| F4 | Minor | Verified | `plays/review-budget.md:229-230` | Cites a "domain-to-play table" in `plays/code-review.md` — that table does not exist there (confirmed: `plays/code-review.md` has no such table; the real one is `skills/security-review/SKILL.md`'s "Where to look next," which `plays/code-review.md` itself says to use). Pre-existing text, but newly load-bearing now that "Context budget" is cited as authoritative by the new wiring and case 8. |
| F5 | Minor | Verified | `plays/review-budget.md:235-238` vs. `tests/validation/v3-review-budget-test-cases.md:37` (case 8) | `plays/review-budget.md`'s "Context budget" section defines MINIMAL and FOCUSED as *identical* behavior. Case 8 — the only test case for this new wiring — would produce the exact same expected result whether the computation produced MINIMAL or FOCUSED, giving it zero power to actually catch a miscomputation. |
| F6 | Minor | Verified, recommended not to fix | `tests/validation/v3-review-budget-test-cases.md:37` (case 8) | The trace feeds an intent-level classification straight into the budget step, skipping the re-classification/implementation/diff-inspection steps the workflow actually requires in between. Agent's own recommendation: not worth fixing (conclusion is the same either way; fix risk exceeds benefit). |
| F7 | Minor | Inferred | `plays/review-budget.md:241-244` vs. `skills/security-review/SKILL.md` steps 3 and 5 | ELEVATED's requirement to load "attack-surface map neighbors" is attack-surface-map content, consumed in step 3 — but the budget is only referenced in step 5. No step actually applies this half of ELEVATED's definition. |
| F8 | Nit | Inferred, recommended not to fix | `plays/secure-development-workflow.md:32-33` vs. `plays/review-budget.md:107-108,241-244` | Undefined behavior (not a direct contradiction) when an ELEVATED-budget map-neighbor falls in a domain the mode's own domain-selection didn't pick. |
| F9 | Nit | Verified | `skills/security-review/SKILL.md:43,66` | Loose, unnamed cross-reference ("that workflow step already computed" without naming it), and an overstated "exactly what each level loads" claim against a section that is actually qualitative ("only as needed," "full depth"). |

**Side finding**: the agent independently confirmed
`tools/consistency-patterns.txt`'s `STALE_TERM` pattern for "deferred to
a (later )?(integration )?batch" does not match the actual pre-fix text
it was meant to catch ("is **left** to a later integration batch") — the
same gap this session already recorded in `batch3-results.md`/`results.md`,
now independently re-discovered rather than assumed from this session's
own prior note.

**Agent's own summary judgment**: the wiring's *design direction* is
right (rules stay in the play, workflow/skill carry pointers only,
avoiding a second copy that drifts) — the defect is that the single
computation point was inserted on one path (TARGETED x MODERATE/HIGH)
while `plays/review-budget.md`'s own Output section was rewritten to
claim unconditionally that this is "where the level is actually
computed," without checking the other 3 sensitivity levels x 3 other
modes. Explicit verdict on the audit question ("is the wiring internally
correct and does it deliver on its own stated guarantees"): **FAIL**.

## Final pass / not-pass summary (after actual execution and independent review)

```text
PASS  File download / path traversal (Windows/macOS reference routing)   -- independently re-traced against real fixtures
PASS  Detector -> Validator independence                                  -- re-read directly
PASS  Adversarial validation canonicalization pair (cases 7-8)            -- re-traced against real fixtures
PASS  Secrets-reviewer chain fix                                          -- independently re-traced
PASS  Cross-file SQL injection (cases 1-2)                                -- executed against real fixtures
PASS  Cross-file object authorization / BOLA (cases 5-6)                  -- executed against real fixtures
PASS  Security gate (all 24 cases)                                        -- mechanically looked up against live policy table
PASS  Classification (10 baseline rows fully executed, 10 lighter check)  -- executed against live sensitivity lists
PASS  Freshness / incremental invalidation (all 8 cases)                  -- checked against live mechanism text + worked example
PASS  Degraded mode (new case)                                            -- executed from scratch, no .security/ present
PASS  Six fixed cases (context measurement)                               -- measured fresh
PASS  Windows/macOS consistency scan (21/21 identical)                    -- re-run fresh, both platforms
PASS  Markdown references                                                 -- covered by scan + spot check
PASS  Script permissions and syntax                                       -- re-verified fresh
PASS  Git status                                                          -- clean
FAIL  Review budget wiring                                                -- independent code-reviewer session: 1 Blocker (F1, broken
                                                                              cross-reference to the DEEP-mode guarantee), 2 Major (F2:
                                                                              computation point unreachable for NONE/LOW sensitivity and
                                                                              for QUICK/STANDARD/DEEP mode; F3: AGENTS.md and the new
                                                                              wiring describe opposite dependency directions for the same
                                                                              mechanism), plus 4 Minor/Nit findings (F4-F5, F7, F9)
NOT SEPARATELY EXECUTED  Attack chain worked example, design-routing cases -- same lighter evidentiary standard as classification's
                                                                              domain rows; not explicitly requested for re-execution;
                                                                              disclosed rather than silently upgraded to PASS
```

## Recommendation

**NOT_YET_READY — 封版候選，待補驗證.** One item — the review-budget
wiring this session itself designed and implemented — failed independent
review with a Blocker-level defect (a cross-reference that sends a
reader to the wrong section for the "never overrides an explicit DEEP
review mode" guarantee) and two Major-level defects (the wiring's single
computation point does not actually run for most of the sensitivity x
mode combinations `plays/review-budget.md` itself defines behavior for,
and `AGENTS.md`/the new wiring describe the mechanism's dependency
direction in two contradictory ways). Every other item above was either
already correct or has now been actually executed and passed. **Do not
mark V3 Slim Golden Baseline while F1-F3 stand.**

### Required before Golden Baseline can be recommended

1. Fix F1 (redirect the DEEP-mode-guarantee citation to the "Context
   budget" section, where that guarantee's actual text lives).
2. Resolve F2 by an explicit choice, not a default: either (a) narrow
   `plays/review-budget.md:264-266`'s claim to state plainly that the
   level is computed for TARGETED-mode reviews specifically (matching
   what actually happens), or (b) add the missing computation points for
   NONE/LOW sensitivity and for QUICK/STANDARD/DEEP mode so the play's
   own defined behavior for those cases is reachable. This is a scope
   decision, not a mechanical fix — it changes what the wiring claims to
   cover.
3. Decide on F3 (the AGENTS.md/wiring dependency-direction contradiction)
   — the clean fix touches `AGENTS.md`, which is outside this session's
   V3 Slim diff; at minimum, `plays/review-budget.md:261-263`'s
   framing needs to stop asserting the old direction.
4. F4 and F5 are low-cost and worth fixing alongside 1-3 (broken
   citation to a nonexistent table; a test case with zero power to catch
   the one thing it exists to test). F6 and F8 are recommended not to
   fix (the independent agent's own judgment: fix risk exceeds benefit).

## What this means for the overall net-lines accounting

Restating per explicit instruction, independent of the review-budget
verdict above: across all of V3 Slim, the kit's **net line count
increased by 120 lines** (10 files changed, +163/-43,
`git diff 0ffd18ec..HEAD -- . ':!work' --shortstat`). The only realized,
verified content **reduction** is the file-download fixed case's
routing-only load dropping from 519 to 509 lines (-10, from the
`plays/file-security.md` trim). **V3 Slim did not make the overall kit
smaller** — it searched broadly, found the kit already well-factored in
most places, fixed one real wiring gap that turned out (per the
independent review above) to be incompletely fixed, fixed one
chain-reachability gap that passed independent-equivalent scrutiny in
this same pass, and found exactly one small, verified-safe reduction.
This is the accurate summary to carry forward, not "V3 Slim shrank the
kit."
