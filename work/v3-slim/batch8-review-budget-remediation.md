# V3 Slim Batch 8 — Review-budget wiring remediation (F1-F5, F7)

Scope: close F1-F5 and F7 from the independent review's findings
(`golden-baseline-verification.md`, commit `a2cca0a`). Not a reduction
batch — this closes real defects in previously-wired functionality. No
new Slim-reduction candidates were searched for.

## Applicability matrix (Step 1, final)

See `plays/review-budget.md`'s new "Applicability matrix" section
(authoritative — not restated here). Summary of the design decision:
sensitivity (NONE/LOW/MODERATE/HIGH) and explicitly-requested mode
(QUICK/STANDARD/DEEP) never actually combine in this kit's mechanism —
sensitivity is only computed by the proactive workflow, and an explicit
mode request bypasses that workflow entirely (confirmed via
`plays/code-review.md`'s `TARGETED` note and
`plays/secure-development-workflow.md`'s "This does not replace explicit
workflows" section, both unchanged, re-read fresh for this batch). Of
16 nominal cells, only 2 are live computation points (MODERATE/TARGETED
-> FOCUSED, HIGH/TARGETED -> ELEVATED); NONE/LOW-TARGETED have no live
review to scope (narrowed the play's own claim rather than inventing a
computation point, per instruction); the 3 explicit modes compute
directly at `skills/security-review/SKILL.md`'s Scope step since they
never reach the workflow's computation step at all.

## Jev-assisted analysis (offline advisory only — see reasoning/decision for each)

Full log: session scratchpad `v3slim-budget-fix/jev-log.md` (not copied
into the repo — working material, not a kit deliverable, consistent
with `work/` being excluded from the consistency scanner per an earlier
batch's fix).

| Call | Question | Jev output | Decision |
|---|---|---|---|
| 1 | Does the draft applicability matrix leave any authoritative-text applicability claim unaddressed for a cell marked N/A? | "no_unreachable_claim_found," confidence 0.09 (55/45 split) — inconclusive | Human check: the Default starting point table's NONE/LOW rows read as unconditional-looking, but the actual overclaim was in the old Output section, already slated for rewrite. Added a clarifying sentence to the Default starting point table anyway (near-zero cost) rather than dismiss the flag outright. |
| 1 | Does keeping the Default-starting-point table's NONE/LOW rows unchanged contradict the matrix's "N/A, no live review" framing? | "no_contradiction," confidence 0.81 | Accepted — matches human reading. |
| 2 | Does the draft new Output/matrix text drift from 3 authoritative excerpts (TARGETED note, NONE/LOW actions, AGENTS.md step wording)? | "consistent," confidence 0.09 (55/45) — inconclusive | Not acted on alone; the more decisive finding was question 2 below. |
| 2 | Does the draft restate computation logic that already lives elsewhere in the same file (Default starting point, Context budget)? | "restates_existing_logic," confidence 0.87 — high confidence | **Accepted.** Found two real instances: verbatim quotes of Context budget's AUDIT definition and Levels' FOCUSED description in the new "Explicit mode" section, and the matrix's cells restating FOCUSED/ELEVATED values the Default starting point table already states. Revised: removed verbatim quotes (replaced with "see X for why"), changed matrix cells to say "REACHABLE — value per Default starting point below" instead of restating the value. |
| 3 | Does the full diff (review-budget.md + SKILL.md + AGENTS.md) weaken any pre-existing safety guarantee? | "no_weakening_found," confidence 0.99 | Accepted as a supporting signal; final confirmation is the independent code-reviewer dispatch below, not this score. |

**Jev was not used to decide PASS/FAIL on any test case** — every case
result in this batch was reached by tracing the live files by hand
(below), matching the instruction that Jev's judgment is an offline
lead, not a substitute for actual verification.

## Changes made

| File | F# closed | What changed |
|---|---|---|
| `plays/review-budget.md` | F1 | Added the DEEP-mode mandatory-*activity* guarantee to "The floor this play cannot lower" (the section `plays/secure-development-workflow.md` already cited for this — the citation was correct, the cited section was missing the content; fixed the content, not the pointer) |
| `plays/review-budget.md` | F2 | Replaced the unconditional "workflow diagram is where this is computed" claim with the Applicability matrix + a new "Explicit mode" section giving QUICK/STANDARD/DEEP their own reachable computation point at `skills/security-review/SKILL.md`'s Scope step |
| `AGENTS.md` | F3 | Removed `plays/review-budget.md` from step 1's "refines classification" parenthetical (that direction was backwards); added it to step 6 as the thing *computed from* step 5's classification |
| `plays/review-budget.md` | F3 | "Output" section now states the same (classification -> budget) direction as `AGENTS.md`'s corrected step 6, instead of the old two-sentences-in-opposite-directions text |
| `plays/review-budget.md` | F4 | Fixed the QUICK/STANDARD domain-table citation from the nonexistent `plays/code-review.md` table to the actual `skills/security-review/SKILL.md` "Where to look next" table |
| `tests/validation/v3-review-budget-test-cases.md` | F5 | Split case 8 into a level-computation assertion (case 12) and a conditional loading assertion, paired with a new case 13 (HIGH/ELEVATED) that is *observably different* from case 12 — a wrong level or wrong entry point would now visibly change what's expected to load |
| `plays/review-budget.md`, `skills/security-review/SKILL.md` | F7 | ELEVATED's attack-surface-map-neighbor requirement now lands at `SKILL.md` step 3 (where map data is actually read), with an explicit decision for a neighbor outside the selected domain: flag for domain-selection reconsideration, neither silently load nor silently drop |

F6 and F8 were not changed, matching the independent reviewer's own
recommendation (fix risk exceeds benefit for both — F6 is a test-trace
precision issue with no effect on the conclusion; F8 is genuinely
undefined behavior needing a new decision rule, not a defect in what
already exists). F9 (loose pointer wording, overstated "exactly") is
addressed incidentally: the SKILL.md step 1 rewrite for F2 replaced the
loose "that workflow step already computed" phrasing, and the "exactly
what each level loads" overstatement was not touched (Context budget's
levels remain qualitative by design, per this batch's own case
12/13 loading assertions treating them as such).

## Diff

`git diff --stat` (working tree, this batch only):

```text
 AGENTS.md                                       |   8 +-
 plays/review-budget.md                          | 162 ++++++++++++++++++++----
 skills/security-review/SKILL.md                 |  21 ++-
 tests/validation/v3-review-budget-test-cases.md | 136 +++++++++++++++-----
 4 files changed, 261 insertions(+), 66 deletions(-)
```

## Case-by-case execution (all 17, including 7b)

Traced by hand against the files as they now stand (not assumed from
design intent). Version: `v3-slim` working tree, this batch's edits.

| # | Input | Expected | Actual (traced) | Result |
|---|---|---|---|---|
| 1 | CSS color change | N/A, no live review | NONE sensitivity -> "no security workflow... do not run a scanner, do not load a play" (`plays/security-change-detection.md`, unchanged) -> matrix's NONE/TARGETED cell confirms no live review | PASS |
| 2 | Internal refactor, no behavior change | N/A unless escalated | LOW sensitivity -> lightweight diff check only, nothing suspicious surfaces -> no live review | PASS |
| 3 | New EF Core query, already-authorized | FOCUSED | MODERATE sensitivity -> Default starting point FOCUSED, no Factor adjusts it | PASS |
| 4 | Authenticated file-download endpoint | ELEVATED | HIGH sensitivity -> Default starting point ELEVATED | PASS |
| 5 | Auth middleware rewrite | AUDIT | HIGH -> ELEVATED default -> "Changed attack-surface centrality" Factor (shared auth middleware explicitly named) moves it up one level -> AUDIT | PASS |
| 6 | Small endpoint, UNKNOWN auth state in baseline | ELEVATED | Matches the play's own "Examples" section verbatim | PASS |
| 7 | MINIMAL budget under explicit DEEP mode | Gets everything DEEP requires (loading) | "Context budget" guarantee, unchanged in substance | PASS |
| 7b | Same, checking activities not loading | All DEEP activities still run | New "The floor this play cannot lower" text explicitly states this — this is the direct closure of F1's missing guarantee | PASS |
| 8 | TARGETED HIGH->ELEVATED, candidate resolves HIGH/CRITICAL | Independent validation + gate unaffected by budget | "The floor this play cannot lower" — validation/gate guarantees, unchanged in substance | PASS |
| 9 | Explicit QUICK review request | FOCUSED, computed at SKILL.md Scope | New "Explicit mode" section + SKILL.md step 1 edit, both consistent | PASS |
| 10 | Explicit STANDARD review request | FOCUSED, same entry point | Same as case 9 | PASS |
| 11 | Explicit DEEP review request | AUDIT, computed at SKILL.md Scope | New "Explicit mode" section; distinct path from case 5's Factors-driven AUDIT, no contradiction | PASS |
| 12 | MODERATE end-to-end (level assertion + conditional loading) | FOCUSED computed; `plays/code-review.md` loaded, `references/dotnet-security.md` only if needed | Traced through `plays/secure-development-workflow.md`'s existing "Determine review budget" step (unchanged this batch, still correctly cites the now-fixed "Default starting point" table) -> `SKILL.md` Scope records it -> conditional loading per Context budget's MINIMAL/FOCUSED row | PASS |
| 13 | HIGH end-to-end, observably different from case 12 | ELEVATED computed; full reference depth + map neighbors pulled at step 3 | Same trace shape, different (and correctly different) result — confirms F5's discrimination requirement | PASS |
| 14 | ELEVATED with a map neighbor outside the selected domain | Flagged for domain-selection reconsideration, neither silently loaded nor dropped | Matches new Context budget ELEVATED row + SKILL.md step 3 edit; analogy to `plays/security-impact-analysis.md`'s `POTENTIAL` classification confirmed accurate by re-reading that play's own worked example (`BackgroundExportJob -> POTENTIAL`, unchanged) | PASS |
| 15 | NONE through the full proactive workflow | Never reaches the budget step | `plays/secure-development-workflow.md`'s Proportionality table (unchanged): "NONE -> stop here" | PASS |
| 16 | LOW through the workflow, nothing suspicious | Never reaches the budget step | Same table: "LOW -> lightweight diff check only" | PASS |

**17/17 PASS.**

## Consistency scan

Ran both `scripts/windows/consistency-check.ps1` and
`scripts/macos/consistency-check.sh` after these edits: **23 hits** (up
from the prior 21). All 3 new hits adjudicated:

| New hit | Text | Disposition |
|---|---|---|
| `skills/security-review/SKILL.md:43` | "...(`plays/review-budget.md`) here — for a TARGETED review, record the..." | False positive — "TARGETED" names the review mode correctly; "budget" is a separate noun referring to the play. This is the kit's own established, deliberate coexistence of mode and budget in the same sentence, the same family already adjudicated benign for every prior TARGETED/DEEP+budget hit this session. |
| `tests/validation/v3-review-budget-test-cases.md:22` | "...not a formal targeted review. Budget applies only if..." | Same family — correct, non-colliding usage. |
| `tests/validation/v3-review-budget-test-cases.md:33` | Case 7b's row, discussing DEEP mode and budget as explicitly distinct axes | Same family — this row's entire point is explaining the two are different, which is exactly what the pattern's own disclosure carve-out anticipates. |

No hit was resolved by changing correct content — consistent with this
session's standing rule not to "fix" a false positive by editing away
accurate text.

## Git / hygiene

- `git status --porcelain`: 4 files modified (`AGENTS.md`,
  `plays/review-budget.md`, `skills/security-review/SKILL.md`,
  `tests/validation/v3-review-budget-test-cases.md`), no untracked
  files besides this batch's own `work/v3-slim/` additions.
- No script touched this batch — permissions/syntax unaffected,
  previously verified state stands.
- Markdown references: covered by the consistency scan's
  `BROKEN_REFERENCE` category (unchanged, still the 7 disclosed negated
  references).

## Independent review verdict (commit `bd51424`)

Dispatched to a fresh `code-reviewer` subagent with no prior context
from this session. It located the fix commit itself via `git log`/`git
show` (confirmed `bd51424`, confirmed it was HEAD, confirmed working
tree clean) and read every downstream file it cited independently —
`plays/code-review.md`, `plays/security-change-detection.md`,
`plays/secure-development-workflow.md`, `plays/project-security-baseline.md`,
`plays/security-impact-analysis.md`, `skills/security-change-detection/SKILL.md`,
`tests/validation/classification-test-cases.md`,
`tools/consistency-patterns.txt` — rather than trusting the commit
message or the prior independent review's summary.

**F1–F5, F7: all six CLOSED**, each with exact quotes and line numbers
confirming the fix text actually exists and says what it needs to say
(full quotes in the reviewer's own report, not reproduced here in full).
Independently confirmed via its own `bash scripts/macos/consistency-check.sh`
run (23 hits, matching this commit's own claim) and its own re-play of
the `STALE_TERM`/`VOCABULARY` patterns against the before/after commits
(9 -> 11 hits in the 4 changed files specifically, net +2 — it caught
that this batch's own report had mis-added 21+3=23 instead of accounting
for one old hit that stopped matching, a bookkeeping slip in the report
text, not in the fix itself).

**New findings from the fix batch itself** (none Blocker or Major):

| # | Severity | Finding |
|---|---|---|
| N1 | Minor | The new "Explicit mode" section's DEEP->AUDIT citation pointed to "Renamed from the naming..." (lines 20-47), which never mentions `AUDIT` at all — the same defect *shape* as F1/F4 (citation correct in form, wrong in target), newly introduced in the same commit that fixed F1/F4. |
| N2 | Minor | The Applicability matrix's MODERATE/HIGH cells said budget is "applied at Scope and Manual semantic analysis steps" — omitting `skills/security-review/SKILL.md` step 3, even though this same commit moved ELEVATED's map-neighbor consumption there. Three files (matrix, Context budget, the test file) disagreed on how many steps consume budget. |
| N3 | Minor | The "move at most one level up or down" cap made the `MINIMAL`-budget-under-explicit-`DEEP` scenario (case 7/7b, and the play's own naming-collision worked example at lines 41-44) *unreachable* under the new Explicit-mode design, since `DEEP`'s fixed default (`AUDIT`) is 3 levels above `MINIMAL` and the cap only allows 1. |
| N4 | Minor | "The floor this play cannot lower" claimed budget affects "how much material is loaded" for `DEEP`; "Context budget" separately claimed budget "never overrides what mode already committed to loading, in either direction" — directly opposed claims on the same axis, papered over by an activities-vs-loading split that the floor section's own wording didn't actually maintain. |
| N5 | Minor | "Default starting point"'s new clarifying note said a `LOW` check that escalates mid-review applies the `LOW` row's own value; the Applicability matrix said escalation re-classifies to a *new, higher* row first. Two different algorithms for the same scenario, one section each, no case covering the escalation branch either way. |
| N6 | Minor | The matrix's "invoked exclusively"/"never actually combine" wording is disproven by `skills/security-change-detection`'s own independent entry points (its own `SKILL.md` "When to use," a directly-callable Claude subagent wrapper, a direct Codex `README.md` reference) — an absolutist claim a future maintainer would likely trust and be wrong to. |
| N11 | Minor | "Flag it for the domain-selection step to evaluate" named no step that exists anywhere in this kit by that name, and specified no landing point for the flag — non-silent in wording only, not actually operable or checkable. |
| N7-N10 | Nit | Loose pointer wording, a scope gap for QUICK/STANDARD's own loading floor, a duplicate-word typo, and a bookkeeping slip in this batch's own working notes (the 21->23 hit-count arithmetic) — reviewer's own recommendation: not worth fixing (N7, N8, N10) or trivial to fix in passing (N9, the typo). |

**Reviewer's own summary**: no Blocker, no safety guarantee actually
narrowed (the direction was net-expansion — the floor section gained the
DEEP-activity guarantee, nothing lost precision) — but 4 of the 6 new
Minors (N2, N3, N5, N6) are products of the same "two/three/four
documents describing one cross-cutting mechanism" structure the fix
batch was built on, not simple typos. Its explicit, disclosed
recommendation, **not acted on unilaterally**: consider consolidating
review-budget's now-two parallel computation entry points (the
workflow's step, and `SKILL.md`'s Scope-step "Explicit mode" path) into
a single owning node, so reachability has only one place it can be read
from — this is a real architectural option worth the user's judgment,
not something this session decided on its own.

## Remediation of the independent review's new findings (commit `8a64a7c`)

Fixed N1, N2, N3+N4 (merged — same root scenario), N5, N6, N9 (typo),
N11. Left N7, N8, N10 as-is, matching the reviewer's own "not worth
fixing" assessment. **Self-verified by re-tracing all 17 test cases
against the updated live text** (case 5's Factors-capped path and case
7/7b's now-reachable uncapped explicit-mode path were both re-checked
specifically, since N3's fix touches exactly that boundary) — **not**
independently re-reviewed by a third fresh agent, since none of N1-N11
were Blocker/Major and the instruction's mandatory-re-review trigger is
specifically for those. This is disclosed as a narrower evidentiary
standard than F1-F5/F7 received (two independent passes each), not
presented as equivalent.

Consistency scan re-run after this second fix (both platforms): still
23 hits, no new hit, no hit lost.
