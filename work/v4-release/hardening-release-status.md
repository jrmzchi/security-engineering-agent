# V4 release hardening: release status (2026-09-30)

**STATUS: STOPPED at validation step A.** The fix-only re-review of the Unicode round still found an input that makes
`none-gate` wrongly return `STOP_NONE`. The user's rule for this round: "若仍有可錯回 `STOP_NONE` 的未解問題，停止發布並回報，
不自動開下一輪". So:
- no NONE-workflow model run (step B);
- no 52-case run and no repeats (step C);
- no push, and no master integration change (step D).

## Evidence, kept apart

**Published version: `origin/v4-release` = `6f90d0d`**, kit `812115b5…`.
- Revision 9: 52 of 52 passed, one run per case.
- It has no NONE gate: the NONE stop there depends on the agent noticing the CSRF signal pair.
- That result stands for that kit only.

**This branch: `v4-release-hardening` = HEAD of this record's commit.**
- The product is as of `b4f6864`, kit export `cd838128c9200dc345f8c08e020abd0048dcfcc69f7b05ac4844e4c3487ddef2`. It is
  computed with the revision-9 export function, and that function reproduces `812115b5…` for `6f90d0d`.
- Deterministic evidence only:
  - context_manifest 338 OK, on both the PATH Python 3.13 and the embedded one;
  - feedback_store 354 OK (2 skipped);
  - 22 mutants on the gate, the CLI and the documents, all killed;
  - offline fallbacks A/D/E/F: built-in, floor kept;
  - 9 feedback-record scenarios: as before;
  - wrappers (PS 5.1, PS 7, Git Bash): 23 hits each, identical to the base; exit 2 (ERROR) without Python;
  - adapter tests: caseval 49 OK against this repo;
  - 52-case gate integration: the fire set equals revision 9's {RV-18, RV-28, RE-09, RE-10, RE-11};
  - mixed-encoding sweep: 0 wrong STOP_NONE over 37,982 newline-bounded files, against 7,426 on `67d6d29`.
- **No model-based validation has run on this kit.**

## Security gaps

**Closed:**
- The NONE stop has a code entry, `cli none-gate`. It runs the floor before any NONE stop that goes through it, and no
  failure yields `STOP_NONE`.
- The signal-pair exception's handling and reporting are defined consistently: web-security only, MINIMAL, the
  manifest's scanners with unavailable ones in `coverageGaps`, a finding goes through finding-validation and then
  security-gate, and no finding gets one line limited to that domain.
- The following no longer yield `STOP_NONE`:
  - UTF-16/32 in either byte order, with or without a BOM, at any alignment;
  - a BOM that disagrees with its content;
  - segments that switch encoding at line breaks;
  - non-ASCII route text, including U+4E22.
- An undecodable NUL-bearing file, and a NUL-bearing file over 1 MiB, give `MANUAL_CHECK`.

**Open, and blocking:**
- **The fault:** an encoding switch in the middle of a line, with a signal directly next to the switch point.
- **How it happens:** a byte of the neighbouring character decodes as an ASCII word character (U+3001 in UTF-16-LE
  gives `01 30`, and 0x30 is `0`). That character glues itself to the signal and defeats `\b`.
- **Reproduced through the real CLI:** exit 0, `STOP_NONE`, no `unread:` line, on three constructions.
- **Scope:** the re-review counted 636 characters (for example U+3000–U+300F) in one direction, plus 3,202 combining
  marks in others.
- **Not a regression:** `634f77e`, `67d6d29` and `b4f6864` all miss it. The published version has no gate, so this
  input stopped at NONE there too.
- **Practical likelihood:** very low, since a file would have to switch between UTF-16 and UTF-8 mid-line. But the
  rule is literal.

**Open, not code-closable:** whether the agent calls the gate at all. The workflow is Markdown the agent follows.
Nothing forces the call; this is disclosed, not claimed.

## Decisions needed (see the chat report)

1. **Close the mid-line gap.** Recommended: a positive reliability rule. A NUL-bearing file is reliable only when a
   single encoding and alignment explains all its NUL bytes; anything else gets `MANUAL_CHECK`. The cost is more manual
   checks. The alternative is to accept the gap as a disclosed non-coverage (a scope change the user would have to
   make).
2. **Authorize the next round:** whichever option is chosen needs its own fix, review and re-review before steps B–D.

## Prepared, not pinned, not run

- `tests/fixtures/none_workflow/` and `tests/validation/v4-none-workflow-cases.json`, for step B. Uncommitted: they
  are pinned only with the protocol, before the first model run.
- The local adapters, which are not shipped:
  - `nonewf.py`: the step-B driver, with a grader that has 6 unit tests;
  - `caseval_subset.py`: the four-case repeat wrapper, with `caseval.py` unchanged;
  - `relman.py`: its release-repo path now points at this branch.
- **One calibration run was made** with the step-B runner flags: a neutral prompt in a neutral directory, not a case,
  not graded. It found one harness defect, the working-directory check after the runner's `cd` into the kit, which was
  fixed before any pin. That is a disclosed model run outside the validation.

## Git housekeeping done this round

- The origin URL was updated to `jrmzchi/security-engineering-agent` (local config only). Before the change, both URLs
  served identical refs.
- **Kept on purpose:**
  - both golden-baseline tags;
  - `refs/original`;
  - the scratch worktree;
  - every published commit.

## Master integration (read-only look, not prepared)

- `origin/master` (`dc51ce9`) has one commit that the V4 line lacks: a README edit, "describe V3 baselines and planned
  V4". Its "planned V4" text would be stale after a V4 merge.
- Against `origin/master`: `origin/v4-release` changes 166 files, and this branch 173.
- `git merge-tree` reports no conflicts with this branch.
- No integration branch or PR was created. That is step D, which was not reached.
