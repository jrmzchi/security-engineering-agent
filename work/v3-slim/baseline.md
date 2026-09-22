# V3 Slim — Phase 1: V3 Full Baseline

Baseline commit: `0ffd18ec8af3651af48a4f6187cdadd516045be1` (see
`phase0-baseline-record.md` for how this was confirmed). Full per-file line
counts: `full-linecounts.tsv` in this directory.

## Golden / validation coverage actually present (verified by listing, not assumed)

| Capability named in prior sessions | Actual artifact in this repo |
|---|---|
| cross-file SQL / path traversal / object authorization | `tests/validation/v3-cross-file-test-cases.md` + `tests/fixtures/cross_file_*` |
| attack chain | `tests/validation/v3-attack-chain-test-cases.md` |
| adversarial validation | `tests/validation/v3-adversarial-test-cases.md` + `tests/fixtures/path_prefix_*` |
| freshness / incremental impact | `tests/validation/v3-freshness-test-cases.md` (covers both) |
| review budget | `tests/validation/v3-review-budget-test-cases.md` |
| scanner selection (domain-driven tool selection) | `tests/validation/classification-test-cases.md`'s "Domain selection cases" section (no separate dedicated file) |
| security-change-detection classification | `tests/validation/classification-test-cases.md` |
| security-design activation routing | `tests/validation/design-routing-test-cases.md` |
| security gate | `tests/validation/gate-test-cases.md` |
| repository consistency | `scripts/*/consistency-check.*` — this ONE is actually executable/automated; already run this session (21 hits, all reviewed, none required a fix) |
| **degraded mode** | **No dedicated test file exists.** Only prose in `skills/security-review/SKILL.md` steps 2–3 (freshness-gated fallback). Not independently re-verified with fresh evidence in this pass — flagged as a gap, not silently assumed covered. |

None of the Markdown-based ones have a pass/fail exit code — see
`phase0-baseline-record.md` for why "running the golden tests" here means
manual per-case comparison against each file's Expected column, not a test
runner invocation.

## Fixed-case routing & context measurement (current, pre-slim, state)

Traced by hand against `plays/security-change-detection.md`'s sensitivity
levels, `skills/security-review/SKILL.md`'s "Where to look next" coarse
table (9 domain rows), and
`skills/security-review/references/quick-reference.md`'s fine-grained
21-row symptom table — the exact pair this pilot targets. Line counts from
`full-linecounts.tsv`. Classifier overhead (`skills/security-change-detection/SKILL.md`
57 + `plays/security-change-detection.md` 159 = 216 lines) is constant across
every case and every column below, so it is excluded from the per-case
totals to keep the comparison meaningful — it is not something this pilot
touches.

| # | Fixed case | Sensitivity | Coarse-table route (play + reference) | Coarse-table lines | Fine-table (`quick-reference.md`) row | Fine-table alone: same, less, or more coverage? |
|---|---|---|---|---|---|---|
| 1 | CSS color change | NONE | — (no workflow) | 0 | no matching row (correctly absent) | same (both correctly load nothing) |
| 2 | Remove `[Authorize]` from an ASP.NET controller | HIGH | `plays/authorization.md` (98) + `references/aspnet-security.md` (149) | 247 | line 22: `[Authorize]/role/policy checks... -> plays/authorization.md` | **less** — fine table names the play but never names a reference; the reference still has to come from the coarse table's "Then reference" column |
| 3 | Authenticated file-download endpoint, user-supplied filename | HIGH | `plays/file-security.md` (155) + `references/aspnet-security.md` (149) + `references/windows-security.md` (117, deployment OS) + `plays/authorization.md` (98, object-level access) | 519 | line 24: `File upload/download... -> plays/file-security.md` only | **less** — misses the authorization angle (98 lines) and the OS reference (117 lines) entirely; relying on the fine row alone would under-load by 215 lines |
| 4 | New EF Core query for an existing, already-authorized report | MODERATE | `plays/code-review.md` (149, general injection section) + `references/dotnet-security.md` (150) | 299 | line 8: `String-concatenated SQL, FromSqlRaw/ExecuteSqlRaw... -> plays/code-review.md (injection section), then stack reference` | **same destination as the general row** — candidate for redundancy (this is `pair-01-sql` in the Jev trial set) |
| 5 | New dependency added to `package.json` | MODERATE | `plays/dependency-security.md` (83) | 83 | line 25: `package.json/requirements.txt/*.csproj/lockfiles changed -> plays/dependency-security.md` | **same destination as the general row** — candidate for redundancy |
| 6 | Authentication middleware registration change (`AddAuthentication`/`UseAuthentication`) | HIGH | `plays/authentication.md` (94) + `references/aspnet-security.md` (149) | 243 | **no matching row** — closest is line 21 (login/session/cookie/JWT), which is about flow content, not middleware registration | **less** — a reviewer using only the fine table might not recognize this code as matching any row at all; the coarse table's domain-level row is what actually guarantees this gets caught |

## What this baseline already shows (evidence, not yet a decision)

- In every one of the 6 fixed cases, `quick-reference.md` never adds a routing
  destination the coarse table doesn't already have — in cases 4 and 5 it is a
  literal duplicate of the general row; in cases 2, 3, and 6 it is
  *incomplete* relative to the coarse table (missing the reference column
  entirely, and in case 3 also missing a whole second concern).
- This means `quick-reference.md`'s actual role, evidenced by these 6 cases,
  is "fast pattern-recognition aid for a few specific code shapes," not an
  independent or more complete routing source — matching
  `skills/security-review/SKILL.md:136`'s own framing of it as a supplement
  ("See ... for a flat lookup table"), not a replacement.
- This does **not** by itself mean any row should be deleted — cases 2/3/6
  show the file's 21 rows are not uniformly redundant; the row at line 28
  (`A candidate is HIGH/CRITICAL... -> plays/finding-validation.md`,
  the pilot's deliberate negative control) has a destination the coarse
  table doesn't cover *at all*, and row 12 (CORS) legitimately spans two
  coarse-table rows. Phase 2/3 need to go row-by-row, not conclude "delete
  the file" from this aggregate pattern.

## Not yet done in Phase 1

- Full regression walk of the other `tests/validation/v3-*.md` files against
  current `master` — not needed yet since this pilot has not changed
  anything; will be re-run in Phase 4 against whatever files this pilot
  actually touches, per the plan's own "跑相關測試及完整 golden/regression 套件"
  requirement.
- Degraded-mode fresh verification (flagged as a gap above, inherited from
  the earlier V3 Finalization Report, not something this pilot introduces).
