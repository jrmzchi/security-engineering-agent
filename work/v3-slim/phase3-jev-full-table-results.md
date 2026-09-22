# V3 Slim — Full `quick-reference.md` table check (all 21 rows)

Extends the 7-row sample in `phase3-jev-calibration-record.md` to the
complete table, after the TypeSafe API key was rotated (2026-09-22).
Same two questions per row (`classification` choice,
`uniqueness_value` score 0–2); raw request/response JSON in scratchpad
(`v3slim/pair-*.json` + `.response.json`).

| Row (`quick-reference.md` line) | Destination play | Classification (confidence) | Uniqueness score (confidence) |
|---|---|---|---|
| 8 SQL injection | code-review.md | adds_specificity_same_play (0.97) | 1.31 (0.41) |
| 9 process/shell exec | code-review.md | adds_specificity_same_play (0.96) | 1.33 (0.42) |
| 10 template injection | code-review.md | adds_specificity_same_play (0.99) | 1.15 (0.55) |
| 11 innerHTML/XSS sinks | web-security.md | adds_specificity_same_play (0.99) | 1.12 (0.47) |
| 12 CORS/cookies/CSP | web-security.md **or** configuration-security.md | adds_specificity_same_play (0.64) | 0.75 (0.60) |
| 13 postMessage | web-security.md | adds_specificity_same_play (0.98) | 0.76 (0.54) |
| 14 open redirect | web-security.md | adds_specificity_same_play (0.98) | 1.10 (0.39) |
| 15 X-Frame-Options | web-security.md | adds_specificity_same_play (0.99) | 0.91 (0.52) |
| 16 XXE | api-security.md | adds_specificity_same_play (0.98) | 0.80 (0.40) |
| 17 SSRF | api-security.md | adds_specificity_same_play (0.98) | 0.92 (0.62) |
| 18 deserialization | api-security.md | adds_specificity_same_play (0.97) | 0.75 (0.42) |
| 19 mass assignment | api-security.md | adds_specificity_same_play (0.94) | 0.76 (0.52) |
| 20 IDOR/BOLA routes | authorization.md | adds_specificity_same_play (0.94) | 0.77 (0.63) |
| 21 login/session/JWT | authentication.md | adds_specificity_same_play (0.95) | 0.74 (0.57) |
| 22 [Authorize]/roles | authorization.md | adds_specificity_same_play (0.94) | **0.63 (0.38)** — lowest of all 21, but still majority-weighted to "minor value" (0/1/2 probs: 0.39/0.59/0.02) |
| 23 hardcoded crypto | data-security.md | adds_specificity_same_play (0.99) | 1.00 (0.52) |
| 24 file upload/download | file-security.md | adds_specificity_same_play (0.99) | 1.18 (0.49) |
| 25 dependency files changed | dependency-security.md | adds_specificity_same_play (0.93) | 0.90 (0.69) |
| 26 secrets in code/config | secrets-security.md | adds_specificity_same_play (0.94) | 0.88 (0.73) |
| 27 debug/config exposure | configuration-security.md | adds_specificity_same_play (0.99) | 1.18 (0.46) |
| 28 (negative control) HIGH/CRITICAL needs validation | finding-validation.md (absent from coarse table) | **points_elsewhere (1.00)** | **1.95 (0.93)** — highest of all 21 |

## Reading across the full table (not just the earlier 7-row sample)

- **0 of 21 rows classified as `redundant_with_general`** as the top choice.
  Every single row — not just the earlier sample — comes back
  `adds_specificity_same_play`, except the deliberate negative control,
  which correctly comes back `points_elsewhere` with the highest confidence
  of the entire batch.
- **0 of 21 rows scored near 0** on uniqueness (closest is row 22 at 0.63,
  and even there the probability mass sits mostly on "minor value," not
  "no value").
- Row 12 (CORS, spanning two coarse-table destinations) remains the single
  lowest-confidence *classification* call (0.64) — consistent with the
  7-row sample's finding that this is a genuinely ambiguous row, not noise.
- Row 22 (`[Authorize]`/role checks) is the closest thing to a borderline
  case in the whole table: lowest uniqueness score (0.63) and lowest score
  confidence (0.38) of all 21. Worth a closer human look specifically, since
  "closest to redundant" is a meaningfully different claim from "actually
  redundant" — see below.

## Human semantic check on the one borderline row (22)

`[Authorize]/role/policy checks, or their absence -> plays/authorization.md`
vs. the coarse table's `Authorization / IDOR / BOLA -> plays/authorization.md`.
Re-reading both: the coarse row's parenthetical already names IDOR/BOLA
specifically, and row 22 adds the *mechanism* (`[Authorize]` attribute,
role/policy checks) rather than the *vulnerability class* — genuinely closer
to the general row's own wording than any other row in the table, which is
consistent with it scoring lowest. But it is still a different piece of
information (a mechanism cue vs. a vulnerability-class cue), and a reviewer
scanning for a missing `[Authorize]` attribute benefits from the mechanism
being named explicitly rather than inferring it from "Authorization." Not
recommending removal even for this one — same conclusion as the rest of the
table, on weaker but still real grounds.

## Conclusion

This is now an exhaustive check of `skills/security-review/references/quick-reference.md`'s
entire table (21/21 rows), not a sample. **No row is a safe deletion
candidate.** The table's actual function, confirmed both by the model and
by human re-reading, is closer to "21 independently useful recognition
cues that happen to share destinations with a 9-row domain index" than
"9 rows duplicated into 21." This is a stronger, more conclusive version of
the sampled finding already recorded in `results.md`.
