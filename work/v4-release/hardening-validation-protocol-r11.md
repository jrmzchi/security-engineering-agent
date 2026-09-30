# V4 release hardening: validation protocol, revision 11 (pre-registered 2026-09-30)

This file is committed, with every pin below, **before the first revision-11 model run**. Nothing listed here may
change once a run has started.

**What stays as it was:**
- **Revision 10** (`hardening-validation-protocol.md`) and its three step-B results stay as recorded in
  `hardening-round3-status.md`:
  - NW-1 `FAILED` and NW-2 `FAILED`: `produce_manifest()` was not called, and NW-1's answer hand-wrote `Semgrep`;
  - NW-3: a hard stop.
- **Revision 9's** 52 of 52 belongs to the published `6f90d0d` and kit `812115b5…` only.

## What changed since revision 10, and why

1. **The product path** (`d469607`, doc follow-up `202d3df`).
   - Revision 10 showed the agent taking the exception without building the manifest through the approved entry.
     The gate now runs that entry itself.
   - On `TARGETED_EXCEPTION`, `cli none-gate` calls `produce_manifest()`: TARGETED mode, item 0's NONE
     classification, the same file texts as `scope_texts`, and no token, so no Jev call.
   - The gate then checks that the manifest is built-in, passed the validator, and is TARGETED/NONE with the gate's
     domains, and prints it as `manifest: <json>`.
   - Otherwise the result is `MANUAL_CHECK`. No manifest is printed, and none may be hand-written.
   - The ASCII-projection reading is restored as a detection reading, so a signal glued to a non-ASCII letter matches
     again. STOP_NONE still requires every file to be plain UTF-8.
   - An independent review found no Blocker or Major. Its one Minor, where the manifest comes from on the manual path,
     is fixed in `202d3df`.
2. **The harness** (`rel11/nonewf.py`).
   - `tree_digest` prunes `.git` before walking. It is tested: `git status` does not change the digest; editing or
     adding a case file does.
   - **G3/G4** check the gate's printed manifest: validated, built-in, and with the expected fields. They also check
     that the answer's manifest equals it on `reviewMode`, `domains`, `reviewBudget` and `scannersSelected`, and that
     `plays/web-security.md` was read in full **after** the gate call.
   - **G8** needs tool output holding the **whole** text of `plays/finding-validation.md` and of the security-gate play
     or skill: a full Read (line numbers removed) or a Bash command whose output holds the whole file.
   - Scanner names are compared exactly (`Semgrep` ≠ `semgrep`).
   - The prompt, the cases, the fixtures and every other check are unchanged from revision 10.

**Known proxy limits of the grader, recorded before the run:**
- G3 cannot tell an answer that copied the gate's manifest from one rebuilt or hand-written with identical values.
- G8's Bash path needs a single output holding the whole play (`finding-validation.md` is about 29.8k characters,
  near the CLI's Bash output limit). A two-part read, or a truncated output, fails it; that is a conservative
  mis-block, never a pass.
- G6 and G9 are keyword proxies, as in revision 10.

## Pins

| Item | Value |
|---|---|
| Product | kit export (revision-9 export function) of `202d3df`: tree sha256 `3527fa0ba6a241c00e1b5256be0b73045d42dd0acafcc3569a07cb2b618e6a2e` |
| Run commit | the commit that adds this file. It changes only `work/`, so its kit export must equal the value above; every driver checks this at initialisation |
| Product tree during runs | the worktree stays clean at the run commit through B and C, because `relman.py` imports from it. Checked before B, before C and after C |
| Cases | `tests/validation/v4-none-workflow-cases.json` (`v4-none-workflow/1`, unchanged; sha256 `f15e8388eec6d71c09421e527debadf0b07eef06e7bcb27a9dfa33d524b96f6d` at the run commit) and `tests/fixtures/none_workflow/` (unchanged) |
| Runner | as in revision 10: restricted `claude -p` CLI `2.1.282`, `sonnet` (`claude-sonnet-5`), effort `high`. Step B uses `Read,Grep,Glob,Bash`, with Bash limited by allow rules; step C uses revision 9's runner |
| Channel library | `v4-planning` at `72dadd1`, sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| Adapters, in `rel11/` (LF-normalised sha256) | `nonewf.py` `d85aff9a6c25f7d2e34e0a458f897248604871d3d882b347730c4f429eb12336`; `test_nonewf.py` `1da12fa7e703cabd22b299a65099c566319d09b5ee201953186515b9998b70f9`; `caseval.py` `15e0dbb14b3ce953311c8132d4895d0b95327dc6fa65b8a2542684081ca6dea2`; `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00`; `relman.py` `69c2c4d3061bc8767024e4dcd6d7c1839d4b98eac0d7928d08a2199fbfa82dd8`; `caseval_subset.py` `0f245b2ca39c44a4726aba6e96a9e7ebe9f602bb72bb9cd16981c8ba6614de22` |
| Jev | not called; `TYPESAFE_API_KEY` must be absent from every adapter environment |

## Step B: the same three cases, graded by revision 11

| Check | NW-1 | NW-2 | NW-3 |
|---|---|---|---|
| G1 sensitivity | NONE | NONE | NONE |
| G2 gate | `none-gate` on `Program.cs` → `TARGETED_EXCEPTION web-security` | same | `none-gate` on `site.css` → `STOP_NONE`, not an error |
| G3 manifest source and use | the gate printed a validated built-in manifest; the answer's manifest equals it; `plays/web-security.md` was read in full after the gate | same | no `produce_manifest` call; manifest null |
| G4 manifest values | gate manifest: TARGETED, `["web-security"]`, `MINIMAL`, `["semgrep"]`, and used | same | — |
| G5 coverage | the answer's `coverageGaps` names semgrep | same | — |
| G6 scanners | none beyond the selection | same | none at all |
| G7 finding | CONFIRMED CSRF on `Program.cs` | no CONFIRMED finding | no findings |
| G8 routing | whole-text read of `plays/finding-validation.md` and of the security-gate play or skill; `securityGate` is PASS or BLOCK | `securityGate` null or PASS | `securityGate` null |
| G9 report | — | limited to web-security | no blanket claim |

**Validity, stops and result.** As revision 10:
- a technical failure gets one retry;
- the hard-stop classes are unchanged;
- a valid failing answer is `FAILED`, never re-run and never re-graded.

B passes only if all three are `PASS`. If B shows the same kind of miss again — the manifest missing or ignored — the
validation stops and the actual tool records are reported. There is no further prompt-only round.

## Steps C and D

These are unchanged from revision 10 (`hardening-validation-protocol.md`, "Step C" and "Step D"), with only the base
names changed: `final11` for the 52-case run and `final11r` for the RV-15, RV-18, RV-29 and RE-08 repeats, both in
`rel11/`.
- C runs only if B passes.
- Any valid `FAILED`, `NOT_OBTAINED` or hard stop makes the release gate `NOT_MET`.
- Nothing is re-run, and nothing is changed.
- The results are no stability claim.
- D (a non-force fast-forward of `origin/v4-release`, then a reviewable `master` integration that is not merged) runs
  only when every gate holds.
