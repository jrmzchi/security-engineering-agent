# Play: Security Remediation

Authoritative procedure for fixing a confirmed finding, verifying the
fix independently, and adding regression protection. Picks up where
`plays/finding-validation.md` leaves off (a CONFIRMED finding) and ends
at `RESOLVED` or a documented reason it isn't.

## Workflow

```text
Confirmed finding
        |
Identify root cause
        |
Design smallest safe fix
        |
Implement fix
        |
Review resulting diff
        |
Reconstruct original attack path
        |
Verify attack path is broken
        |
Run regression test
        |
Check for newly introduced security issues
        |
Mark RESOLVED
```

**Prefer the smallest correct remediation over an unrelated
architectural rewrite** — see `plays/finding-validation.md`'s
Remediation requirements ("Prefer the smallest safe fix... that is
scope creep, not remediation"), which applies here with extra force: a
remediation diff is exactly the kind of change that should be small
enough for the independent re-validation step below to actually
re-derive confidence in.

## Root cause, not symptom

Identify what actually let the attack path work (missing
parameterization, missing authorization check, missing containment
check — see the relevant `plays/*.md` for the category) before writing
a fix. A fix that suppresses the specific payload used to demonstrate
the finding, without addressing the underlying missing control, is not
remediation — see "fake fix" below.

## Finding lifecycle

`CONFIRMED`, `REJECTED`, and `NEEDS_VERIFICATION` are defined in
`plays/finding-validation.md`'s Result section — this play does not
redefine them. (`CANDIDATE` is used informally throughout this project
for "not yet validated" and is formalized as a status in
`templates/finding.md`'s Status field, not in `plays/finding-validation.md`
itself.) This play adds the statuses that track what happens *after* a
finding is `CONFIRMED`:

```text
REMEDIATION_IN_PROGRESS     a fix is being worked on
FIXED_PENDING_VERIFICATION  a fix has been implemented, not yet
                             re-validated (see below)
RESOLVED                    independently re-validated as fixed
RISK_ACCEPTED               see plays/security-gate.md's risk-acceptance
                             section
```

Use these statuses where remediation is actually being tracked — do not
pad an ordinary report with lifecycle fields for findings that were
simply `REJECTED` on first pass and need no further tracking.

## Independent re-validation (mandatory for HIGH/CRITICAL)

**Never consider a HIGH/CRITICAL vulnerability resolved solely because
the same agent that found it also changed the code.** Run a genuinely
independent pass — a separate `security-validator` subagent where
available (see `integrations/claude/README.md`), or a deliberately
skeptical second pass otherwise (see `agents/security-validator.md`'s
"Independence" section, which applies identically here).

The re-validation pass determines:

```text
Does the original attack path still work?
Did the fix address the root cause, or just this one payload?
Was the vulnerability merely moved somewhere else?
Can the protection be bypassed a different way?
Did the fix introduce another vulnerability?
Does legitimate functionality still work?
```

For "Can the protection be bypassed a different way?" specifically,
`plays/adversarial-validation.md` gives a systematic ten-technique
checklist (alternate representations, encoding/canonicalization,
sibling endpoints, and more) instead of relying on whatever bypass
attempt comes to mind — apply it in full for any HIGH/CRITICAL
remediation except an exposure-type one (see that play's trigger list
and "Structured result metadata" section, which name this exact case
and its exception).

Result:

```text
RESOLVED               attack path confirmed broken, root cause addressed,
                        legitimate use still works
STILL_VULNERABLE        attack path still works, or only the demonstrated
                        payload was blocked while the underlying gap remains
FIX_UNVERIFIED          re-validation could not establish one of the above
                        (deliberately not named "NEEDS_VERIFICATION" —
                        that name is already the finding-level status
                        for "validator couldn't confirm or reject the
                        original candidate", a different fact at a
                        different stage; see plays/security-gate.md's
                        note on why the two must stay distinct)
REGRESSION_INTRODUCED   the fix broke legitimate functionality, or
                        introduced a new, different security issue
```

Once `plays/adversarial-validation.md`'s checklist has been considered
for this remediation (mandatory by default for any HIGH/CRITICAL
remediation, per that play's trigger list), record:

```text
Adversarial Validation: FIX_HOLDS | FIX_BYPASSED | FIX_INCONCLUSIVE |
    NOT_APPLICABLE
    (see that play's "Structured result metadata" — an evidence tag
    the re-validation pass weighs, never a replacement for the Result
    above; use NOT_APPLICABLE only if the underlying finding is
    exposure-type with no fix behavior to attack — every other HIGH/
    CRITICAL remediation is on the trigger list by default, so use one
    of the other three values instead of marking it not applicable)
Techniques tried: which technique(s) were tried and what they found
```

A HIGH/CRITICAL finding cannot become `RESOLVED` without this pass. If
subagents are unavailable and a genuinely independent second look is
not practical, mark `FIX_UNVERIFIED` rather than claiming `RESOLVED` on
an unearned basis. Treat `FIX_UNVERIFIED` the same as `STILL_VULNERABLE`
for gate purposes — see `plays/security-gate.md`'s handling of an
unresolved HIGH/CRITICAL candidate — since the alternative (defaulting
to safe) would be the same false-assurance failure mode that play
exists to prevent.

### Fake fix (what STILL_VULNERABLE looks like in practice)

A fix that special-cases the exact reproduction string from the
original finding — e.g. blocking the literal payload
`' OR '1'='1` instead of parameterizing the query — leaves the
underlying missing control in place. Reconstructing the attack path
with a *different* payload targeting the same root cause should still
succeed, and the validator should report `STILL_VULNERABLE`, not
`RESOLVED`.

## Regression verification

Add a regression test whenever practical, covering both the attack and
that legitimate use still works. Worked examples by category:

```text
SQL injection
  malicious SQL-like input -> query structure remains unchanged
  legitimate query -> still returns correct results

Path traversal
  ../appsettings.json (and encoded variants) -> rejected
  legitimate filename -> still served

Authorization (IDOR)
  User A requests User B's resource -> forbidden (or concealed,
      per the app's disclosure policy)
  User A requests their own resource -> still works

XSS
  <script>alert(1)</script> as input -> rendered as inert text, not
      executed
  legitimate content with markup-like characters -> still displays
      correctly

File upload
  dangerous executable/script content -> rejected, or stored in a
      non-executable location per policy
  legitimate file type -> still uploads and is retrievable
```

See `plays/finding-validation.md`'s "Verification requirements" for the
general shape this follows, and `templates/finding.md`'s
`### Verification` field for where this goes in the report.

## Checking for newly introduced issues

Before marking `RESOLVED`, review the remediation diff itself with the
same rigor as any other change — a parameterization fix that
introduces a new type-confusion bug, or an authorization fix that
accidentally locks out a legitimate role, is a `REGRESSION_INTRODUCED`
result, not a clean resolution.
