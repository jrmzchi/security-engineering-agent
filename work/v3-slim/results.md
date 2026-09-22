# V3 Slim — Results (final)

## Executive result

**No changes made to the kit.** Two duplication candidates were
investigated with real Jev calls: `skills/security-review/references/quick-reference.md`'s
entire 21-row table (exhaustively, not sampled — extended from an initial
7-row sample after the API key was rotated 2026-09-22) against
`skills/security-review/SKILL.md`'s coarse routing table, and
`skills/adversarial-validation/SKILL.md`'s "Results" section against its
authoritative play. Both came back "not safe to remove" — the first from
direct, complete evidence (0 of 21 rows redundant, the deliberate negative
control scoring highest of all), the second from a low-confidence signal
that a follow-up human semantic review confirmed rather than overrode.
This is reported as the honest outcome per the user's decision (2026-09-22)
to stop expanding scope further, and per this plan's own §5 completion
condition that explicitly anticipates "no improvement, report it": no
reproducible slimming metric was achieved, so none is claimed.

## Basis and commits

- Baseline (V3 Full): `0ffd18ec8af3651af48a4f6187cdadd516045be1` on `master`.
- Working branch: `v3-slim`, in an isolated worktree
  (`../security-engineering-agent-v3-slim`), created from that same commit.
- Because no kit file was changed, `v3-slim`'s tree is identical to
  `master`'s except for the new `work/v3-slim/` directory itself (this
  file, `phase0-baseline-record.md`, `baseline.md`,
  `phase3-jev-calibration-record.md`, `full-linecounts.tsv`) — see "Git
  status" below for what that means for merging.

## Test comparison

No automated golden/regression suite exists in this repository (verified,
not assumed — see `phase0-baseline-record.md`). Since no kit file changed,
there is nothing to regress: every `tests/validation/*.md` case's expected
answer is unaffected because its subject files
(`skills/security-review/SKILL.md`,
`skills/security-review/references/quick-reference.md`,
`skills/adversarial-validation/SKILL.md`, and the other 5
adversarial-validation touchpoints) are byte-identical to the baseline
commit. No case needs re-running to confirm this — `git diff master v3-slim`
on those paths is empty.

## Fixed-case behavior comparison

Identical to baseline for the same reason — the 6 fixed cases in
`baseline.md` (CSS change / ASP.NET authorization change / file-download
endpoint / EF Core query / dependency update / auth middleware) route
through exactly the same files, since none of those files changed. No
"after" column differs from the "before" column recorded there.

## Context measurement method and change

Method: per-file line counts (`full-linecounts.tsv`), summed for whichever
files a fixed case's routing tables send a reviewer to (see `baseline.md`
for the worked totals per case, e.g. case 3's 519-line total across
`plays/file-security.md` + two references + `plays/authorization.md`).

**Change: none.** No file's line count changed, so no case's total changed.
Wall-clock/token-cost of the Jev calls themselves is not counted here —
that was offline analysis cost during this pilot, not something the kit's
own review workflow pays per the plan's own Phase 3.1 boundary ("V3 Slim
的正式執行流程不得依賴 Jev").

## Candidates considered and retained unchanged, with reasons

