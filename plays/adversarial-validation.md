# Play: Adversarial Validation

Authoritative procedure for `skills/adversarial-validation`. Actively
tries to **defeat** a claimed protection or remediation, for a
specific, bounded set of high-risk cases — not a separate pass with
its own result vocabulary, but a technique checklist whose findings
get recorded using this kit's *existing* finding/remediation
vocabulary (see "Results use existing vocabulary, not a new one"
below). Extends `plays/security-remediation.md`'s existing
re-validation questions (which already ask some of this, narrowly) and
`plays/finding-validation.md`'s existing validation procedure into a
more systematic bypass-hunting pass for the specific cases where that
extra rigor is worth its cost.

## A different objective from ordinary validation, not more of the same

`skills/security-validate/SKILL.md`'s Validator asks: *does the
evidence for this candidate actually hold up?* — reduces false
positives. This play asks the opposite-facing question, for a *claimed
protection on an original finding* specifically: *given a control that
appears to hold, can I actively find a way past it anyway?* — reduces
false negatives.

For a *remediation*, this play does not introduce a separate question
at all. `plays/security-remediation.md`'s "Independent re-validation
(mandatory for HIGH/CRITICAL)" section already requires asking, for
every HIGH/CRITICAL fix: "Can the protection be bypassed a different
way? Was the vulnerability merely moved somewhere else?" — that
question already covers this play's territory for remediations. What
this play adds there is not a new pass but a **systematic checklist**
for answering it (see "The techniques" below) instead of relying on
whatever bypass attempt happens to come to mind, plus an explicit
trigger list for which remediations most need the full checklist
applied rather than a lighter pass. Don't build a second "adversarial
remediation validation" pass alongside the existing one — extend the
existing one with this checklist.

### Independence

`skills/security-validate/SKILL.md`'s "Independence" section already
requires the Validator to be a distinct pass from whichever one
produced the candidate. Apply the same principle here: for a claimed
protection on an original finding, run this checklist as a pass
distinct from the one that first accepted the control at face value —
where the environment supports it (a separate subagent/context), run
it independently; where it doesn't, perform it as an explicitly
separate reasoning pass that reconstructs its own evidence rather than
restating the earlier pass's conclusion in adversarial-sounding
language. For a remediation, this is simply what
`plays/security-remediation.md`'s existing independence requirement
for that mandatory pass already means, applied with this checklist.

## When this checklist is worth the effort

**Apply it (rather than an ordinary validation/re-validation pass with
no special bypass-hunting effort) by default for:**

```text
Confirmed CRITICAL finding, before accepting any claimed mitigating
    control at face value
Confirmed HIGH finding with more than one control in its path, or
    where a control's effectiveness depends on normalization/encoding/
    execution order rather than a simple check
Any HIGH/CRITICAL remediation (applying this checklist to
    plays/security-remediation.md's existing mandatory re-validation
    question, per "A different objective" above)
Authentication bypass claims
Authorization bypass claims
SSRF with an allowlist/proxy protection
Path traversal with a canonicalization control
Upload restrictions (extension/content-type/size checks)
Deserialization
Any other security-control bypass claim
A multi-finding attack chain (plays/attack-chain-analysis.md) — apply
    it to the preconditions/controls BETWEEN steps, asking whether a
    step in the chain can be reached some other way that skips an
    earlier step, not to the chain's already-established combined
    impact (disproving that a chain holds together is
    plays/finding-validation.md's/plays/attack-chain-analysis.md's own
    validation job, not this play's)
```

**Not required for every LOW finding**, and not a blanket second pass
on everything `skills/security-validate` touches or every ordinary
remediation. Applying it indiscriminately burns effort disproportionate
to the risk. Findings/remediations not on this list still go through
ordinary validation/re-validation as before — this play adds rigor for
specific cases, it doesn't gate everything else on it.

This list is not exhaustive for what an original finding's claimed
protection might need it — `Confirmed HIGH finding with more than one
control in its path` is deliberately the catch-all: if a control's
soundness depends on more than a single, simply-checkable condition,
default to applying this checklist rather than skipping it.

## The techniques

For the claimed protection or fix in question:

```text
1.  Start from the protection/fix itself, not from a blank slate —
    what specifically is it checking or blocking?
2.  Identify its assumptions — what does it assume is true about the
    input, the caller, or the environment that might not hold?
3.  Search for bypass conditions given those assumptions
4.  Try alternate attacker-controlled representations of the same
    logical input (different casing, encoding, structure) — not just
    the original reproduction restated
5.  Consider framework normalization — does something upstream or
    downstream transform the input in a way the control doesn't
    account for? (The mirror image of
    plays/cross-file-data-flow.md's "Inspect framework protections"
    step: that one asks whether a framework protection defeats an
    apparent vulnerability; this asks whether framework behavior
    defeats an apparent protection.)
6.  Consider encoding/canonicalization differences specifically
    (percent-encoding, Unicode normalization, path separators)
7.  Consider alternate entry points that might reach the same
    vulnerable operation without passing through this control at all
8.  Consider race/state issues where relevant (check-then-use gaps,
    concurrent requests) — this is usually where "say so and stop"
    applies (see "Safety boundary" below): confirming a race condition
    typically requires live timing behavior this kit's static analysis
    can't demonstrate
9.  Consider whether a sibling endpoint/route shares the vulnerable
    logic but lacks this specific control
10. Report evidence conservatively — a technique that seems like it
    should work but wasn't actually confirmed against real behavior is
    not a demonstrated bypass; record it as inconclusive per "Results"
    below, not as a finding
```

