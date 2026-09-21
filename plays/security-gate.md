# Play: Security Gate

Authoritative procedure for `skills/security-gate`.

## When this runs

The gate runs whenever candidate findings exist, **regardless of the
change's sensitivity level** from `skills/security-change-detection`.
Sensitivity determines whether design/review happen at all — it does
not exempt a MODERATE-classified change from the gate if targeted
review turned up something CONFIRMED. A NONE/LOW change with zero
findings has nothing to gate; that is what skips it in practice, not
the sensitivity label itself.

## Inputs this play consumes (and does not redefine)

Every finding arriving here already has a status from
`plays/finding-validation.md`'s Result section: `CONFIRMED`, `REJECTED`,
or `NEEDS_VERIFICATION`, plus a severity and a confidence. Because
`finding-validation.md` never allows a LOW-confidence candidate to
become `CONFIRMED`, a `CONFIRMED` finding reaching this step has
already cleared the confidence bar — this play does not re-check
confidence separately, only severity, and only for findings that are
`CONFIRMED` or still unvalidated.

**This play does not reuse `NEEDS_VERIFICATION` as an outcome name.**
`finding-validation.md`'s `NEEDS_VERIFICATION` is a *finding* status —
a candidate that was independently validated and the validator could
not establish enough to confirm or reject it. That is a different fact
from "no one has validated this candidate yet," which is what used to
be called `NEEDS_VERIFICATION` here in an earlier draft and collided
with the finding-level status of the same name — see "Handling an
unresolved HIGH/CRITICAL candidate" below for why the two cases need
different outcomes.

**A chain record (`plays/attack-chain-analysis.md`) is a second,
independent input this play consumes, alongside findings.** It is not
itself a finding and carries no `CONFIRMED`/`REJECTED`/
`NEEDS_VERIFICATION` finding-level status — instead it carries its own
Confidence (`HIGH`/`MEDIUM`/`LOW`/`NEEDS_VERIFICATION`) and Chain
severity fields, and this play gates on the chain's own assessed
severity, not derived from its component findings' severities. Gate on
it in addition to gating on each component finding individually — a
CRITICAL chain built from component findings that individually only
reach MEDIUM must BLOCK even though neither component alone would
have. An unresolved (`NEEDS_VERIFICATION`-confidence) chain follows the
same rule as an unresolved HIGH/CRITICAL candidate below — treated as
unsafe, not a free pass; see "Default policy" for the exact rows. No
automated tooling in this kit currently looks up a chain record as
part of running the gate — until it does, whoever runs the gate must
check for one manually and apply those rows by hand.

## Outcomes

```text
PASS                     no CONFIRMED findings requiring action, and no
                          chain record above INFORMATIONAL severity
PASS_WITH_WARNINGS        CONFIRMED MEDIUM/LOW findings and/or a
                          MEDIUM/LOW-severity chain record only —
                          noted, not blocking
AWAITING_VALIDATION       a HIGH/CRITICAL candidate exists that has not
                          yet been through skills/security-validate
BLOCK                     a HIGH/CRITICAL finding is CONFIRMED, OR a
                          HIGH/CRITICAL candidate was independently
                          validated and resolved NEEDS_VERIFICATION
                          (see below — unresolved is treated as unsafe,
                          not as a free pass), OR a chain record reaches
                          CRITICAL/HIGH severity at any confidence,
                          including NEEDS_VERIFICATION (same "no free
                          pass" rule applied to the chain's own
                          Confidence field)
PASS_WITH_ACCEPTED_RISK    a BLOCK-eligible finding or chain record
                          exists, but the user has explicitly accepted
                          the risk
```

These five have a fixed precedence, most severe first, for aggregating
across a batch of findings:

```text
BLOCK > AWAITING_VALIDATION > PASS_WITH_ACCEPTED_RISK >
PASS_WITH_WARNINGS > PASS
```

Take the least-permissive (highest-precedence) outcome across all
findings **and any chain records** in scope. `REJECTED` findings are
not live findings and do not enter this computation at all — see
`plays/finding-validation.md`'s "Rejected findings" for where they go
instead (kept for audit transparency, not gated on).

## Default policy (per finding, or per chain record)

