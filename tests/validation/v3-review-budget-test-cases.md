# V3 Review Budget Test Cases

Validates `plays/review-budget.md`. See `tests/validation/README.md`
for how to run a validation pass. Uses this kit's actual implemented
vocabulary — `MINIMAL`/`FOCUSED`/`ELEVATED`/`AUDIT` — not an earlier
draft's `TARGETED`/`DEEP`, which `plays/review-budget.md` explains was
deliberately renamed to avoid colliding with the pre-existing review
*mode* names of the same words (see that play's naming-collision
disclosure). Do not "correct" these cases to the draft vocabulary.

| # | Change description | Expected budget | Reason |
|---|---|---|---|
| 1 | Change a CSS color value | `MINIMAL` | No security-relevant surface touched at all |
| 2 | Refactor an internal calculation function, no behavior change | `MINIMAL` | Ordinary internal logic — see `plays/review-budget.md`'s default sensitivity-to-budget mapping |
| 3 | Add a new EF Core query for an existing, already-authorized report (comparable to this batch's `cross_file_sql_safe/` shape, minus the vulnerability) | `FOCUSED` | Database-query change — proportionate scrutiny on the query construction, not a full-repository pass |
| 4 | Add an authenticated endpoint that downloads a file by user-supplied filename (comparable to this batch's `cross_file_path_traversal_unsafe/` shape) | `ELEVATED` | File download + user-controlled filesystem path + authorization — multiple HIGH-sensitivity signals in one change, per `plays/security-change-detection.md`'s own classification of this exact shape |
| 5 | Rewrite the authentication middleware configuration | `AUDIT` | Foundational, broad-blast-radius change — "whatever DEEP review mode already requires loading" per `plays/review-budget.md`'s `AUDIT` level definition |
| 6 | A small, internal endpoint change, but the endpoint's authentication state is `UNKNOWN` in the baseline (per `plays/project-security-baseline.md`'s fact schema) | `ELEVATED` | `plays/review-budget.md`'s own "Examples" section names this exact scenario — genuine uncertainty about the surrounding system, not just the diff's own size, justifies more scrutiny. This is a `plays/review-budget.md`-only factor (its "Baseline confidence" section); it is a deliberate, disclosed, safe reuse of a *name* some of `plays/finding-validation.md`'s severity factors also use, not the same factor list applied twice — see that play's note that the two lists answer different questions for different objects and should not be merged |

## Mode-vs-budget interaction case

| # | Scenario | Expected outcome | Reason |
|---|---|---|---|
| 7 | A `MINIMAL`-budget change (case 1's CSS edit) reviewed under an explicit DEEP review mode (e.g. a release audit that happens to touch this file among many others) | The review still gets everything DEEP mode requires for this file — budget never downgrades what mode already committed to loading | `plays/review-budget.md`'s "A `MINIMAL`-budget change under `DEEP` review mode... still gets everything DEEP mode requires" — mode decides domains, budget only decides depth within what mode already selected, never the reverse |

## End-to-end invocation case

Validates that the workflow actually computes and applies this level —
not just that the play's own logic is internally correct (cases 1–7
above) — per the wiring added to `plays/secure-development-workflow.md`'s
workflow diagram (the "Determine review budget" step, between scanner
selection and targeted review) and `skills/security-review/SKILL.md`'s
"Scope" and "Manual semantic analysis" steps.

| # | Trace | Expected result at each step |
|---|---|---|
| 8 | Same change as case 3 (new EF Core query for an existing, already-authorized report) | (a) `skills/security-change-detection` classifies `MODERATE` (per `tests/validation/classification-test-cases.md`'s matching case). (b) `plays/secure-development-workflow.md`'s new "Determine review budget" step computes `plays/review-budget.md`'s level from that classification: `MODERATE` sensitivity's "Default starting point" is `FOCUSED`, and none of the Factors here (no external exposure change, no privilege change, no new attack-surface centrality) move it up or down — result: `FOCUSED`. (c) `skills/security-review/SKILL.md`'s "Scope" step records `FOCUSED` alongside the `TARGETED` mode. (d) "Manual semantic analysis" loads at `FOCUSED` depth per `plays/review-budget.md`'s "Context budget": `plays/code-review.md` (the domain already selected) + `references/dotnet-security.md` only — no full-reference-depth material and no attack-surface-neighbor expansion (those are `ELEVATED`-only), and no domain outside what domain selection already picked (budget never expands the domain set). |

This does not re-test the non-override guarantees — case 7 above and
`plays/review-budget.md`'s "The floor this play cannot lower" already
cover those at the play level; this case only checks that the new
wiring actually reaches the play and applies its result, for one
concrete change.
