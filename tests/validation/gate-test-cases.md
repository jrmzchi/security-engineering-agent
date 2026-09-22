# Security Gate Test Cases

Validates `skills/security-gate` / `plays/security-gate.md`'s policy
table and precedence rules deterministically — unlike most of this
kit's validation, these inputs are already-determined finding statuses
(not code to review), so the expected outcome is a mechanical lookup,
not a judgment call. A reviewer that gets any of these wrong has a bug
in gate logic, not a difference of security opinion.

| # | Input finding(s) or chain record | Expected outcome |
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
| 18 | A `plays/attack-chain-analysis.md` chain record, CRITICAL severity, HIGH confidence, built from two CONFIRMED MEDIUM component findings (neither BLOCK-eligible alone) | BLOCK (chain severity is an independent input, not derived from component severities — see `plays/security-gate.md`'s "Inputs this play consumes") |
| 19 | A chain record, CRITICAL severity, `NEEDS_VERIFICATION` confidence | BLOCK (unresolved chain confidence is treated the same as an unresolved HIGH/CRITICAL candidate — not a free pass, same failure mode as case 4/16) |
| 20 | A chain record, MEDIUM severity, HIGH confidence | PASS_WITH_WARNINGS |
| 21 | A chain record, CRITICAL severity + one unrelated CONFIRMED LOW finding, same batch | BLOCK (precedence across findings and chain records together — see `plays/security-gate.md`'s "Outcomes") |
| 22 | A chain record, INFORMATIONAL severity | PASS |
| 23 | One MEDIUM candidate, validated, result NEEDS_VERIFICATION | PASS_WITH_WARNINGS (unlike case 4 — the BLOCK escalation for an unresolved candidate applies only at HIGH/CRITICAL; see `plays/security-gate.md`'s Default policy table) |
| 24 | One MEDIUM candidate, not yet validated | PASS (unlike case 3 — an unvalidated MEDIUM/LOW candidate doesn't itself warrant AWAITING_VALIDATION or a note) |

Cases 1–9 exercise the default policy table directly. Case 10 exercises
risk-acceptance handling; cases 11–13 exercise precedence/aggregation
across a batch. Cases 14–17 exercise the remediation-outcome mapping.
Cases 18–22 exercise the chain-record rows added alongside the
per-finding policy table — a chain record is not itself a finding and
has no CONFIRMED/REJECTED status, only a Confidence and a Chain
severity, so the lookup keys differ from cases 1–17 even though the
outcome vocabulary is the same. Cases 23–24 exercise the MEDIUM/LOW
candidate rows — do not conflate them with cases 3–4; only HIGH/
CRITICAL gets the AWAITING_VALIDATION/BLOCK treatment for an
unresolved candidate.
If a reviewer gets case 4, 16, or 19 wrong
(treating an unresolved HIGH/CRITICAL, or an unresolved chain, as
safe), that is the specific failure mode `plays/security-gate.md`'s
"Handling an unresolved HIGH/CRITICAL candidate" section (and its
chain-record analog) exists to prevent — treat it as a priority fix,
not a minor scoring miss.
