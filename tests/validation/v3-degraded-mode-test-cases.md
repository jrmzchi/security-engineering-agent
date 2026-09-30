# V3 Degraded Mode Test Cases

Validates `skills/security-review/SKILL.md`'s steps 2-3 fallback
behavior when `.security/baseline.json` and `.security/attack-surface.json`
do not exist (or are stale) for the repository under review — the review
must still reach a correct result using direct code evidence, not skip
or silently weaken anything. No dedicated case existed for this before
2026-09-22; this file was added specifically to close that gap rather
than continuing to rely on reasoning over unchanged text alone.

## Case 1: file-download path traversal, no `.security/` present at all

**Version under test**: `v3-slim` branch, commit `6cb995d` and later
(the relevant files — `skills/security-review/SKILL.md` steps 2-3,
`plays/file-security.md`, `plays/cross-file-data-flow.md`,
`plays/finding-validation.md` — are byte-identical to V3 Final commit
`0ffd18ec8af3651af48a4f6187cdadd516045be1`, confirmed via `git diff`
before running this case, so the result applies equally to both).

**Input**: `tests/fixtures/cross_file_path_traversal_unsafe/`
(`DownloadController.cs`, `FileService.cs`, `PathHelper.cs`), treated as
the target repository under review. Confirmed before running the case
that no `.security/` directory exists anywhere in this repository
(`find . -iname ".security"` — zero results) — this is a naturally
occurring degraded-mode condition, not a simulated one.

**Expected result** (per `skills/security-review/SKILL.md` steps 2-3):
since neither `.security/baseline.json` nor `.security/attack-surface.json`
exists, the review must fall back to discovering architecture and attack
surface directly from source ("rediscovering... from scratch" / "same
freshness caveat as step 2's baseline") rather than skip these steps or
produce a weaker result — and must still reach the same CONFIRMED
finding this fixture group produces under `tests/validation/v3-cross-file-test-cases.md`'s
cases 3-4 (which assume no particular baseline state either way).

**Actual result** (executed 2026-09-22, without consulting any
baseline/map — none exists to consult):

| Step | What was actually done | Finding |
|---|---|---|
| 2. Architecture discovery | Read all 3 files directly (no baseline to consult). Identified: C#/ASP.NET Core (`Microsoft.AspNetCore.Mvc`, `[ApiController]`/`[HttpGet]`), entry point `DownloadController.Download` at `GET /reports/download`, trust boundary at the HTTP request boundary | — |
| 3. Attack surface identification | Read `DownloadController.cs` directly (no map to consult): `reportName` is a `[FromQuery]` parameter, attacker-controlled, no upstream validation visible | — |
| 5. Manual semantic analysis | Domain recognized directly from code ("file download + path building from user input") without a baseline/map telling us which domain applies — routes to `plays/file-security.md` and `plays/cross-file-data-flow.md`'s multi-hop procedure the same way it would with a map present. Traced: `reportName` (Controller, unvalidated) -> `FileService.GetReportBytes` (unvalidated) -> `PathHelper.ResolveReportPath` (uncontained `Path.Combine`, no canonicalization) -> `File.ReadAllBytes` sink | CONFIRMED HIGH/CRITICAL path traversal (CWE-22) |

**Result: PASS.** The degraded-mode trace reaches the identical
CONFIRMED HIGH/CRITICAL outcome as the normal-mode trace of the same
fixture (`v3-cross-file-test-cases.md` cases 3-4, executed in the same
verification pass) — confirming the fallback does not under-detect
relative to the baseline-assisted path. Validation (`skills/security-validate`,
mandatory for HIGH/CRITICAL regardless of baseline/map state) was not
itself re-executed as a separate step here since `agents/security-validator.md`
is confirmed unconditional and byte-identical to V3 Final; this case
tests steps 2-3's fallback specifically, not the full pipeline end to
end.

## What this does not test

Does not test a *stale* (as opposed to *absent*) baseline/map — that is
a different scenario (`plays/security-impact-analysis.md`'s incremental
invalidation, already covered by `tests/validation/v3-freshness-test-cases.md`).
Does not test degraded mode for `project-security-baseline`/`attack-surface-map`
themselves (those skills' own job is to *build* the artifact this case
assumes is simply absent, not to degrade gracefully without one).
