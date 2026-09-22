# V3 Slim — Phase 3: Jev Calibration Record

Model: `jev-1.13.0` (requested `jev-latest`). Endpoint:
`https://api.typesafe.ai/v1/systemone`. Two questions asked per pair: a
`choice` classification (`redundant_with_general` / `adds_specificity_same_play`
/ `points_elsewhere`) and a `score` (0=no added value, 1=minor added value,
2=essential added value). Full request/response JSON for all 7 calls is in
the session scratchpad (`v3slim/pair-*.json` + `pair-*.response.json`) — not
copied into the repo since it is working material, not a kit deliverable.

## Results

| Pair | Rows compared | Jev classification (confidence) | Jev score (confidence) |
|---|---|---|---|
| 01 | SQL injection row vs. general injection row | adds_specificity_same_play (0.97) | 1.31 (0.41) |
| 02 | innerHTML row vs. Browser-side row | adds_specificity_same_play (0.99) | 1.12 (0.47) |
| 03 | CORS/cookie/CSP row vs. two general rows | adds_specificity_same_play (0.64) | 0.75 (0.60) |
| 04 | SSRF row vs. APIs/SSRF row | adds_specificity_same_play (0.98) | 0.92 (0.62) |
| 05 | IDOR route-pattern row vs. Authorization row | adds_specificity_same_play (0.94) | 0.77 (0.63) |
| 06 | Hardcoded-crypto row vs. Cryptography row | adds_specificity_same_play (0.99) | 1.00 (0.52) |
| 07 (negative control) | finding-validation row, absent from general table | **points_elsewhere (1.00)** | **1.95 (0.93)** |

## Calibration read

Pair 07 was the one deliberately pre-labeled case in this set: its
destination (`plays/finding-validation.md`) genuinely has no row in
`skills/security-review/SKILL.md`'s coarse table at all, so it should score
as clearly non-redundant. Jev returned the single highest confidence
(1.00 classification, 0.93 score) and highest score (1.95/2) of all 7
calls — it did not conflate "the specific and general rows point to the
same play" with "therefore redundant," which is the exact failure mode this
pilot was checking for.

## Human semantic review (per this plan's own requirement — the score is a lead, not a verdict)

My own prior expectation, before calling Jev, was that pairs 01
(SQL/EF Core) and 06 (crypto) in particular were likely redundant, since
both route to the same play as the general row with no ambiguity (recorded
in `baseline.md`'s fixed-case table, cases 4/5). **Jev's output prompted a
re-check of that expectation, not an override of it** — re-reading the
actual rows:

- `quick-reference.md`'s framing is "if you see this exact code shape, open
  this play" (symptom recognition while reading code line-by-line), whereas
  `SKILL.md`'s coarse table is "if this domain is in scope, open this play"
  (domain-level scoping decided before reading code closely). These are
  different reading tasks even when the destination play is identical — a
  reviewer scanning a diff benefits from "`Random`/`Math.random()` for
  security tokens" as a recognizable trigger in a way that "Cryptography,
  sensitive data" alone does not provide.
- No pair scored at or near 0 (no added value) on either the model's output
  or my own re-reading. The lowest-confidence, lowest-score case (03, CORS)
  is also the one row that legitimately spans two coarse-table destinations
  — the model's own uncertainty tracked a real ambiguity in the row, not
  noise.

**Conclusion for this trial set: none of the 6 sampled "candidate" rows are
safe to delete.** This is a legitimate, useful result of the pilot, not a
failure of it — my initial hypothesis (formed from the redundancy pattern
in `baseline.md`) was wrong for these 6 rows, and the calibration signal
(pair 07's correct high-confidence non-redundant call) is what makes me
trust the "no, don't delete these" reading of pairs 01–06 rather than
dismiss it. No security rule was removed on the basis of a score alone,
per this plan's non-negotiable rule.

## What this does and does not settle

- Settled: the Jev call pipeline works end to end (key handling, request
  format, response parsing), and produces judgments that track a real,
  pre-labeled distinction rather than noise.
- Not settled: whether *any* row in `quick-reference.md`'s remaining 21
  un-sampled rows is a genuine redundancy candidate. This 7-row sample was
  chosen for domain diversity, not to be exhaustive — see `baseline.md`'s
  pilot selection rationale.