## Results use existing vocabulary, not a new one

This play doesn't add `CONTROL_HOLDS`/`BYPASS_FOUND`-style states on
top of what already exists — a bypass or its absence is recorded using
the finding/remediation vocabulary that already applies to whatever
was being checked:

**For a claimed protection on an original finding:**

```text
A concrete bypass demonstrated with evidence
    -> the finding is CONFIRMED (plays/finding-validation.md) — if it
       was previously REJECTED on the strength of the now-bypassed
       control, it moves back to CONFIRMED, never staying REJECTED
       once a concrete bypass exists

A technique suggests a possible gap that couldn't be confirmed with
available evidence
    -> NEEDS_VERIFICATION (plays/finding-validation.md), stating which
       technique and what would resolve it

Every technique tried, none produced a concrete bypass or an
unresolved lead
    -> the finding's existing status stands (REJECTED stays REJECTED;
       CONFIRMED stays CONFIRMED) — this checklist is supporting
       evidence for that conclusion, not a new one of its own

A CONFIRMED finding's claimed mitigating control turns out to be
bypassable
    -> the control's failure changes what an attacker can actually
       achieve, which may change severity even though the CONFIRMED
       status doesn't change — re-assess severity per
       plays/finding-validation.md's severity model, don't just note
       the bypass and leave severity as originally assessed
```

**For a remediation:** the checklist feeds
`plays/security-remediation.md`'s existing re-validation outcomes
directly — a demonstrated bypass means `STILL_VULNERABLE`
(`plays/security-remediation.md`'s "Fake fix" section is exactly this
case, checked with technique 4 specifically); an unresolved lead that
can't be confirmed means `FIX_UNVERIFIED`; no bypass found across the
techniques actually tried supports (but by itself does not guarantee)
`RESOLVED` — ordinary re-validation's own check against the original
reproduction still has to pass too.

**Findings this checklist genuinely doesn't apply to:** an
exposure-type finding (a leaked credential, a reachable known-CVE
dependency — see `plays/finding-validation.md`'s exposure-type
exception) has no claimed protection or fix to attack in the first
place. Route these back to ordinary validation rather than running this
checklist against nothing.

## Sequential fallback: no independent pass available

When no separate subagent/context is available and a genuinely
independent second look isn't practical, do not silently default to
whichever result implies the control/fix holds — that is exactly the
unearned-confidence failure mode
`plays/security-remediation.md`'s independence requirement already
exists to prevent for remediations (mark `FIX_UNVERIFIED` rather than
claim `RESOLVED` on that basis). Apply the same default for an original
finding's claimed protection: if this checklist couldn't actually be
run as a separate pass, record `NEEDS_VERIFICATION` rather than letting
the finding's or control's existing status stand unexamined.

## Safety boundary

This is reasoning about exploit paths in code already available for
review, using the same static-analysis discipline as the rest of this
kit — not authorization to scan third-party hosts, brute-force
anything, or take any action against a running system. See
`plays/finding-validation.md`'s "Safe testing and validation
boundaries" section, which already governs every finding this play
touches, including its explicit prohibition on exfiltrating or
printing real, unredacted secrets — nothing here loosens that. If
confirming a bypass (a race condition is the most likely case here —
see technique 8) would require live testing against a real
environment, say so and stop rather than asserting the bypass anyway.

## Recorded via existing narrative, not a dedicated field

This play is invoked from `skills/security-review/SKILL.md`'s workflow
(step 7), `AGENTS.md`'s routing summary (steps 7 and 9), and
`plays/security-remediation.md`'s mandatory re-validation question —
that wiring is done. What remains open: `templates/finding.md`'s
"Validation" section and `plays/security-remediation.md`'s
re-validation reporting still have no dedicated structured field for
recording that this checklist was applied (which techniques, and what
was found) — record it as part of the existing Validation/
re-validation narrative rather than omitting it, or adding one,
until a later batch decides a dedicated field is worth it.

## Output

No new artifact and no new status vocabulary of its own — see
"Results use existing vocabulary, not a new one" above. A finding or
remediation this checklist was applied to is still reported using
`templates/finding.md`/`plays/security-remediation.md`'s existing
format, same as always.
