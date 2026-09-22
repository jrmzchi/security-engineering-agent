# V3 Slim Batch 3 — Baseline: security-review's Skill -> Play -> Reference loading

Scope: only `skills/security-review/SKILL.md`'s routing (its own "Attack
path model"/"Where to look next" content, plus
`skills/security-review/references/quick-reference.md`) and the
plays/references it sends a reviewer to for the same 6 fixed cases used
in earlier batches. Measured against the current `v3-slim` branch state
(commit `e620df0`, i.e. after the file-mode fix and the review-budget
wiring already committed) — not the original V3 Full commit, since this
batch's job is to find further reduction from where the kit actually
stands now.

`skills/security-review/SKILL.md` itself is now 163 lines (was 156 at V3
Full — +7 from the review-budget wiring sentences added in the prior
batch). `quick-reference.md` is unchanged at 21 data rows.

**Note, not in scope for this batch's candidate search:** every case below
that reaches a targeted review now also loads `plays/review-budget.md`
(267 lines) per the wiring committed in the previous batch — that cost is
a known, deliberate consequence of fixing that gap, not something this
batch is looking to reduce. Case totals below are reported both
including and excluding it, so this batch's own findings aren't
conflated with the previous batch's tradeoff.

| # | Fixed case | Sensitivity | Play(s) + reference(s) loaded | Routing-only total (excl. review-budget.md) | + review-budget.md (267) |
|---|---|---|---|---|---|
| 1 | CSS color change | NONE | — | 0 | 0 (budget step never reached) |
| 2 | Remove `[Authorize]` from an ASP.NET controller | HIGH | `plays/authorization.md` (98) + `references/aspnet-security.md` (149) | 247 | 514 |
| 3 | Authenticated file-download endpoint, user-supplied filename | HIGH | `plays/file-security.md` (145, was 155 — trimmed in batch 7) + `references/aspnet-security.md` (149) + `references/windows-security.md` (117) + `plays/authorization.md` (98) | 509 (was 519) | 776 (was 786) |
| 4 | New EF Core query for an existing, already-authorized report | MODERATE | `plays/code-review.md` (149) + `references/dotnet-security.md` (150) | 299 | 566 |
| 5 | New dependency added to `package.json` | MODERATE | `plays/dependency-security.md` (83) | 83 | 350 |
| 6 | Authentication middleware registration change | HIGH | `plays/authentication.md` (94) + `references/aspnet-security.md` (149) | 243 | 510 |

Unchanged from the original V3 Full baseline (`baseline.md`) for the
routing-only columns — nothing in the file-mode fix or the review-budget
wiring touched which plays/references any of these 6 cases route to.

## What this batch is looking for

A reduction in the routing-only columns above (fewer or smaller
plays/references genuinely needed for the same cases), found the same way
as before: a real candidate, checked with Jev as offline advice, then
verified by hand against the actual text and against
`tests/validation/*.md`'s relevant cases before touching anything.
