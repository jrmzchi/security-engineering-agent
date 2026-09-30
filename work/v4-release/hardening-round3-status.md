# V4 release hardening, policy round: status (2026-09-30)

**STATUS: `V4_RELEASE_NOT_READY`, stopped at step B.**
- Step A passed.
- Step B (revision 10, pre-registered in `5fea8f2`) did not pass: NW-1 and NW-2 are `FAILED`, and NW-3 ended in a
  hard stop.
- By the protocol:
  - step C (52 cases and the four repeats) did not run;
  - nothing was re-run or re-graded;
  - no fixture, grader or threshold was changed;
  - nothing was pushed.
- The previous records (`hardening-release-status.md`, `STOPPED_AT_A`, with its three CLI reproductions) are not
  rewritten.

## Evidence, kept apart

- **Published `origin/v4-release` = `6f90d0d`, kit `812115b5…`:**
  - revision 9, 52 of 52, one run per case;
  - it has no NONE gate;
  - it is not evidence for the kit below.
- **This branch, product `10f2149`, kit `27fff648ce788434c9f60b4fd299e27407e632cba70e44d7af2c5dd423a21aa8`:**
  - deterministic gates (next section);
  - the step-B model runs below.
  - No 52-case result exists for this kit.

## Step A: the STOP_NONE invariant

- **The rule (`6ed245f`).** `STOP_NONE` only when all of these hold:
  - every given file was read;
  - every file is plain UTF-8: no NUL byte, and the whole file decodes strictly;
  - `required_domains()` completed;
  - no domain was required.

  Every other file is `unread` ("cannot be decoded reliably"), giving `MANUAL_CHECK`, or `TARGETED_EXCEPTION` when a
  pair is visible anyway.
- **The previous round's three mid-line reproductions** now give CLI exit 2 `MANUAL_CHECK` with an `unread:` line.
- **Independent review:** adoptable on the blocking criterion. It traced from the code that no unread, NUL-bearing,
  non-UTF-8 or floor-error input can reach `STOP_NONE`.
- **Disclosed, not fixed** (`10f2149`, doc-only, under the blocking-only rule):
  - **A correction:** `6ed245f`'s message wrongly said that dropping the ASCII projection could only turn
    `TARGETED_EXCEPTION` into `MANUAL_CHECK`. For plain UTF-8, a signal glued to a non-ASCII letter now gives
    `STOP_NONE`. This is recorded in `signal_floor.py`'s known misses, and the floor has the same limit on every path.
  - 7-bit encodings (UTF-7, ISO-2022-*, HZ) are valid UTF-8, so they count as plain.
- **Recorded, not fixed** (review Minors and Nits):
  - `test_stop_none_implies_every_file_is_plain_utf8` uses the rule function as its own oracle, so its name claims
    more than it checks. Other tests pin the rule directly.
  - "No security theater" still says "a NONE gate that did not run", which is narrower than the play's new "did not
    permit the stop".
  - One condition in `_readings` is redundant.
- **Deterministic gates on `10f2149`:**
  - context_manifest 339 OK, on both interpreters;
  - feedback_store 354 OK (2 skipped);
  - 17 mutants killed;
  - offline fallbacks A/D/E/F built-in with the floor kept;
  - 9 feedback scenarios as before;
  - wrappers (PS 5.1 / PS 7 / Bash): 23 hits each; exit 2 without Python;
  - 52-case gate fire set unchanged.

## Step B: raw results (`rel10/nonewf`, one attempt each, all valid except NW-3)

| Case | Outcome | Checks that failed | Classification (checked against the transcript) |
|---|---|---|---|
| NW-1 | `FAILED` | G3 (no `produce_manifest` call), G4 (manifest fields written by hand; also `Semgrep` capitalised), G8 | G3/G4: **a real workflow miss.** The agent ran the gate (exit 1, `TARGETED_EXCEPTION web-security`), read `plays/web-security.md`, and correctly reported CONFIRMED CSRF with gate BLOCK. But it never read `skills/security-review/SKILL.md` and never built the manifest with `produce_manifest()`. The NONE action says "build the manifest" without naming the tool. G8: **a grader defect.** The agent read `plays/finding-validation.md` and `plays/security-gate.md` with `cat` through Bash; the grader counts only the Read tool |
| NW-2 | `FAILED` | G3, G4 | **A real workflow miss, as in NW-1.** Otherwise correct: the gate ran; no CONFIRMED finding (CSRF NOT_CONFIRMED); the report was limited to web-security; semgrep was recorded in `coverageGaps` |
| NW-3 | hard stop `MODIFIED` | — | **A harness defect.** `nonewf.tree_digest` meant to skip `.git`, but `sorted(os.walk())` walks the tree before the prune can apply, so `.git` was hashed. The agent's `git status` refreshed `.git/index` (27 files became 30). The working tree still held only the planted change. An informational grade of its transcript, which is not evidence because the run stopped, passes every check: the gate ran, `STOP_NONE`, the agent stopped, no manifest, scanner or summary |

What this does and does not show:
- In all three runs the agent **did** call the gate before stopping or reviewing, and acted on its exit.
- It did **not** follow the kit's manifest step on the exception path.
- This is one run per case. The gate call is still not enforced by code.

## Needed before a next attempt (each needs authorization)

1. **Guidance:** make the exception path name the tool.
   - The NONE action and the workflow row should say "build the manifest with `produce_manifest()`
     (`skills/security-review/SKILL.md` step 1), passing the gate's files as `scope_texts`".
   - The CLI's `TARGETED_EXCEPTION` output could print that next step as well.
2. **Harness, as a new pre-registered revision 11** (revision 10's results stay as recorded):
   - `tree_digest` must really skip `.git`;
   - G8 must count Bash reads (`cat`, `head`) of the two plays;
   - scanner names should be compared case-insensitively.
3. **Then** step B again under revision 11, and only if it passes, step C and step D.
