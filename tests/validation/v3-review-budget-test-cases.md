# V3 Review Budget Test Cases

Validates `plays/review-budget.md`, including its "Applicability
matrix" (which sensitivity/mode combinations actually compute and apply
a budget, and where). See `tests/validation/README.md` for how to run a
validation pass. Uses this kit's actual implemented vocabulary —
`MINIMAL`/`FOCUSED`/`ELEVATED`/`AUDIT` — not an earlier draft's
`TARGETED`/`DEEP`, which `plays/review-budget.md` explains was
deliberately renamed to avoid colliding with the pre-existing review
*mode* names of the same words (see that play's naming-collision
disclosure). Do not "correct" these cases to the draft vocabulary.

These are manual/LLM-traced cases against cited authoritative text, not
an automated test suite — there is no exit code, only a comparison
between the play's stated rules and a case's traced result.

## Level computation (TARGETED path, ordinary development changes)

| # | Change description | Expected budget | Reason |
|---|---|---|---|
| 1 | Change a CSS color value | N/A — no live review | `NONE` sensitivity per `plays/security-change-detection.md` — "no security workflow... do not run a scanner, do not load a play." Per the Applicability matrix, this is not "budget computed as MINIMAL and unused," there is no review to scope at all. |
| 2 | Refactor an internal calculation function, no behavior change | N/A — no live review (unless escalated) | `LOW` sensitivity — only a lightweight diff check runs, not a formal targeted review. Budget applies only if the check surfaces something that re-classifies the change higher first. |
| 3 | Add a new EF Core query for an existing, already-authorized report (comparable to this batch's `cross_file_sql_safe/` shape, minus the vulnerability) | `FOCUSED` | `MODERATE` sensitivity (database-query change) -> `plays/review-budget.md`'s Default starting point table. No Factor moves it up or down. |
| 4 | Add an authenticated endpoint that downloads a file by user-supplied filename (comparable to this batch's `cross_file_path_traversal_unsafe/` shape) | `ELEVATED` | `HIGH` sensitivity (file download + user-controlled filesystem path + authorization, per `plays/security-change-detection.md`'s own classification of this exact shape) -> Default starting point `ELEVATED`. |
| 5 | Rewrite the authentication middleware configuration | `AUDIT` | `HIGH` sensitivity -> default `ELEVATED`, then moved up one level by the "Changed attack-surface centrality" Factor (shared authentication middleware is named directly in that Factor's qualitative list) — this is the Factors-driven path to `AUDIT`, distinct from case 11 below's explicit-DEEP-request path to the same level. Per "Move at most one level up or down... per the Factors," `ELEVATED` -> `AUDIT` is exactly one step. |
| 6 | A small, internal endpoint change, but the endpoint's authentication state is `UNKNOWN` in the baseline (per `plays/project-security-baseline.md`'s fact schema) | `ELEVATED` | `plays/review-budget.md`'s own "Examples" section names this exact scenario — genuine uncertainty about the surrounding system, not just the diff's own size, justifies more scrutiny ("Baseline confidence" Factor). |

## Mode-vs-budget non-override cases

| # | Scenario | Expected outcome | Reason |
|---|---|---|---|
| 7 | A `MINIMAL`-budget change (case 1's CSS edit) reviewed under an explicit `DEEP` review mode (e.g. a release audit that happens to touch this file among many others) | The review still loads everything DEEP mode requires for this file — budget never downgrades what mode already committed to loading | `plays/review-budget.md`'s "Context budget" — mode decides domains/loading floor, budget only decides depth within what mode already selected |
| 7b | Same scenario as 7, but checking *activities* specifically, not loading: does the DEEP review still run architecture analysis, threat modeling, a full scanner run, and produce a complete security report for the rest of the repository, or does the low per-file budget skip any of them? | All of DEEP's mandatory activities still run in full | `plays/review-budget.md`'s "The floor this play cannot lower" — the loading guarantee (case 7) and the activity guarantee (this case) are two different claims; this case exists because the independent review that found this wiring's original defect (F1) found the activity guarantee was previously undocumented, not just under-cited |
| 8 | `TARGETED`-mode review of a `HIGH`-sensitivity change that computes `ELEVATED` budget, and the candidate resolves to a HIGH/CRITICAL finding | Independent validation (`skills/security-validate`) still runs in full regardless of the budget level, and the Security Gate still applies its normal policy table | `plays/review-budget.md`'s "The floor this play cannot lower" — `plays/finding-validation.md`'s independent-validation requirement and `plays/security-gate.md`'s outcomes are budget-independent |

## Explicit-mode computation (QUICK/STANDARD/DEEP, no sensitivity input)

| # | Scenario | Expected budget | Computed where | Reason |
|---|---|---|---|---|
| 9 | User explicitly requests "Review this repository using QUICK security review" | `FOCUSED` | `skills/security-review/SKILL.md`'s Scope step, directly (never reaches the workflow's "Determine review budget" step) | No sensitivity signal exists for an explicit request — `plays/review-budget.md`'s "Explicit mode" section defaults `QUICK` to `FOCUSED` |
| 10 | User explicitly requests "Review this repository using STANDARD security review" | `FOCUSED` | Same entry point as case 9 | Same reasoning as case 9 |
| 11 | User explicitly requests "Perform a DEEP security assessment" | `AUDIT` | Same entry point as case 9 | `plays/review-budget.md`'s "Explicit mode" section defaults `DEEP` to `AUDIT` — a no-op cap per "Context budget"'s own AUDIT definition, not a new restriction. Contrast with case 5, which reaches `AUDIT` via the *Factors* path on an ordinary (non-explicit-DEEP) `HIGH`-sensitivity change — two different paths to the same level. |

## End-to-end invocation trace (TARGETED path)

Validates that the wiring actually computes and applies a level for a
live case — not just that the play's own logic is internally correct
(cases 1-6 above) — per `plays/secure-development-workflow.md`'s
"Determine review budget" step and `skills/security-review/SKILL.md`'s
"Scope"/"Attack surface identification"/"Manual semantic analysis"
steps. Split, per correction, into a **level-computation assertion**
and a **separate, conditional loading assertion** — a case that bundles
both into one hard-coded expectation cannot tell "wrong level computed"
apart from "right level, but this specific file wasn't needed."

### Case 12: MODERATE change (paired with case 13 as a level-discrimination pair)

| Step | Expected result |
|---|---|
| (a) Classification | `skills/security-change-detection` classifies the case-3 change (new EF Core query) `MODERATE`, per `tests/validation/classification-test-cases.md`'s matching case |
| (b) Level computed | `plays/secure-development-workflow.md`'s "Determine review budget" step computes `FOCUSED` from `MODERATE`'s Default starting point; no Factor here (no external exposure change, no privilege change, no attack-surface centrality signal) moves it |
| (c) Recorded | `skills/security-review/SKILL.md`'s Scope step records `FOCUSED` alongside `TARGETED` mode |
| (d) Loaded (conditional, not a fixed list) | `plays/code-review.md` (the domain domain-selection already picked) is loaded. `references/dotnet-security.md` is loaded **only if** the manual semantic analysis actually needs a stack-specific detail to resolve a question about this EF Core query (`plays/review-budget.md`'s `MINIMAL`/`FOCUSED` row: "reference material only as needed to resolve a specific question" — not an unconditional load). No full-reference-depth material and no attack-surface-map-neighbor expansion (both `ELEVATED`-only per "Context budget"), and no domain outside what domain selection already picked. |

### Case 13: HIGH change, same trace shape, different observable result (the counter-example F5 required)

| Step | Expected result |
|---|---|
| (a) Classification | The case-4 change (authenticated file-download endpoint) classifies `HIGH` |
| (b) Level computed | `ELEVATED` from `HIGH`'s Default starting point |
| (c) Recorded | `skills/security-review/SKILL.md`'s Scope step records `ELEVATED` alongside `TARGETED` mode |
| (d) Loaded — **observably different from case 12** | Full reference depth for the identified domain(s) (not "only as needed"), **plus** `skills/security-review/SKILL.md`'s Attack surface identification step pulls in directly-connected attack-surface-map neighbors of the changed node, if `.security/attack-surface.json` exists |

**Why 12 and 13 are a pair, not two independent cases**: if a wiring bug
computed `ELEVATED` for the case-12 change, or `FOCUSED` for the
case-13 change, the resulting loaded material would visibly differ from
what's specified above (map-neighbor pull happens or doesn't; full vs.
conditional reference depth) — unlike the prior version of this
end-to-end case (which asserted the same unconditional
`references/dotnet-security.md` load regardless of `MINIMAL` or
`FOCUSED`, giving it no power to catch either being computed instead of
the other, since `plays/review-budget.md`'s "Context budget" section
defines `MINIMAL` and `FOCUSED` identically). This pair does not
resolve that identical-definition characteristic of `MINIMAL`/`FOCUSED`
themselves (out of this batch's scope — a review-budget.md level-design
question, not a wiring-reachability one); it works around it by pairing
a `FOCUSED` case against an `ELEVATED` one, which do differ observably.

### Case 14: ELEVATED with an attack-surface-map neighbor outside the selected domain

| Step | Expected result |
|---|---|
| Setup | A `HIGH`-sensitivity change to an authentication middleware component computes `ELEVATED` (per case 5's shape). `.security/attack-surface.json` exists and shows a directly-connected neighbor node that belongs to a domain (e.g. a file-storage `SERVICE` node) domain selection did **not** pick for this change (domain selection picked only `authentication`). |
| Expected | The neighbor is neither silently loaded (would violate "budget never expands the domain set") nor silently dropped (would lose a real structural signal) — it is flagged for the domain-selection step to reconsider, per `plays/review-budget.md`'s updated "Context budget" ELEVATED row and `skills/security-review/SKILL.md`'s step 3 |

## NONE/LOW sensitivity — explicitly confirming "no live review" is not silently treated as MINIMAL

| # | Scenario | Expected | Reason |
|---|---|---|---|
| 15 | Ordinary `NONE`-classified change (case 1's CSS edit) proceeds through the full proactive workflow | No step ever reaches "Determine review budget" — the workflow already stops at classification | Confirms the Applicability matrix's NONE/TARGETED cell is genuinely unreachable, not merely undocumented |
| 16 | Ordinary `LOW`-classified change (case 2's refactor) proceeds through the workflow, and the lightweight diff check finds nothing suspicious | Same as case 15 — no budget computation occurs | Confirms the LOW/TARGETED cell's "unless escalated" branch does not fire when nothing actually escalates it |

## What this document validates and does not

Validates: `plays/review-budget.md`'s own level-computation logic
(cases 1-6), the non-override floor over both loading (case 7) and
activities (case 7b) and over independent validation/gate (case 8), the
explicit-mode computation path (cases 9-11), the end-to-end wiring for
the TARGETED path with a genuine level-discriminating pair (cases
12-13), the ELEVATED cross-domain-neighbor handling (case 14), and that
NONE/LOW genuinely never reach a computation (cases 15-16).

Does not validate: `plays/review-budget.md`'s own design choice to
define `MINIMAL` and `FOCUSED` identically in "Context budget" (a
level-design question, not a wiring-reachability one, out of this
batch's scope) — cases 12/13 route around this by using a
`FOCUSED`/`ELEVATED` pair instead.
