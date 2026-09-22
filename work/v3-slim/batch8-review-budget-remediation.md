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

## Independent review dispatch

See "Independent review verdict" section below — dispatched separately,
result appended once received.
