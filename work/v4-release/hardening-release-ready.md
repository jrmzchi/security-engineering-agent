# V4 release hardening: revision 11 result (2026-09-30)

**STATUS: `V4_RELEASE_READY` by the pre-registered result rule of revision 11**
(`hardening-validation-protocol-r11.md`, run commit `e8f1636`, kit `3527fa0b…` of `202d3df`).

This is **not** a claim of run-to-run stability, and not a code-enforced guarantee that an agent calls the NONE gate.

**Earlier records, unchanged:**
- `hardening-release-status.md` (`STOPPED_AT_A` and its three CLI reproductions);
- `hardening-round3-status.md` (revision 10: NW-1 and NW-2 `FAILED`, NW-3 a hard stop);
- revision 9's 52 of 52 for the published `6f90d0d` / kit `812115b5…`.

## Evidence, kept apart

| Evidence | Version | Result |
|---|---|---|
| Revision 9, 52 cases, one run each | published `6f90d0d`, kit `812115b5…` | 52 of 52 (historical; not evidence for this kit) |
| Revision 10 step B, NONE workflow | kit `27fff648…` | NW-1 `FAILED`, NW-2 `FAILED` (no `produce_manifest()`), NW-3 hard stop (a harness defect). Kept as recorded |
| **Revision 11 step B**, NONE workflow, one run each | kit `3527fa0b…` | **NW-1, NW-2, NW-3 all PASS**; 3 valid runs, 0 invalid, no hard stop |
| **Revision 11 step C**, 52 cases (39 V3 corpus + 13 enterprise identity), one run each | kit `3527fa0b…` | **52 PASS**, 0 FAILED, 0 NOT_OBTAINED; 104 model runs, 0 invalid, 1 result-tool call rejected and corrected by the runner, 0 outside reads, no hard stop |
| **Revision 11 repeats**, the same pins | kit `3527fa0b…` | 4 PASS (8 runs, 0 invalid) |

**Repeats, side by side:**

| Case | Expected | 52-case run | Repeat |
|---|---|---|---|
| RV-15 | no CONFIRMED | PASS (`NOT_CONFIRMED`) | PASS (`NOT_CONFIRMED`) |
| RV-18 | CONFIRMED | PASS (`CONFIRMED`) | PASS (`CONFIRMED`) |
| RV-29 | CONFIRMED ×3 | PASS (`CONFIRMED` ×3) | PASS (`CONFIRMED` ×3) |
| RE-08 | no CONFIRMED | PASS (`NOT_CONFIRMED`) | PASS (`NOT_CONFIRMED`) |

**What step B's tool records show.** From the transcripts, per case:
- **NW-1 / NW-2:** the agent ran `none-gate`, received `TARGETED_EXCEPTION web-security` and the gate-built manifest,
  used that manifest unchanged (`semgrep`, `MINIMAL`), and read `plays/web-security.md` in full after the gate.
  - NW-1 then read `plays/finding-validation.md` and the security-gate play in full, reported the CSRF as CONFIRMED,
    and gated it BLOCK.
  - NW-2 reported no CONFIRMED finding, limited to web-security.
- **NW-3:** the agent ran the gate, received `STOP_NONE`, and stopped with no manifest, scanner or summary.

**Product gates on the run commit:**
- context_manifest 349 OK, on both interpreters; feedback_store 354 OK (2 skipped);
- 25 product mutants and 6 harness mutants killed;
- offline fallbacks A/D/E/F built-in, with the floor kept;
- 9 feedback scenarios as before;
- wrappers (PS 5.1 / PS 7 / Bash): 23 hits each; exit 2 without Python;
- 52-case gate fire set unchanged;
- privacy scan of `origin/v4-release..HEAD`: 0 new hits; the only hits are inherited, already-published ones.

**Reviews:**
- policy round (`6ed245f`): adoptable;
- revision-11 product and grader (`d469607` + `rel11/nonewf.py`): no Blocker or Major; its Minor fixed in `202d3df`.

## Security gaps closed, and limits that remain

**Closed:**
- The NONE stop has a code check. `STOP_NONE` requires every file to be read and to be plain UTF-8, and no signal
  pair.
- Unreliable encodings never stop at NONE.
- On the exception, the gate builds and validates the manifest itself, and the documents forbid hand-written
  manifests.
- The exception's reporting is defined: web-security only, MINIMAL, the manifest's scanners with gaps recorded, and a
  finding goes through finding-validation and then security-gate.

**Remaining:**
- Nothing in code forces an agent to call the gate. Step B observed it in 3 of 3 cases, one run each.
- The floor's documented pattern misses, plus 7-bit encodings (UTF-7, ISO-2022-*), which count as plain UTF-8.
- Binary, UTF-16/32 and legacy-encoded files go to the manual check. This is the deliberate cost.
- Every model result is one run per case, except the four repeats. That is limited evidence, not stability.
- The grader proxies recorded in revision 11: G3 cannot tell a copied manifest from an identical rebuild; G6 and G9
  are keyword checks.
