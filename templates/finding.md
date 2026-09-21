# Finding Template

Copy this format for each finding. See `plays/finding-validation.md` for
the confidence/severity models and the attack-path requirement that
drives several of these fields, and `references/*.md` for the CWE/OWASP
mappings relevant to a given stack.

```markdown
## [SEVERITY] Finding title

Status: Candidate | Confirmed | Rejected | Needs_Verification |
    Remediation_In_Progress | Fixed_Pending_Verification | Resolved |
    Risk_Accepted
    (first four: plays/finding-validation.md's Result section.
    Last three: plays/security-remediation.md's lifecycle, entered only
    once a finding is Confirmed and remediation begins — most findings
    never leave the first four.)
Confidence: HIGH | MEDIUM | LOW
Change Origin: Introduced | Modified | Pre_Existing | Unknown
    (see plays/finding-validation.md's "Baseline origin" — omit this
    field entirely for a review that isn't diff-aware, e.g. a full
    STANDARD/DEEP repository review with no "before" to compare against)

CWE: CWE-XXX (only if reasonably justified — see plays/finding-validation.md)
OWASP: relevant category, if applicable

Location:

file: path/to/file.ext
line: NN (or a range)

### Summary

One or two sentences: what is wrong, in plain language.

### Attack Path

For data-flow vulnerabilities (injection, XSS, SSRF, IDOR,
deserialization, and similar): the traced chain — attacker capability ->
entry point -> controlled data -> vulnerable operation -> boundary
crossed -> impact.

For exposure-type findings (confirmed leaked secret, reachable known-CVE
dependency, production misconfiguration): state the exposure and its
reachability/blast radius instead — see `plays/finding-validation.md`'s
exposure-type exception.

### Evidence

Minimal file/line references and the relevant snippet or scanner output
that supports the finding. Do not paste large code sections. Redact any
secret values (see `plays/secrets-security.md`).

### Impact

What an attacker can realistically achieve, given the confirmed attack
path/exposure — not the theoretical worst case for this CWE class in
general.

### Existing Controls

Any relevant control already in place (framework protection,
partial validation, authorization check) and why it does or does not
fully mitigate this finding.

### Validation

For HIGH/CRITICAL: the validator's independent findings per
`plays/finding-validation.md` (reachability, sanitization, authorization,
framework protections checked, and the resulting CONFIRMED/REJECTED/
NEEDS_VERIFICATION determination with reason). For lower severities,
this section may simply state that validation was not required per the
project's process. If this finding went through `skills/security-gate`,
note the outcome here too (PASS/BLOCK/AWAITING_VALIDATION/
PASS_WITH_WARNINGS/PASS_WITH_ACCEPTED_RISK — see `plays/security-gate.md`).
If this finding matched `plays/adversarial-validation.md`'s trigger
list, note which techniques were actually tried and what they found —
that play has no dedicated field of its own yet, so record it here as
part of this narrative rather than omitting it.

### Remediation

Actionable and specific — see `plays/finding-validation.md`'s
"Remediation requirements". Include a minimal safe code example
appropriate for the actual framework/language in use where practical.

### Verification

Concrete steps to confirm the fix works: add a regression test, submit
the input the finding describes, confirm the vulnerable behavior no
longer occurs, confirm legitimate use still works. See
`plays/finding-validation.md`'s "Verification requirements".

### References

Links or citations for the CWE/OWASP category, and any specific advisory
(CVE, GHSA) for dependency/secrets findings.
```
