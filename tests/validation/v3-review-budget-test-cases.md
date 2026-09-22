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

## What this document does not validate

No step in `skills/security-review/SKILL.md`'s workflow, or in
`AGENTS.md`'s "Before implementing a meaningful software change"
routing, currently instructs *computing* this level and applying it to
scope a review automatically — see `plays/review-budget.md`'s own
"Output" section for this open item. These cases validate the
play's own stated logic (given a change description, what budget
would it call for), not an end-to-end automatic invocation that does
not exist yet.
