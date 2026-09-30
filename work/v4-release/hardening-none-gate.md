# V4 release hardening: the NONE gate and the signal-pair exception's reporting (2026-09-30)

**Status:** implemented on the local branch `v4-release-hardening`. Not published, not merged, no tag.
It closes the two Minors recorded in `followup-targeted-none-floor.md`, as far as code can; see "What is closed and
what is not".

**Starting state:**
- The published `origin/v4-release` is at `6f90d0d`, with a clean tree.
- `v4-release-hardening` was created from it with no upstream.
- The published branch itself was not modified.

## What changed

1. **The NONE gate** (Minor 1):
   - **The code entry.** `tools/context_manifest/none_gate.py` and `python -m tools.context_manifest.cli none-gate --root <repository root> <file>...`, run from the kit's root
     (the kit may sit apart from the repository under review).
   - **What it checks.** It reads the change's files — whole files, as they are after the change. It calls
     `signal_floor.required_domains()` on their texts before it can return `STOP_NONE`.
   - **Results:**
     - `STOP_NONE` (exit 0) when no pair is present;
     - `TARGETED_EXCEPTION <domain>` (exit 1) when both signals are present;
     - `MANUAL_CHECK` (exit 2) when a file is missing or unreadable, no files are given, an argument is bad, or the
       floor raised.
   - **Unread files are reported separately:** as `unread:` lines, so the exception's report lists them as not
     covered.
   - **Other encodings** (Unicode round, below). A file with NUL bytes is also read as UTF-16 LE/BE and UTF-32 LE/BE
     at every alignment, whatever its BOM says, plus each reading with non-ASCII characters replaced by spaces.
     A file with a UTF-16/32 BOM its encoding cannot decode, a NUL-bearing file no UTF-16/32 decoding accepts
     (a binary file, for example), or a NUL-bearing file over 1 MiB, is reported as `unread` ("cannot be decoded
     reliably"): MANUAL_CHECK, never STOP_NONE.
   - **Exit 0 is only ever STOP_NONE.** A crash inside the command is exit 2. An interpreter that cannot import the
     package exits 1, and the documents accept exit 1 only *with* the `TARGETED_EXCEPTION` line. So every failure
     lands on "do not stop at NONE".
   - **The documents** (workflow NONE row, change-detection NONE action, both SKILLs, review-budget, `AGENTS.md`,
     `CLAUDE.md`, both integrations) now require the gate before every NONE stop. They also give a manual check for
     when it cannot run: read the files for both halves; both found → the exception; otherwise stop, and say in
     one line that the gate did not run, why, and what the manual check found.
2. **The exception's reporting** (Minor 2). Stated in full in the change-detection NONE action, and pointed to
   everywhere else:
   - the pair's domain only: its play, no design step, MINIMAL;
   - the manifest's `scannersSelected` for that domain and no other scanner; an unavailable or failed scanner goes
     to `coverageGaps`;
   - a finding → `plays/finding-validation.md` → `skills/security-gate`, and it is reported;
   - no finding → one line naming the check, the files and the result, and nothing about other domains.
   - "No security theater" and the workflow's completion-summary line now carry this exception where the
     unconditional rule stands.

**Scope decision** (the follow-up's open question): whole files, not the diff.
- It matches the floor's existing definition and is the conservative direction.
- The cost: it can fire for a comment-only change to a file that already holds the pair, which means one play read.

## What is closed and what is not

- **Closed in code:** a NONE decision that goes through the gate cannot stop without the floor having run on every
  given file's text, and no failure inside the gate yields a NONE stop.
- **Not closed, and not claimable:** that the agent calls the gate. The workflow is Markdown the agent follows;
  nothing in code can force an agent that skips both the gate and the manual check. The documents and
  `none_gate.py` say so.
- **Unchanged:** the floor's patterns and their known misses (listed in `signal_floor.py`). A pair written some
  other way still depends on item 0 or on the agent noticing it.

## Impact against the published `v4-release` (`6f90d0d`)

| File | +/− | Behaviour impact |
|---|---|---|
| `tools/context_manifest/none_gate.py` | +115 | New module. Nothing else imports it except the CLI. |
| `tools/context_manifest/cli.py` | +41/−3 | New `none-gate` command. `scope-coverage-check` is unchanged: its handler still takes no arguments, and extra arguments are ignored as before. The consistency-check output is identical to the base tree. |
| `tools/context_manifest/signal_floor.py` | +2/−1 | Docstring only. |
| `tools/context_manifest/tests/test_release_none_gate.py` | +348 | 27 new tests. |
| `tools/README.md` | +8/−7 | The CLI is no longer described as consistency-check only. |
| `plays/security-change-detection.md` | +49 | The gate step, the manual check, the exception's reporting, and the "No security theater" exception. |
| `plays/secure-development-workflow.md` | +14/−1 | The NONE row requires the gate. The completion-summary line points to the NONE action. |
| `skills/security-change-detection/SKILL.md` | +7 | Pointer: NONE stops only after the gate. |
| `skills/security-review/SKILL.md` | +6 | Step 1: on the exception path, `scope_texts` are the gate's files, and the reporting is limited to that domain. |
| `plays/review-budget.md` | +4/−1 | The note points at the gate. |
| `AGENTS.md`, `CLAUDE.md` | +2, +3/−2 | Routing pointers. `CLAUDE.md`'s wording Nit is fixed: it now names the play. |
| `integrations/claude/agents/security-change-detection.md` | +3/−1 | This read-only subagent cannot run the gate; its NONE result is not a stop. |
| `integrations/codex/README.md` | +2/−1 | A NONE result stops only after the gate. |

**What did not change:**
- `orchestrator.py`, `producer.py`, `validator.py` and the budget code;
- every fixture, validation manifest and expected result;
- the feedback store, the scripts and the protocol.

**The kit export changed:** `812115b5…` → `5828991e…`, computed with the same export function the revision-9
protocol pins. Re-exporting `6f90d0d` reproduces `812115b5…`.

## Evidence, kept apart

**The published version** (`6f90d0d`, kit `812115b5…`):
- revision 9's 52 of 52, one model run per case (`v4-release-report.md` §18);
- it applies to that kit only. **It has not been run on this version**, and it is not evidence for it.

**This version** (kit `5828991e…` (superseded: the current product's kit is `cd838128…`, see `hardening-release-status.md`)), all deterministic, with no model call and no network:
- context_manifest 325 OK (298 unchanged + 27 new); feedback_store 354 OK (2 skipped);
- 12 mutants on the gate, the CLI and the documents, all killed;
- consistency-check identical to the base tree (23 hits);
- **one integration pass over the 52 validation cases.** Each case's files were run through the real CLI in a
  separate interpreter, on the raw files and on the comment-stripped texts:
  - both fire sets equal revision 9's recorded one {RV-18, RV-28, RE-09, RE-10, RE-11};
  - no MANUAL_CHECK occurred;
  - each exception produced a valid TARGETED manifest with `domains ["web-security"]`, `MINIMAL`, `semgrep`, and no
    gaps.
  This shows the gate decides as the floor did. **It is not a review-quality result:** no model reviewed anything.

## Independent review

**Round 1** (`6f90d0d..f3f4ac2`): not adoptable as it stood.
- **Major:** UTF-16/UTF-32 files hid the pair, and the gate returned STOP_NONE.
- **Minors:**
  - the workflow row accepted a bare exit 1;
  - unread files were not reported separately on the exception;
  - `tools/README.md` was stale;
  - no test put a signal late in a large file.
- **Nit:** two "runs before any NONE stop" statements.
- **Open question:** the invocation directory, since the kit may sit apart from the reviewed repository.

All of these were fixed in `634f77e`. The open question was settled as "run from the kit's root with
`--root <repository root>`", which holds for either layout.

**Fix-only re-review** (`f3f4ac2..634f77e`): adoptable.
- The Major is closed for all eight UTF-16/32 variants (both byte orders, with and without BOM) when the text around
  the signals is ASCII.
- No new STOP_NONE path and no crash path.
- `unread` is carried on every branch.
- The documents are consistent.

**Recorded after that round:**
- **Minor:** in a UTF-16/32 file, a non-ASCII character whose code unit contains the byte `0x22` or `0x27` became a
  quote once the NULs were removed, so the gate returned STOP_NONE. Examples: 丢 (U+4E22) and − (U+2212).
  This was closed by the Unicode round below.
- **Nit:** `tools/README.md` says `none-gate` "is run by the reviewing agent before a NONE stop"; it should say it
  is required. Still open.

**Unicode round** (user-authorized, 2026-09-30; one fix round, then one fix-only re-review):
- `67d6d29`: decoding by BOM and byte order.
- Its independent review found:
  - **Major:** a regression. A BOM that disagrees with the content, or a BOM file holding segments in another byte
    order or width, gave STOP_NONE, because the BOM narrowed the readings.
  - **Minor:** in mixed-encoding files, a wrong-alignment neighbour glued itself to a `\b` signal.
  - **Minor:** no test covered the UTF-32 alignments or the BOM mismatch.
  - **Minor:** this record was stale.
- The single fix round:
  - every NUL-bearing file gets all readings, whatever its BOM;
  - every reading also gets an ASCII projection;
  - a 1 MiB cap on NUL-bearing files, above which the result is MANUAL_CHECK.
- Measured on the fixed code:
  - 40 regression tests (every construction the review found, all UTF-32 alignments, the cap);
  - 22 mutants killed;
  - a mixed-encoding sweep of 37,982 files that hold the pair (random byte order, width, BOM and junk bytes between
    newline-bounded segments): **0 wrong STOP_NONE**. The same sweep finds 7,426 on `67d6d29`, so it can detect the
    fault.
- **Fix-only re-review of `b4f6864`:** every earlier construction is closed and the commit adds no new code defect, but one wrong-STOP_NONE path remains: an encoding switch in the middle of a line, next to a signal. It was reproduced through the CLI. Per the user's rule, the release stops here; see `hardening-release-status.md`.

## Release validation this version still needs

- **A new, pre-registered model validation on kit `5828991e…` (superseded: the current product's kit is `cd838128…`, see `hardening-release-status.md`).** The 52-case corpus plus enterprise identity, pins
  re-taken, before any claim that this version is release-ready.
  - The validation builds every manifest in STANDARD mode, so it never reaches the NONE path.
  - It re-checks that the guidance changes did not move any existing row.
- **Optionally, a NONE-path case,** where the review agent must itself decide NONE and meet the gate. That would
  measure whether agents actually call the gate, the part code cannot guarantee. It is not in the current corpus
  and would need its own pre-registration.
- **No stability claim either way:** one run per case measures no run-to-run stability.
