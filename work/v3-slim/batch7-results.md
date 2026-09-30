# V3 Slim Batch 7 — Results: final scope-limited reduction trial

Per user instruction (2026-09-22): up to 2 not-yet-verified candidates
from the existing inventory, pre-recorded before checking, human
semantic check + relevant case validation with Jev as offline advice
only, modify only if safety and reduction both hold. No re-checking
already-rejected candidates, no expanding to a third candidate.

## Outcome

**One candidate found, verified safe, and applied.** No second
comparable candidate was found after a genuine search (documented in
`batch7-pre-record.md`) — proceeded with one per "最多 2 個" allowing
fewer, rather than forcing a weaker second one. This is a real,
measured reduction, but still **not `V3 SLIM GOLDEN BASELINE`** — one
small, isolated trim does not constitute the full validated baseline the
user's completion criteria describe.

## Candidate: `plays/file-security.md`'s Windows/macOS path-semantics summary

Pre-recorded in full, before the check, in `batch7-pre-record.md`
(affected fixed case, current load, expected savings, possible missed
rules — written down first, per instruction).

### Jev advisory (offline, not authoritative)

`classification`: `redundant_with_reference` (0.68 confidence, 0.84
probability). `trim_safety`: 0.72/2, confidence 0.44, but with a clearly
skewed distribution this time — 0.33 + 0.62 = 0.95 combined probability
on "safe" (0: nothing lost, 1: minor convenience only), just 0.05 on
"real risk." This is a materially stronger, more decisive signal than
every previous candidate this session (which either landed on "keep" or
came back flat/inconclusive).

### Human semantic check (the actual basis for the decision, not the score alone)

1. **Content comparison**: `plays/file-security.md`'s 17-line summary
   was confirmed to be a *less complete* version of both
   `references/windows-security.md`'s and `references/macos-security.md`'s
   "Path semantics" sections — missing the denylist-vs-allowlist
   bypass-direction distinction and the Unicode NFC/NFD normalization
   issue entirely. It was never a reliable standalone substitute for the
   references, even before this trim.
2. **Routing independence, confirmed by direct read**:
   `skills/security-review/SKILL.md:131`'s coarse-table row for "File
   upload/download/paths" already independently names both reference
   files for this domain — this routing mechanism does not read or
   depend on `plays/file-security.md`'s own text, so trimming that text
   does not touch the guarantee that a reviewer following the kit's
   normal routing reaches the references.
3. **Counter-example confirming this is the right shape to trim to**:
   `plays/configuration-security.md`'s analogous IIS section is already
   written as a pointer plus one non-redundant nuance, not a restated
   list — the fix brings `file-security.md` in line with this kit's own
   established, already-correct pattern rather than inventing a new one.
4. **Pre-existing entry-path caveat, not newly introduced**:
   `skills/security-review/references/quick-reference.md`'s row 24
   (file upload/download) names only `plays/file-security.md`, no
   reference — already flagged in `baseline.md` as under-loading
   relative to the coarse table, before this batch. The play's summary
   was already an incomplete mitigation for that pre-existing gap; this
   trim does not make that specific path any worse than it already was.

**Decision: safe to trim.** Verified against `tests/validation/*` and
`tests/fixtures/*` for any dependency on the removed facts — none found
(see new case below).

## Diff

```diff
 ## Windows and macOS path semantics
 
-Consider both when the deployment target is cross-platform:
-
-```text
-Windows: case-insensitive filesystem by default, drive letters, UNC
-    paths, `\` and `/` both often accepted as separators, reserved
-    device names (CON, PRN, AUX, NUL, COM1...) as filenames can behave
-    unexpectedly
-macOS: case-insensitive-by-default (but case-preserving) on the common
-    default filesystem format, though case-sensitive volumes exist;
-    do not assume filename comparisons are safe across both without
-    checking
-```
-
-See `references/windows-security.md` and `references/macos-security.md`
-for platform-specific detail.
+Consider both when the deployment target is cross-platform — see
+`references/windows-security.md` and `references/macos-security.md` for
+the platform-specific detail (case-insensitivity's risk direction
+depending on denylist vs. allowlist checks, path-separator acceptance,
+drive letters/UNC paths, reserved device names, Unicode normalization).
```

`plays/file-security.md`: 155 -> 145 lines (10 lines net, after
accounting for the new sentence).

## Before/after context measurement

| | Before | After |
|---|---|---|
| `plays/file-security.md` | 155 | 145 |
| Fixed case 3 routing-only total (`batch3-baseline.md`) | 519 | **509** |
| Fixed case 3 + review-budget.md | 786 | 776 |

This is the first actual, applied reduction across all 7 V3 Slim
batches this session.

## Validation

- New case: `tests/validation/v3-play-reference-trim-test-cases.md`
  case 1 — traces the routing-independence guarantee and confirms no
  existing fixture/test depends on the removed facts (`grep` swept
  across all of `tests/`, zero matches for the specific removed terms).
- `batch3-baseline.md`'s case 3 row updated to the new numbers, with the
  prior numbers kept visible ("was 519") rather than silently
  overwritten.
- Consistency check (`scripts/{windows,macos}/consistency-check.*`)
  re-run after the edit: still 21 hits, byte-identical content, no new
  hit introduced.
- No fixture, classification table, or gate/chain/adversarial test case
  needed re-running — none reference the removed content.

## Second candidate: not found

Searched (documented in `batch7-pre-record.md`): every play for the same
"See references/X" shape (only 2 exist kit-wide;
`configuration-security.md`'s was already minimal, confirming it as the
*target* shape rather than a second candidate), `templates/attack-surface-map.md`
and `templates/project-security-baseline.md` (both a single
non-repeating worked example per node/edge/fact type — no internal
duplication), and `references/windows-security.md` vs.
`references/iis-security.md`'s "permissions" sections (already a
correctly-layered general-principle-plus-specific-elaboration pair, not
duplication). None met the bar. Not forcing a second candidate, per
instruction.

## Git

Committed to `v3-slim`: `b5635613216ec43f492ed690c0205c5edc219ecc`
("feat: trim plays/file-security.md's redundant Windows/macOS path summary").

## Not done here

- No further reduction candidates pursued beyond this one, per
  instruction not to expand searching.
- **Not `V3 SLIM GOLDEN BASELINE`** — this is one verified, applied
  trim; the user's own completion bar (all fixed cases + full
  regression + a reproducible metric, assessed together) has not been
  formally re-run end-to-end as a single pass.