| # | Candidate | Files | Why retained |
|---|---|---|---|
| 1 | All 21 rows of `skills/security-review/references/quick-reference.md`, vs. their matching `skills/security-review/SKILL.md` coarse-table rows | `skills/security-review/SKILL.md:123-134`, `skills/security-review/references/quick-reference.md` (entire table) | Exhaustively checked (not sampled) after the API key was rotated 2026-09-22: 0 of 21 rows classified as redundant with the general table, 0 scored near "no added value." The deliberate negative control (line 28, `plays/finding-validation.md`) scored highest on both classification confidence and uniqueness of the whole set, validating the process. The single closest-to-borderline row (line 22, `[Authorize]`/role checks) was individually re-read by hand and still retained — it names a mechanism cue the coarse row's vulnerability-class wording doesn't. Full detail: `phase3-jev-calibration-record.md` (initial 7-row sample) and `phase3-jev-full-table-results.md` (complete 21-row table). |
| 2 | `skills/adversarial-validation/SKILL.md`'s "## Results" section vs. `plays/adversarial-validation.md`'s "Results use existing vocabulary" + "Structured result metadata" sections | `skills/adversarial-validation/SKILL.md:44-67`, `plays/adversarial-validation.md:139-193,195-323` | Jev's own confidence on whether trimming was safe was 0.0 (flat distribution) — a "needs human review" signal per this plan's own rule, not something to act on regardless. Human re-read found the section plays the same "surface one load-bearing nuance before the reader opens the full play" role its two clean sibling SKILL.md files also play (compare `skills/security-gate/SKILL.md`'s "one rule that matters most"), just covering more ground. Removing it risks the exact unearned-confidence failure mode `plays/adversarial-validation.md`'s own "Sequential fallback" section warns against. |

## 尚存風險 / known gaps found along the way (out of this pilot's scope)

### review-budget.md is under-wired, not over-duplicated

`plays/review-budget.md:260-267` (its own "Output" section) states plainly:
`AGENTS.md`'s workflow step 1 points to this play as an input, but no step
in `plays/secure-development-workflow.md`, and no step in
`skills/security-review/SKILL.md`, actually computes this budget level or
applies it to scope a review — "that specific invocation is left to a later
integration batch." Found while checking whether review-budget was a good
V3 Slim pilot candidate (it was not — its level vocabulary is defined in
exactly one file, no cross-file duplication exists to trim there). This is
the opposite problem from what V3 Slim looks for (a missing wire, not a
redundant copy), so it is out of scope for this pilot's fixes. Recorded
here per the user's instruction (2026-09-22) rather than opened as a
separate task.

Side-finding: this exact phrasing ("left to a later integration batch") is
not caught by `scripts/*/consistency-check.*`'s `STALE_TERM` pattern for
this failure shape (`deferred to a (later )?(integration )?batch` requires
"deferred to"; this text says "left to"). A narrow, real gap in that
pattern's coverage, consistent with the tool's own documented nature
(mechanical recall, not exhaustive) — not something this pilot fixes
either, but worth knowing if `tools/consistency-patterns.txt` is revisited.

### Jev pipeline notes for any future reuse

- Auth: `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer
  <key>`. The key used for the first 8 calls in this session was exposed in
  the chat transcript by an earlier mistake (a diagnostic `xxd` dump); the
  user kept using it for that batch and rotated it before this session's
  remaining 14 calls (confirmed working via a smoke test, 2026-09-22). No
  further action needed on that front.
- The calibration pattern that worked well: always include at least one
  deliberately-labeled negative control (a case whose correct answer is
  known in advance) alongside real candidates in the same batch, and treat
  a low-confidence score as "look closer," never as "average toward the
  middle and proceed."

## Completion assessment against this plan's §5 conditions

```text
V3 Full golden/regression tests pass under the same conditions        -> N/A, nothing changed to regress; baseline unaffected
No unexplained security-capability regression on fixed cases          -> true, nothing changed
Every deletion/change traces to source, authority, and evidence       -> N/A, no deletion/change was made
At least one pre-defined slimming metric shows reproducible improvement,
    or is honestly reported as not achieved                            -> not achieved; reported here, not claimed
V3 Slim's production workflow needs no Jev key/SDK/MCP to run          -> true; Jev was only used offline during this pilot, never wired into any play/skill
```

## Not done / left open

- `quick-reference.md`'s full 21-row table has now been exhaustively
  checked (not sampled) — see "Candidates considered" above and
  `phase3-jev-full-table-results.md`. Only 1 of `adversarial-validation`'s
  several plausible internal-restatement candidates was checked; a wider
  pass there might still find something, but was not pursued further per
  the user's decision to stop expanding scope (2026-09-22, reaffirmed
  after the full-table check came back the same way).
- V4's proposal for bringing Jev into the runtime decision layer is out of
  this plan's scope by its own instruction ("不要在本次 V3 Slim 中實作 V4") and
  is not attempted here.

## Final conclusion

**V3 Slim is complete. Recommendation: `NO_SLIM_CANDIDATE_FOUND` — the kit
stays as V3 Full, unchanged, and that is the correct outcome given the
evidence, not a shortfall of this pilot.**

Two duplication hypotheses were formed from this session's own prior
history (the routing-table split, and the adversarial-validation
5+-layer field), both were checked with real, working Jev calls rather
than assumed, and both were checked exhaustively or near-exhaustively
rather than left as an untested guess:

- `quick-reference.md` vs. `SKILL.md`'s coarse table: **21/21 rows**
  checked. 0 redundant. The one deliberately-planted negative control was
  correctly identified as non-redundant with the highest confidence of the
  batch, which is what makes the "0/21 redundant" result trustworthy rather
  than a rubber stamp.
- `skills/adversarial-validation/SKILL.md`'s restatement: 1 candidate
  checked, came back genuinely ambiguous (not confidently safe), and a
  human re-read sided with keeping it after finding it serves the same
  role its two clean sibling files' own non-bare-pointer paragraphs serve.

This kit's structure, at least in the two places this pilot specifically
tested, is not carrying dead weight — the apparent duplication is mostly
independently-useful content (symptom-recognition cues, a load-bearing
practical nuance) that happens to converge on the same destination, not
redundant copies of the same fact. The one real, separate finding from
this work is not a duplication at all but a wiring gap
(`plays/review-budget.md`'s budget level is computed nowhere), recorded
above and explicitly left open rather than fixed, since fixing it is out
of this plan's scope.

No file in `plays/`, `skills/`, `templates/`, or `references/` was
modified. `master` is untouched. The `v3-slim` branch/worktree holds only
this working record and is being kept per the user's instruction, not
merged or deleted.

