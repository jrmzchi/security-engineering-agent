# Security Gate Test Cases

Validates `skills/security-gate` / `plays/security-gate.md`'s policy
table and precedence rules deterministically — unlike most of this
kit's validation, these inputs are already-determined finding statuses
(not code to review), so the expected outcome is a mechanical lookup,
not a judgment call. A reviewer that gets any of these wrong has a bug
in gate logic, not a difference of security opinion.

| # | Input finding(s) | Expected outcome |
|---|---|---|
| 1 | One CONFIRMED CRITICAL | BLOCK |
| 2 | One CONFIRMED HIGH | BLOCK |
| 3 | One HIGH candidate, not yet validated | AWAITING_VALIDATION |
| 4 | One HIGH candidate, validated, result NEEDS_VERIFICATION | BLOCK |
| 5 | One CONFIRMED MEDIUM | PASS_WITH_WARNINGS |
| 6 | One CONFIRMED LOW | PASS_WITH_WARNINGS |
| 7 | One INFORMATIONAL finding only | PASS |
| 8 | One REJECTED finding only | PASS (REJECTED is excluded from gating entirely — see `plays/security-gate.md`'s "Outcomes") |
| 9 | No findings at all | PASS (if the gate is invoked at all; per `plays/security-gate.md`'s "When this runs", a NONE/LOW change with zero findings typically has nothing to gate and the gate step is skipped in practice) |
| 10 | One CONFIRMED HIGH with explicit user risk acceptance | PASS_WITH_ACCEPTED_RISK |
| 11 | One CONFIRMED HIGH + three non-BLOCK-level (INFORMATIONAL/LOW/MEDIUM) findings in the same batch | BLOCK (precedence, not majority — see `plays/security-gate.md`'s worked examples) |
| 12 | One CONFIRMED HIGH with risk acceptance + one CONFIRMED MEDIUM with no acceptance, same batch | PASS_WITH_ACCEPTED_RISK (still outranks PASS_WITH_WARNINGS in precedence) |
| 13 | One HIGH candidate not yet validated + one CONFIRMED MEDIUM, same batch | AWAITING_VALIDATION (outranks PASS_WITH_WARNINGS) |
| 14 | A remediation's independent re-validation result: RESOLVED | Re-apply the table without that finding (typically PASS, or whatever the rest of the batch resolves to) |
| 15 | A remediation's independent re-validation result: STILL_VULNERABLE | BLOCK (unchanged — see `remediation_fake_fix_after_still_vulnerable.py`) |
| 16 | A remediation's independent re-validation result: FIX_UNVERIFIED | BLOCK (same treatment as case 4) |
| 17 | A remediation's independent re-validation result: REGRESSION_INTRODUCED | The new issue gates as its own candidate, in addition to the original finding's status — see `plays/security-gate.md`'s "After a remediation attempt" |

Cases 1–9 exercise the default policy table directly. Case 10 exercises
risk-acceptance handling; cases 11–13 exercise precedence/aggregation
across a batch. Cases 14–17 exercise the remediation-outcome mapping.
If a reviewer gets case 4 or 16 wrong
(treating an unresolved HIGH/CRITICAL as safe), that is the specific
failure mode `plays/security-gate.md`'s "Handling an unresolved
HIGH/CRITICAL candidate" section exists to prevent — treat it as a
priority fix, not a minor scoring miss.
