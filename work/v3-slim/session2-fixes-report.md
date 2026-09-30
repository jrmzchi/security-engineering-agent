# V3 Slim — Session 2: Confirmed-Gap Fixes

Scope: the two confirmed, concrete gaps from "V3 Slim 修正與封版任務"
(user-supplied task document, 2026-09-22), fixed in this order per the
user's approved plan. This is **not** the full Slim pass — per the user's
explicit instruction, these two fixes are not to be labeled
`V3 SLIM GOLDEN BASELINE`.

## Verification against the task document's claims (done first, before any edit)

| Claim in task document | Verified status |
|---|---|
| `AGENTS.md` points to a nonexistent `skills/threat-model/SKILL.md` | **False.** File exists (2022 bytes); `AGENTS.md:41`'s link is correct. No fix needed — confirmed and reported back, not silently assumed. |
| `scripts/macos/consistency-check.sh`'s git mode should be `100755` | **True.** Was `100644` while sibling scripts (`doctor.sh`/`install.sh`/`scan.sh`) are all `100755` — a leftover from when the file was first created in an earlier session. |
| `plays/review-budget.md`'s level is computed and applied nowhere | **True.** Confirmed independently in the first working session's `results.md` before this task document arrived. |
| `.git` worktree pointer in a delivered ZIP | Not applicable to this repository — no packaging/export script exists here to inspect; per the user's clarification, this refers to a ZIP delivered through a separate channel and is a note for future portable exports, not a defect to find in this repo. |
| 21 `consistency-check` hits need per-item adjudication | Re-ran both `scripts/windows/consistency-check.ps1` and `scripts/macos/consistency-check.sh` fresh (not from memory) — byte-identical output, still 21 hits, same content as the first working session's judgment. Re-read the actual lines for several hits to confirm rather than assume. See "Consistency check disposition" below. |

## Fix 1: git file mode

```bash
git update-index --chmod=+x scripts/macos/consistency-check.sh
```

Before: `100644 f0e549c...`. After: `100755 f0e549c...` (same blob hash —
content untouched, only the executable bit). Verified with
`git ls-files -s` immediately after staging, and again after the commit
below.

## Fix 2: review-budget wiring

**Plan presented to the user before implementing** (per their explicit
"計畫寫好後就繼續實作與驗證" instruction, this proceeded straight to
implementation after the plan below was stated in chat):

- Authoritative computation stays in `plays/review-budget.md` — no change
  to its Factors/Default-starting-point/Context-budget content.
- `plays/secure-development-workflow.md`'s workflow diagram gets one new
  step, "Determine review budget," between scanner selection and targeted
  review, plus a short prose section pointing to `plays/review-budget.md`
  for the actual procedure (not restating it) and to its "The floor this
  play cannot lower" for the non-override guarantees.
- `skills/security-review/SKILL.md`'s "Scope" step records the computed
  level; "Manual semantic analysis" applies it as loading depth, both as
  pointers to `plays/review-budget.md`, not restatements.
- `plays/review-budget.md`'s own "Output" section, which disclosed this as
  missing, gets updated to point at the new wiring instead.
- New end-to-end test case in `tests/validation/v3-review-budget-test-cases.md`
  (case 8), tracing one concrete change through all three files.

**Files changed** (diff reviewed line-by-line before committing):

| File | Change |
|---|---|
| `plays/secure-development-workflow.md` | +1 diagram step, +1 prose section (`## Review budget: computed here, defined in plays/review-budget.md`) |
| `skills/security-review/SKILL.md` | Step 1 ("Scope") and step 5 ("Manual semantic analysis") each gained one pointing sentence |
| `plays/review-budget.md` | "Output" section rewritten from "not wired, left to a later batch" to "wired here, see these three files" |
| `tests/validation/v3-review-budget-test-cases.md` | Replaced the stale "What this document does not validate" section with a new "End-to-end invocation case" (case 8) |

**Self-check for new duplication** (the point of this whole exercise is
not to fix one wiring gap by creating a new restatement elsewhere):
re-read every new sentence added to `skills/security-review/SKILL.md`
against `plays/review-budget.md`'s actual level definitions — the first
draft of the "Manual semantic analysis" edit accidentally restated the
MINIMAL/FOCUSED/ELEVATED/AUDIT depth rules verbatim; caught on re-read
before committing and rewritten to a bare pointer instead.

