# V3 Adversarial Validation Test Cases

Validates `plays/adversarial-validation.md`'s checklist and structured
result metadata. See `tests/validation/README.md` for how to run a
validation pass. Every case below has both a positive (bypass exists)
and negative (control genuinely holds) counterpart on purpose, in the
spirit of that play's "A different objective from ordinary validation,
not more of the same" section: a checklist that only ever reports
`BYPASS_FOUND` has not been validated for false-positive avoidance any
more than one that only ever reports `CONTROL_HOLDS` has been
validated for false-negative avoidance.

## Bypass / control-holds pair

| # | Fixture | Trigger reason (from the trigger list) | Expected `adversarialValidation` result | Expected underlying finding/remediation status |
|---|---|---|---|---|
| 1 | `tests/fixtures/path_prefix_before_canonicalization_deceptive.cs` | "Path traversal with a canonicalization control" | `BYPASS_FOUND` | `CONFIRMED` — see `tests/validation/v3-cross-file-test-cases.md` case 7 for the full attack path |
| 2 | `tests/fixtures/path_prefix_after_canonicalization_safe.cs` | Same category, structurally similar control | `CONTROL_HOLDS` | No confirmed finding — see `tests/validation/v3-cross-file-test-cases.md` case 8 |

Case 2 is the more important of the two to get right in practice:
`BYPASS_FOUND` findings get caught by ordinary review even without
this checklist (the underlying vulnerability is still there to find).
A checklist that reports `BYPASS_FOUND` on case 2 has actively
produced a false positive that ordinary review would not have — the
harm is specific to this capability, not a pre-existing gap it failed
to close.

## Remediation fake-fix, with structured result

Existing pair: `tests/fixtures/remediation_fake_fix_before.py` /
`remediation_fake_fix_after_still_vulnerable.py` (see
`tests/validation/expected-results.md` and
`plays/security-remediation.md`'s "Fake fix" section for the base
case). This capability adds the structured
`adversarialValidation` field on top of the existing
`STILL_VULNERABLE` result — it does not change what the base case
already validates.

| Step | What happens | Expected `adversarialValidation` result | Expected `Result` (per `plays/security-remediation.md`) |
|---|---|---|---|
| Re-validate the "after" file with only the original payload (`' OR '1'='1`) | The fake fix's literal-string blocklist catches it — looks fixed | Not applicable at this step — this is the failure mode the checklist exists to prevent, not a correct application of it | Would incorrectly report `RESOLVED` if stopped here |
| Apply `plays/adversarial-validation.md`'s technique 4 (alternate representations) — retry with a different payload targeting the same root cause, e.g. `y' OR 'a'='a` or a UNION-based payload | The underlying string-concatenated query is still present; the new payload is not blocked | `FIX_BYPASSED` — this tag *supports* the Result column, per that play's "Structured result metadata": no value in that field ever decides the outcome by itself, so the actual `STILL_VULNERABLE` determination is the re-validation pass's own, using "Results use existing vocabulary, not a new one" above it (this fixture has no legitimate-functionality regression, so `REGRESSION_INTRODUCED` does not apply here — it would if the fix had also broken something) | `STILL_VULNERABLE`, never `RESOLVED` for this specific bypass |

Expected review outcome: a validator that only re-tests the original
payload reports `RESOLVED` and never invokes this checklist at all —
that is the false-assurance failure mode
`plays/security-remediation.md`'s "Independent re-validation" section
already exists to prevent, and is not this checklist's job to catch
retroactively. A validator that correctly identifies this as a
HIGH/CRITICAL remediation (mandatory-by-default trigger, per
`plays/adversarial-validation.md`'s trigger list) and applies the
checklist must reach `FIX_BYPASSED` / `STILL_VULNERABLE`, using a
payload other than the one literally blocklisted.

## What this document does not duplicate

The full ten-technique checklist, the four structured-result values per
carrier (finding/remediation/chain) and their exact non-deterministic
semantics, and the trigger list itself are authoritative in
`plays/adversarial-validation.md` — this document only maps this kit's
existing fixtures onto them for validation purposes. If a technique or
value's meaning is unclear from a case above, the play is the source
of truth, not this table.
