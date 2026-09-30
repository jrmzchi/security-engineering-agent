# V4 release hardening: validation protocol, revision 10 (pre-registered 2026-09-30)

This file is committed, with every fixture, expected result and pin below, **before the first validation model run**.
Nothing listed here may change once a run has started.
- Revision 9 (`final-validation-protocol.md`) and its 52 of 52 result belong to the published `6f90d0d` / kit
  `812115b5…`, and stay as they are. They are not evidence for this kit.
- The step-A record of the previous round (`hardening-release-status.md`, `STOPPED_AT_A`) is not rewritten.

## What is validated

| Item | Value |
|---|---|
| Product | kit export (revision-9 export function) of `10f2149`: tree sha256 `27fff648ce788434c9f60b4fd299e27407e632cba70e44d7af2c5dd423a21aa8`. Step A: the policy fix `6ed245f`, its independent review (adoptable on the blocking criterion), and the disclosure-only commit `10f2149` |
| Run commit | the commit that adds this file. It changes only `tests/` and `work/`, which are outside the kit export, so its kit export must equal the value above; every driver checks this at initialisation and stops on a difference |
| Product tree during runs | the worktree `security-engineering-agent-v4-hardening` stays clean at the run commit for the whole of B and C, because `relman.py` imports the product from it. This is checked before B, before C and after C |
| Runner | restricted `claude -p`, CLI `2.1.282`, `--model sonnet` (`claude-sonnet-5`), effort `high`. The tool sets per step are given below |
| Channel library | `v4-planning` at `72dadd1`, read-only, sha256 `ca5476b7eb684ed3d2d2ac48e965dd7d1c3ea27185edaace6381cb5295d412fd` |
| Adapters (local, not shipped; LF-normalised sha256) | `caseval.py` `15e0dbb14b3ce953311c8132d4895d0b95327dc6fa65b8a2542684081ca6dea2` (unchanged from revision 9); `caseresult.py` `42eb03657c6b4dd8a4b59ecff9b27558df892baa0798a3871312efcc97033b00` (unchanged); `relman.py` `69c2c4d3061bc8767024e4dcd6d7c1839d4b98eac0d7928d08a2199fbfa82dd8` (one line changed: the product repository path now points at this branch's worktree); `nonewf.py` `a58c147648af2a7477493902002050594a65acb0620d1d1133719838bfef07fb` (new, step B); `test_nonewf.py` `783a8eae4d07d5399ced32303c9d01b2492c8aa65256abceeb5b8146bbefd105`; `caseval_subset.py` `0f245b2ca39c44a4726aba6e96a9e7ebe9f602bb72bb9cd16981c8ba6614de22` (new, the repeats) |
| Jev | not called; `TYPESAFE_API_KEY` must be absent from every adapter environment |

**Calibration, disclosed.**
- One neutral run was made before this file existed: not a case, not graded, in a neutral directory.
- It only checked the harness's assumptions about the step-B runner.
- It found one harness defect, fixed before pinning: the working-directory check did not allow the runner's `cd` into
  the kit.
- It is a debugging record, not release evidence.

## Step B — the TARGETED/NONE workflow, run by a real agent

**Cases:** `tests/validation/v4-none-workflow-cases.json`, `v4-none-workflow/1`, fixtures under
`tests/fixtures/none_workflow/`.
- **NW-1 (positive, finding).** An ASP.NET app with cookie authentication (`SameSite=None`) and a `MapPost` account
  deletion without antiforgery. The change fixes a comment typo in `Program.cs`. Expected: sensitivity NONE; the gate
  returns `TARGETED_EXCEPTION web-security`; a web-security review at MINIMAL; a CONFIRMED CSRF finding, routed through
  finding-validation and security-gate.
- **NW-2 (positive, no finding).** The same app, but with `SameSite=Strict` and antiforgery validated by a header. The
  same comment change. Expected: the gate returns `TARGETED_EXCEPTION`; no CONFIRMED finding; a report limited to
  web-security.
- **NW-3 (negative).** A bearer-token API (no ambient credential); the change edits a CSS colour in
  `wwwroot/css/site.css`. Expected: the gate returns `STOP_NONE`; the agent stops, with no manifest, no scanner and no
  security summary.

**Runner.**
- Each case is its own git repository with one uncommitted change. The runner's working directory is that repository;
  the kit is the only `--add-dir`.
- Tools: `Read,Grep,Glob,Bash`. Bash is limited by allow rules to `python`, `python3`, `git`, `cd`, `ls`, `where`,
  `which` and `semgrep`, with `--restricted`, no MCP server, and `--permission-prompts none`.
- The allow rules are not a sandbox: `python -c` can run arbitrary code. Isolation is enforced by the checks below,
  not by the tool set.
- The prompt names the kit and says to follow `AGENTS.md`'s workflow for an ordinary change. It does not mention the
  gate, the exception or the expected result.

**Grade** (`nonewf.grade`). It uses only the session transcript's actual tool calls and the runner's final JSON. All
checks must hold.

| Check | NW-1 | NW-2 | NW-3 |
|---|---|---|---|
| G1 sensitivity | NONE | NONE | NONE |
| G2 gate | a Bash call runs `none-gate` on `Program.cs`, and its output has `TARGETED_EXCEPTION web-security` | same | a Bash call runs `none-gate` on `site.css`, and its output has `STOP_NONE` (not an error) |
| G3 order / manifest | the gate call precedes the first `produce_manifest` call | same | no `produce_manifest` call; manifest null |
| G4 manifest | TARGETED, `domains` `["web-security"]`, `MINIMAL`, `scannersSelected` `["semgrep"]` | same | — |
| G5 coverage | `coverageGaps` names semgrep (it is not installed) | same | — |
| G6 scanners | no scanner beyond the selection (trivy, gitleaks, osv-scanner, pip-audit, npm audit, or a full scan script) | same | no scanner at all |
| G7 finding | a CONFIRMED finding naming CSRF on `Program.cs` | no CONFIRMED finding | no findings |
| G8 routing | `plays/finding-validation.md` and the security-gate skill or play were read; `securityGate` is PASS or BLOCK | `securityGate` null or PASS | `securityGate` null |
| G9 report | — | names web-security or CSRF; every blanket "no issues / secure" sentence is scoped to it | no blanket "no issues / secure" claim |

- G6 and G9 are keyword proxies: they can miss a paraphrase and flag an unusual wording. That is recorded, not
  corrected mid-run.

**Validity and stops.** These follow revision 9, rule 7.
- **Technical failure** (`CHANNEL`, `TRANSCRIPT`, `ANSWER_FORMAT`): one retry per case. A case still invalid after
  the retry is `NOT_OBTAINED`.
- **Hard stop**, immediately and not resumed: `CONTEXT` (instruction files in the runner context), `ISOLATION` (a read
  or a Bash path outside the case repository and the kit, or a session that did not start in the case repository),
  `TOOLS`, `MODEL_EFFORT`, `IDENTITY`, `MODIFIED` (the case repository or the kit changed), `LEAKAGE`, or an
  interrupted attempt.
- **A valid but failing answer** is `FAILED`. It is never re-run and never re-graded.

**Result.** B passes only if all three cases are `PASS`.
- If B does not pass, step C does not run.
- An agent that stops at NONE without calling the gate fails G2. CLI tests do not stand in for that.

## Step C — the 52-case validation and four repeats

- **The 52 cases.** Every rule of revision 9 (rules 1–10, 4a, 5a and the Result rule), with the same corpus manifest
  `v4-release-corpus-v5-manifest.json` (`ffab03e8…`) and the same expected-results sources (`2fac68d5…`,
  `b6e6d6a9…`, `320581bc…`). Only the kit (above) and `relman.py`'s product path differ. Base: `final10`.
- **The repeats.** After the 52-case run ends without a hard stop, RV-15, RV-18, RV-29 and RE-08 are each run once
  more.
  - They use the same pins and the same unchanged `caseval.py`, through `caseval_subset.py`, in the base `final10r`.
  - They run even if the 52-case run has `FAILED` cases, so the evidence is complete.
- **Both runs, and each case within them, are reported separately**, with the two results side by side for the four
  repeated cases.
- **Result.** Any valid `FAILED` case in either run, any `NOT_OBTAINED`, or any hard stop makes the release gate
  `NOT_MET`. Nothing is re-run, and no fixture, grader or threshold changes.
- **Limit.** Two runs of four cases and one run of the rest measure no run-to-run stability. This is limited repeat
  evidence only.

## Step D — publication

D runs only if A, B and C and the product gates hold:
- product tests, fallbacks, wrappers, feedback checks;
- the review gate;
- the privacy scan.

Then:
1. Confirm that the remote `v4-release` is still `6f90d0d` and is an ancestor of the new head.
2. Update it by a non-force fast-forward only. No tag, and `v3-slim` is not touched.
3. Prepare the integration with `origin/master` for review. It is never merged automatically.
