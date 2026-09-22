# V3 Slim — Golden Baseline Verification

**STATUS: 封版候選，待補驗證 (finalization candidate, pending supplementary
verification) — NOT yet recommended for Golden Baseline.** The version
of this report committed at `9b3fe01` marked several items PASS on the
strength of "unchanged file content" reasoning alone, without actually
executing the case. Per explicit correction (2026-09-22), those items are
downgraded to PENDING below until independently re-verified or actually
executed. Do not read anything below as final until the "Updated
disposition" section (added in this revision) is complete for every item.

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
  start of V3 Slim, still true) — every "PASS" above is a manual/LLM
  trace against cited authoritative text, not an exit code.
- Degraded mode has no dedicated executable case — verified by reasoning
  over unchanged text, a lighter form of evidence than the file-download
  case (which was independently re-traced against real fixtures).
- Cross-file SQL/object-authorization and gate/classification/freshness
  cases were verified by unchanged-content proof (byte-identical diff)
  rather than independently re-traced by hand in this pass — a
  legitimate but lighter-weight form of verification than what the
  file-download and review-budget cases received, disclosed here rather
  than presented as equally rigorous.
- Jev (TypeSafe) was used only as offline advisory input during the
  search batches, never wired into any shipped play/skill/script —
  confirmed by the full diff above containing no reference to
  `typesafe`/`jev`/API keys anywhere in kit content.

## Remaining risks (carried forward, not fixed in this session)

- `review-budget`'s newly-wired computation step has not been
  independently re-validated by a second reviewer/session — it was
  designed, implemented, and verified by the same session that wired it.
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
session's own analysis) to audit: whether `plays/secure-development-workflow.md`'s
new "Determine review budget" step is correctly placed and accurately
describes `plays/review-budget.md`; whether `skills/security-review/SKILL.md`'s
two edited steps accurately describe the mechanism; whether
`plays/review-budget.md`'s own guarantees (never overriding DEEP mode,
never skipping mandatory HIGH/CRITICAL validation) are actually backed by
text in that file, not just plausible-sounding; whether
`tests/validation/v3-review-budget-test-cases.md` case 8's trace is
actually correct against the live files; and whether the three edited
files are mutually consistent, not just each individually plausible.
**Result: [pending — agent still running at the time this section was
last edited; do not read a result here until this placeholder is
replaced with an actual verdict].**

## Pass / not-pass summary (superseded by "Updated disposition" below)

```text
PASS     File download / path traversal (Windows/macOS reference routing)  -- independently re-traced against real fixtures
PASS     Detector -> Validator independence                                 -- re-read directly
PENDING  Attack chain                                                       -- was unchanged-content proof only; not separately called out by the correction but same weakness, flagged here rather than left silently mismarked
PASS     Adversarial validation canonicalization pair (cases 7-8)           -- re-traced against real fixtures
PENDING  Degraded mode                                                      -- no case existed; see Updated disposition
PENDING  Review budget (all 8 cases, incl. new end-to-end case)             -- needs independent-session review, not this session's own re-trace
PASS     Secrets-reviewer chain fix                                         -- independently re-traced
PENDING  Cross-file SQL / object authorization                              -- not yet actually executed
PENDING  Gate / classification / design-routing / freshness                 -- not yet actually executed
PASS     Six fixed cases (context measurement)                              -- measured fresh
PASS     Windows/macOS consistency scan (21/21 identical)                   -- re-run fresh, both platforms
PASS     Markdown references                                                -- covered by scan + spot check
PASS     Script permissions and syntax                                      -- re-verified fresh
PASS     Git status                                                         -- clean
```

## Recommendation

**NOT_YET_READY — 封版候選，待補驗證.** Several items above were
previously marked PASS on the strength of "the underlying file didn't
change" alone, which is not the same as executing the case — corrected
per explicit instruction (2026-09-22). No Golden Baseline recommendation
until every PENDING item above is either actually executed (with input,
expected result, actual result recorded) or independently reviewed,
whichever the item requires. See "Updated disposition" below for the
completed portion of that work in this same revision.