**Non-override guarantees**: not re-tested by the new case (case 7,
already in the file, and `plays/review-budget.md`'s own "The floor this
play cannot lower" section already cover DEEP-mode and HIGH/CRITICAL-
validation non-override at the play level) — case 8 only checks that the
new wiring actually reaches and applies the play's result, which is the
part that was actually missing.

## Consistency check disposition (fresh re-run, not carried over from memory)

Ran both `scripts/windows/consistency-check.ps1` and
`scripts/macos/consistency-check.sh` before AND after the two fixes above.
Both times: 21 hits, byte-identical between platforms, byte-identical
before/after (the fixes did not introduce or remove any hit).

**Correction (caught by the user re-running the scan against this
report's own committed content, not by me):** after this file itself was
committed, re-running the scan found **26** hits, not 21 — the 5 new ones
were this report's own lines (86, 89, 92 twice, 94, in the version quoted
above) quoting the STALE_TERM/VOCABULARY pattern text verbatim while
reporting on it. Verified by diffing the 26-hit output against the 21-hit
one before changing anything — confirmed all 5 new hits were exactly this
file, nothing else. Fixed by excluding `work/` from both scripts'
Markdown-scan prune list (`scripts/windows/consistency-check.ps1`'s
`$MdPruneNames` and `scripts/macos/consistency-check.sh`'s `PRUNE_ARGS`),
alongside `.git`/`node_modules`/`bin`/`obj`/`output`/`__pycache__` —
`work/` holds session working notes and analysis reports, not this kit's
own authored `plays`/`skills`/`templates`/`tests`, and is exactly the kind
of content `plays/repository-consistency.md`'s own "Interpreting output"
section already anticipates ("a Nit's own catalogue of past mistakes...
will legitimately match... without being an instance of the mistake
itself") — chose excluding it over documenting 5 recurring hits per report
because every future analysis report written under `work/` would
otherwise add more of the same noise indefinitely. Re-ran both scripts
after the fix: back to 21 hits, byte-identical between platforms and
identical in content to the original 21 documented below — confirming the
fix removed exactly the 5 false hits and nothing else.

```text
STALE_TERM (1)      plays/repository-consistency.md:101 — self-referential
                     worked example of the category's own output format,
                     not a live claim
VOCABULARY (12)     3x "CONFIRMED...chain" family — 1 self-referential
                     example, 2 correct negations ("a chain carries no
                     CONFIRMED status")
                     1x bare `INCONCLUSIVE` — historical narrative in
                     plays/adversarial-validation.md's "Why this is safe"
                     describing a retired design, not live usage
                     8x TARGETED/DEEP-vs-budget family — all are either
                     the deliberate naming-collision disclosure text in
                     plays/review-budget.md, or DEEP correctly used as a
                     review *mode* explicitly qualified alongside a
                     budget level to explain precedence (case 7's own
                     table row) — not an instance of the collision
BROKEN_REFERENCE (7) the established "there is no separate agents/X.md"
                     disclosure sentence in 7 Claude wrapper files — a
                     deliberate negated reference, not a dangling one
```

All 21 are re-confirmed benign, same disposition as the first working
session's review. Per the user's instruction, none of this correct content
was altered just to make the hit count reach zero — the count stays at 21
by design.

## Git

Two separate commits on the `v3-slim` branch (kept split for a clean,
independently-revertible history — the file-mode fix and the wiring fix
are unrelated changes):

```text
67f26bdc393246a90912362dd7dc0d12eade8dd8  fix: mark scripts/macos/consistency-check.sh executable
fbc19c3705bcea2fbad7c3515d1dd0f66aafe92e  feat: wire review-budget computation into the security-review workflow
```

Both on `v3-slim`, author/committer `jrmzchi` (matching the
identity fix applied earlier in this project's session history — this
machine auto-detects a different name/email that the user asked not to
use). File mode verified with `git ls-files -s` after commit 1:
`100755 f0e549c...` — persists correctly.

## Not done here (left for the full Slim pass)

- No new duplication-reduction candidates were searched for in this
  session — that is the separate, larger "完整 Slim pass" the user asked
  to batch separately.
- The `.git` worktree-pointer note for portable ZIP delivery is
  acknowledged but not actioned — no packaging step exists in this repo
  to fix.
- **This is not `V3 SLIM GOLDEN BASELINE`** — per the user's explicit
  instruction, these are two confirmed-gap fixes, not a completed Slim
  pass with a measured context-reduction metric.
