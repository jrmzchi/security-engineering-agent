# V3 Slim — Golden Baseline Verification

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

**No dedicated executable test case exists for this** — flagged as a
pre-existing gap in an earlier session and not fixed in this one (out of
every batch's stated scope). Verified this pass by direct re-read, not
by diff-absence alone: `skills/security-review/SKILL.md` steps 2-3
("Architecture discovery"/"Attack surface identification," both
confirmed untouched by any Slim-batch diff) explicitly say "If
`.security/baseline.json`... already exists... and is fresh, consult it
**instead of rediscovering everything from scratch**" — the fallback
(discovery directly from code when the baseline/map is absent or stale)
is the plain reading of "instead of," not a separate branch that could
have silently broken. **PASS, with a caveat**: this is reasoning over
unchanged text, not an executed scenario against a real repository
missing `.security/` — the same limitation this gap has always had, not
newly introduced.

### Review budget (the area this session actually rewired)

All 8 cases in `tests/validation/v3-review-budget-test-cases.md`
re-checked:

- Cases 1-7: unchanged text, unchanged logic (`plays/review-budget.md`'s
  Factors/Default-starting-point/Context-budget tables were not touched
  by the wiring edit — only its "Output" section was). **PASS**, verified
  by re-reading the play's actual tables, not assumed.
- Case 8 (new, end-to-end): re-traced by hand — `skills/security-change-detection`
  classifies the EF Core case `MODERATE` (unchanged play); the new
  "Determine review budget" step in `plays/secure-development-workflow.md`
  computes `FOCUSED` from `MODERATE`'s default starting point (unchanged
  table, re-read directly); `skills/security-review/SKILL.md`'s Scope
  step now records it and Manual semantic analysis step applies it at
  `FOCUSED` depth (`plays/code-review.md` + `references/dotnet-security.md`
  only, matching case 4's fixed-case loading exactly). **PASS**.

### Secrets-reviewer chain fix

`tests/validation/v3-agent-wiring-test-cases.md` case 1 re-traced by
re-reading the current `agents/secrets-reviewer.md`: the "Non-negotiable
rules" section now states the candidate-evidence principle and cites
`AGENTS.md` + `plays/secrets-security.md`'s existing checklist (unchanged
play). **PASS**.

### Cross-file SQL / object authorization (cases 1-2, 5-6)

Fixtures and the plays they depend on (`plays/code-review.md`,
`plays/authorization.md`, `plays/cross-file-data-flow.md`,
`plays/finding-validation.md`) all confirmed byte-identical. **PASS** by
unchanged-content proof; not individually re-traced by hand in this pass
since none of the changed files this session touches any part of these
specific fixtures' reasoning chain (SQL injection, IDOR/BOLA) — this is
disclosed as a lighter-weight verification than the file-download case
received, not silently equated to it.

### Gate / classification / design-routing / freshness test cases

All confirmed byte-identical (both the plays/skills they validate and
the test-case files themselves). **PASS** by unchanged-content proof.
Not individually re-traced by hand.

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

## Pass / not-pass summary

```text
PASS  File download / path traversal (Windows/macOS reference routing)  -- independently re-traced
PASS  Detector -> Validator independence                                 -- re-read directly
PASS  Attack chain                                                       -- unchanged-content proof
PASS  Adversarial validation (incl. canonicalization pair)               -- re-traced against fixtures
PASS  Degraded mode                                                      -- reasoning over unchanged text (lighter evidence, disclosed)
PASS  Review budget (all 8 cases, incl. new end-to-end case)             -- independently re-traced
PASS  Secrets-reviewer chain fix                                         -- independently re-traced
PASS  Cross-file SQL / object authorization                              -- unchanged-content proof (lighter evidence, disclosed)
PASS  Gate / classification / design-routing / freshness                 -- unchanged-content proof (lighter evidence, disclosed)
PASS  Six fixed cases (context measurement)                              -- measured fresh
PASS  Windows/macOS consistency scan (21/21 identical)                   -- re-run fresh, both platforms
PASS  Markdown references                                                -- covered by scan + spot check
PASS  Script permissions and syntax                                      -- re-verified fresh
PASS  Git status                                                         -- clean
```

**No item failed. No item is unverified in the sense of "not checked at
all."** Several items (degraded mode, cross-file SQL/authz,
gate/classification/freshness) were verified with a lighter evidentiary
standard (unchanged-content proof and/or reasoning) than the areas this
session actually modified (file-security.md, review-budget wiring,
secrets-reviewer chain), which received independent re-tracing. This
distinction is disclosed above per instruction, not smoothed over.

## Recommendation

**READY_FOR_V3_SLIM_GOLDEN_BASELINE**, with the distinction above kept
visible: this is a baseline that fixed 2 real defects, closed 1
consistency-checker gap, corrected 1 file-mode error, and found and
verified exactly 1 safe, measured content reduction (-10 lines,
`plays/file-security.md`) after a genuinely broad search (21/21
`quick-reference.md` rows, multiple SKILL.md-vs-play/AGENTS.md
restatement pairs, all 13 agent wrapper chains, template/reference-pair
overlaps) that mostly came back "this kit is already well-factored,"
which is itself the finding, not a shortfall of the search. The kit's
net size grew, not shrank — the recommendation is not "V3 Slim made the
kit smaller," it is "V3 Slim found and fixed real defects, verified no
regression against everything it touched or could plausibly have
affected, and is not silently claiming untested behavior passed."
