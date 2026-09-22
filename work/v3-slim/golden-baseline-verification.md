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
