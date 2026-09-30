# V3 Slim Batch 3 — Results: security-review's Skill -> Play -> Reference routing/loading

Scope (per user instruction, 2026-09-22): only `skills/security-review`'s
routing and on-demand loading. No change to any other skill/play in this
batch.

## Executive result

**No safe candidate found. No files changed.** Three distinct,
evidence-backed candidates were investigated with real Jev calls in this
scope; all three came back "not safe to remove," for a consistent
underlying reason across all of them: `skills/security-review/SKILL.md`
is a self-contained working reference actively used *during* a review
(not a thin pointer skill like `security-change-detection`/`security-gate`),
and its restatements serve the reviewer at the point of use, not idle
duplication. Reported honestly per the user's explicit instruction — no
rule was removed to manufacture a reduction, and this is not
`V3 SLIM GOLDEN BASELINE`.

## Fixed-case baseline (before, and unchanged after)

See `batch3-baseline.md` for the full table and methodology. Unchanged
from `baseline.md`'s original V3 Full numbers for the routing-only
columns; the review-budget.md load (267 lines, from the previous batch's
wiring fix) is reported there separately, out of this batch's scope.

## Candidates investigated

| # | Candidate | Files | Jev result | Human judgment | Outcome |
|---|---|---|---|---|---|
| 1 | `skills/security-review/SKILL.md`'s "Attack path model" (7-node diagram) vs. `plays/finding-validation.md`'s own 6-node diagram + its explicit "same model, different granularity" reconciliation | `skills/security-review/SKILL.md:99-122`, `plays/finding-validation.md:155-184` | classification `adds_information_not_in_source` (0.91 confidence); `trim_safety` 1.66/2, 0.68 probability on "real risk" | Agree with Jev: the finer node split (separating Validation from Security controls) is a genuine working distinction a reviewer needs while actively tracing a candidate, not restated conceptual filler | **Retained, no change** |
| 2 | `skills/security-review/SKILL.md`'s "Non-negotiable rules" (3 rules) vs. `AGENTS.md`'s own "Non-negotiable rules" (same 3 rules, less specific citations) | `skills/security-review/SKILL.md:79-90`, `AGENTS.md:105-121` | classification `redundant_with_general` (0.95 confidence — the content genuinely is the same three rules); `trim_safety` 0.85/2 but **confidence 0.0** — flat, inconclusive distribution (0.38/0.39/0.23) | Low `trim_safety` confidence is this plan's own explicit "needs human review, don't act regardless" signal (see `phase3-jev-calibration-record.md`'s established pattern from the first batch). Re-reading both: `AGENTS.md` is definitionally read first, so the classification's "genuinely the same content" call is correct — but `skills/security-review/SKILL.md` is the same kind of self-contained, point-of-use reference as candidate 1, and restating its own most-often-violated rules at the moment a review starts is a plausible, real reason to keep them, not just habit. The disagreement between high classification confidence and flat safety confidence is exactly what this plan's rule exists to catch | **Retained, no change** — genuinely the closest call of the three, but not confident enough to act on |
| 3 | `references/aspnet-security.md`'s "File handling" section vs. `references/windows-security.md`'s path-handling sections (both loaded together in fixed case 3) | `references/aspnet-security.md:91-107`, `references/windows-security.md` (headings) | Not sent to Jev — structural check first (heading list + direct read) found no topical overlap at all: `aspnet-security.md` covers ASP.NET-specific types (`IFormFile`, `StaticFiles`) and explicitly redirects general .NET path APIs to `references/dotnet-security.md`; `windows-security.md` covers OS-level path semantics (8.3 names, junctions, drive letters) never mentioned in `aspnet-security.md` at all | Already well-factored; no restatement to investigate further | **No candidate here — clean separation confirmed, not a false negative** |

## Regression check

No file was changed, so no `tests/validation/*.md` case needed re-running
— `git status`/`git diff` on this batch's scope is empty. The relevant
cases that would have needed re-checking had any candidate been actioned:
`tests/validation/classification-test-cases.md` (for candidate 2's
AGENTS.md/SKILL.md relationship) and any case referencing the attack-path
model in `tests/validation/gate-test-cases.md`/`expected-results.md` (for
candidate 1) — none needed touching.

## Unresolved risks / notes for future batches

- The previous batch's review-budget wiring adds 267 lines
  (`plays/review-budget.md`) to every case that reaches a targeted review
  — a known, deliberate tradeoff from fixing that gap, not something this
  batch's scope covers, but worth keeping in view: if a future batch finds
  real reduction elsewhere in `security-review`'s pipeline, this fixed
  cost partially offsets it in the total context-budget accounting.
- Candidate 2 (non-negotiable rules) is the one genuinely close call in
  this batch — not acted on due to low `trim_safety` confidence, but
  flagged here rather than silently dropped in case a future pass with a
  different framing (e.g., checking whether *other* skills also restate
  AGENTS.md's non-negotiable rules the same way, which would strengthen
  or weaken the case for a kit-wide pattern change) wants to revisit it.
- This batch's negative results (0 of 3 candidates safe) are consistent
  with every other Slim pilot run so far in this session (0 of 21
  quick-reference rows, 1 of 1 adversarial-validation restatement) — a
  recurring pattern worth naming to whoever plans the next batch: this
  kit's apparent duplication has so far turned out to be independently
  load-bearing content at a noticeably higher rate than a first read of
  the file structure would suggest.