```text
CONFIRMED, CRITICAL                                    -> BLOCK
CONFIRMED, HIGH                                         -> BLOCK
HIGH/CRITICAL candidate, validated, still NEEDS
    VERIFICATION (validator could not establish enough
    to confirm OR reject)                                -> BLOCK
HIGH/CRITICAL candidate, not yet validated                -> AWAITING_VALIDATION
CONFIRMED, MEDIUM                                         -> PASS_WITH_WARNINGS
CONFIRMED, LOW                                             -> PASS_WITH_WARNINGS
INFORMATIONAL                                               -> PASS
REJECTED                                                     -> excluded (not gated)

Chain record, CRITICAL or HIGH severity, any confidence
    including NEEDS_VERIFICATION                           -> BLOCK
Chain record, MEDIUM or LOW severity, any confidence
    including NEEDS_VERIFICATION                           -> PASS_WITH_WARNINGS
Chain record, INFORMATIONAL severity                          -> PASS
```

## Handling an unresolved HIGH/CRITICAL candidate

Two situations look similar but need different outcomes:

```text
Not yet validated
    -> AWAITING_VALIDATION. The workflow is incomplete, not finished:
    run skills/security-validate, then re-apply this table.

Validated, and the validator's answer is NEEDS_VERIFICATION (evidence
insufficient to confirm or reject — see
plays/finding-validation.md's Result section)
    -> BLOCK, same as CONFIRMED. Validation already happened; there is
    no further step that resolves the uncertainty on its own. Treating
    an un-confirmable HIGH/CRITICAL candidate as safe would contradict
    this project's own bias toward under-reporting over false
    assurance (see AGENTS.md's "Prefer more reliable findings over more
    findings"). The only way past this BLOCK is the same one available
    for a CONFIRMED finding: fix what can be fixed to remove the
    uncertainty, or explicit risk acceptance below.
```

## After a remediation attempt

`plays/security-remediation.md`'s independent re-validation produces
its own result (`RESOLVED`/`STILL_VULNERABLE`/`FIX_UNVERIFIED`/
`REGRESSION_INTRODUCED`), which maps back into this table by re-running
it against the *current* state rather than by a separate rule:

```text
RESOLVED              -> the finding is no longer CONFIRMED; re-apply
                          this table without it (typically -> PASS or
                          whatever the remaining findings resolve to)
STILL_VULNERABLE       -> unchanged: still CONFIRMED -> BLOCK
FIX_UNVERIFIED          -> same treatment as a validated-but-unresolved
                          candidate above -> BLOCK
REGRESSION_INTRODUCED   -> the new issue is its own candidate; gate on
                          it like any other (typically -> BLOCK or
                          AWAITING_VALIDATION depending on whether it
                          has itself been validated yet), in addition
                          to whatever the original finding's status is
```

## Explicit risk acceptance

A CONFIRMED (or validated-but-unresolved) HIGH/CRITICAL finding must
never silently disappear from the record. If the user explicitly
accepts the risk instead of resolving it, retain:

```text
Status: RISK_ACCEPTED
Original severity
Original confidence (or "not established" for the NEEDS_VERIFICATION case)
Residual risk
Reason, if supplied
```

Gate outcome becomes `PASS_WITH_ACCEPTED_RISK` — not a plain `PASS`. Do
not rewrite a blocking finding's record as if it were never found; the
acceptance is a decision layered on top of the finding, not a
replacement for it.

A BLOCK-eligible chain record follows the same rule: retain the same
fields (substituting the chain's own severity/confidence for
"Original severity"/"Original confidence"), and the outcome becomes
`PASS_WITH_ACCEPTED_RISK` rather than dropping the chain from the
record. Accepting the chain's risk does not implicitly accept its
component findings' risk, or vice versa — each is accepted (or not)
independently.

## What this play does not do

It does not re-derive severity or confidence — those come from
`plays/finding-validation.md`'s models, already applied by the time a
finding reaches this step. This play only maps an already-determined
status to a completion outcome.

## Worked examples (cases the policy table above doesn't already spell out)

```text
One CONFIRMED HIGH + three PASS-level findings in the same batch
    -> BLOCK overall (precedence rule, not majority)

One CONFIRMED HIGH with explicit user risk acceptance, plus one
CONFIRMED MEDIUM with no acceptance
    -> PASS_WITH_ACCEPTED_RISK overall (still above
    PASS_WITH_WARNINGS in precedence — the accepted HIGH risk is the
    more consequential fact about this batch, even though the MEDIUM
    was never explicitly accepted)
```
