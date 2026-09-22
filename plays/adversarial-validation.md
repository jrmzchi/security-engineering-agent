# Play: Adversarial Validation

Authoritative procedure for `skills/adversarial-validation`. Actively
tries to **defeat** a claimed protection or remediation, for a
specific, bounded set of high-risk cases — not a separate pass with
its own outcome vocabulary, but a technique checklist whose findings
get recorded using this kit's *existing* finding/remediation
vocabulary (see "Results use existing vocabulary, not a new one"
below), plus a structured evidence tag for the checklist's own
conclusion that never decides that outcome by itself (see "Structured
result metadata" below). Extends `plays/security-remediation.md`'s
existing re-validation questions (which already ask some of this,
narrowly) and
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
    question, per "A different objective" above) EXCEPT an
    exposure-type remediation (see "Findings this checklist genuinely
    doesn't apply to" below and "Structured result metadata"'s
    remediation-side NOT_APPLICABLE)
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

This checklist's **outcome** — what happens to the finding's or
remediation's status — never gets a parallel state machine on top of
what already exists; a bypass or its absence still resolves to the
finding/remediation vocabulary that already applies to whatever was
being checked (see "Structured result metadata" below for how the
checklist's *own* conclusion is additionally recorded as an evidence
tag alongside that outcome, not instead of it):

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

## Structured result metadata (an evidence tag, never a decision)

Record the checklist's own conclusion as a structured field alongside
the outcome above — **every value here is supporting evidence for
whichever section actually decides the outcome (this play's "Results
use existing vocabulary" above, `plays/security-remediation.md`'s
Result block, or `plays/attack-chain-analysis.md`'s "When a chain is
real"/"Confidence" sections for a chain); no value in this field ever
decides the outcome by itself.** That constraint is absolute, not a
default: a value that would need to force a status change belongs in
one of those sections, not here.

Each of the three carriers below gets its own complete definition of
what each value supports *in that carrier's terms* — deliberately not
"define once, reuse by analogy" for the other two, since that pattern
is exactly how earlier issues in this section went unnoticed: a value
re-scoped for one carrier but left with another carrier's wording
still attached.

**For a claimed protection on an original finding:**

```text
CONTROL_HOLDS         the control was actively challenged (realistic
                       bypass paths considered per "The techniques"
                       above) and no viable bypass was found on
                       *this* control specifically. Supports, but does
                       not by itself decide, the finding's status —
                       a CONFIRMED finding can carry a CONTROL_HOLDS
                       tag on a secondary/partial control that never
                       fully mitigated it in the first place
BYPASS_FOUND           a concrete, evidenced bypass of *this* control
                       exists. Supports "Results use existing
                       vocabulary" above's CONFIRMED rule — applied to
                       whichever finding this control's failure
                       actually affects, which the Validator
                       determines; this tag records the evidence, not
                       the resulting status
CONTROL_INCONCLUSIVE   evidence is insufficient, environment/framework
                       behavior can't be established, or the
                       checklist couldn't be run as a genuinely
                       independent pass. Supports NEEDS_VERIFICATION
                       per "Results use existing vocabulary" above,
                       applied by the Validator
NOT_APPLICABLE         considered and determined not to apply — an
                       exposure-type finding with no claimed
                       protection to attack (see "Findings this
                       checklist genuinely doesn't apply to" above),
                       or a finding a reviewer determined was outside
                       the trigger list — not simply omitted without
                       that consideration
```

**For a remediation:**

```text
FIX_HOLDS         no bypass found across the techniques actually
                   tried — supports, but by itself does not
                   guarantee, RESOLVED (ordinary re-validation's own
                   check against the original reproduction still has
                   to pass too, and a regression check per
                   plays/security-remediation.md's "Checking for
                   newly introduced issues" still applies)
FIX_BYPASSED       a concrete bypass of the fix exists. Supports
                   STILL_VULNERABLE (or REGRESSION_INTRODUCED if the
                   fix also broke legitimate functionality) per
                   plays/security-remediation.md's Result block —
                   the Result there states the outcome, this tag only
                   supports it
FIX_INCONCLUSIVE   re-validation could not establish one of the
                   above — supports FIX_UNVERIFIED, applied by the
                   re-validation pass
NOT_APPLICABLE     considered and determined not to apply — the
                   underlying finding is exposure-type with no fix
                   behavior to attack (mirrors the finding-side
                   carve-out above: leaked credentials, reachable
                   known-CVE dependencies). Every other HIGH/CRITICAL
                   remediation is on the trigger list by default (see
                   "When this checklist is worth the effort" above)
                   and should use one of the other three values, not
                   this one
```

**For an attack chain** (`plays/attack-chain-analysis.md`), applying
the checklist to the preconditions/controls *between* steps per this
play's own trigger-list entry above — this reuses three of the same
names for a different object, disclosed as safe the same way
`plays/finding-validation.md`'s notes on `NEEDS_VERIFICATION`'s reuse
disclose it elsewhere: a chain record and a finding are never the same
object needing two meanings at once. Each value is independently
defined here, not inherited from the finding-side table above.
`NOT_APPLICABLE` is deliberately **not** part of this set: a
multi-finding chain is always on the trigger list by default (per this
play's own trigger list above), so there is no case where the
checklist doesn't apply to a chain that exists at all — every
transition gets one of the other three values, never this one:

```text
CONTROL_HOLDS          the precondition/control between two
                       consecutive steps was actively challenged and
                       no way was found to reach the later step while
                       skipping the earlier one. Supports that
                       transition continuing to satisfy
                       plays/attack-chain-analysis.md's "When a chain
                       is real" test — does not by itself confirm the
                       chain overall if other transitions still need
                       checking
BYPASS_FOUND           a way to reach the later step while skipping
                       the earlier one was found — the precondition
                       does not actually hold as claimed. Supports
                       re-examining that link against
                       plays/attack-chain-analysis.md's "When a chain
                       is real" core requirement (if the later step is
                       reachable without the earlier one, the earlier
                       step is not a required link); the chain record
                       needs revising — removing that step, or
                       documenting the shorter path as its own finding
                       — not just noting the bypass
CONTROL_INCONCLUSIVE   evidence is insufficient to confirm whether a
                       precondition holds. Supports
                       `NEEDS_VERIFICATION` specifically as this
                       chain's own Confidence value (see
                       plays/attack-chain-analysis.md's "Confidence"
                       section) — a second disclosed-safe reuse of
                       that name for this object, distinct from this
                       tag: the tag records *why* (a challenged
                       precondition couldn't be resolved), the
                       Confidence field records the resulting level
```

Record supporting evidence (which technique(s) were tried, what they
found) alongside the value in every case above — a bare enum with no
evidence is not more useful than the narrative form this extends.

These values are spelled ALL_CAPS above, matching this kit's
machine-readable-status convention (see
`plays/finding-validation.md`'s note on that convention). Where a
carrier's own template already writes its other fields in a different
case (`templates/finding.md`'s `Status: Candidate | Confirmed | ...`
is Title_Case, matching that template's own local convention, not this
one), write these values in that carrier's local case instead — the
identifier matters, not the letter case.

### Why this is safe

An earlier draft of this play tried a full parallel state machine
(`CONTROL_HOLDS`/`BYPASS_FOUND` *as* the outcome, not alongside it) and
was rejected by review for three reasons: (1) a branch that could
never be reached (`BYPASS_FOUND` combined with an "or
NEEDS_VERIFICATION" option that its own "concrete, evidenced"
definition made impossible); (2) it silently reused the "can't
establish" naming family a third time without disclosure; (3) it
misstated how narrow `plays/security-remediation.md`'s existing
re-validation question was.

A later revision of *this* redesign was itself found, on review, to
have reintroduced (1) and (2) in new forms twice more: first, three of
the four values were defined as deterministic (forcing a status
change) — a second outcome mechanism regardless of framing, whose
scope mismatch (a tag about *one control* forcing a decision about
*the whole finding*) produced exactly the kind of contradictory
combination (1) describes; and the bare `INCONCLUSIVE` name, reused
verbatim across the finding-side and remediation-side enums with two
different target statuses, recreated (2). Second, after fixing those,
the attack-chain carrier was added by re-scoping only one of the four
values and leaving the other three with finding-oriented wording still
attached — which left `CONTROL_INCONCLUSIVE` pointing at a
`NEEDS_VERIFICATION` that, on a chain record, is a different field
(Confidence) than the one it meant for a finding (status), undisclosed,
and left `NOT_APPLICABLE` defined only in finding-shaped terms a chain
could never satisfy.

Rather than re-litigate each fix, use this checklist whenever this
section is next touched — for a new value, a new carrier, or restoring
any determinism:

```text
1. Does this value decide an outcome/status/Confidence field by
   itself, for any carrier? If yes, it belongs in a status-defining
   section (e.g. "Results use existing vocabulary" above), not here.
2. Is every value defined independently and completely for the
   carrier it's being added to — not "same as finding's, except X"?
   A value inherited-by-reference is exactly how the chain carrier's
   defect happened.
3. Does this value's name already carry a specific, different meaning
   elsewhere in this kit? If reused, is it disclosed as safe using the
   same test `plays/finding-validation.md`'s notes on
   `NEEDS_VERIFICATION`'s reuse already apply: would any single object
   ever need this name to mean two different things at once?
4. When adding a new carrier: does its own template gain the field,
   does its owning play's "Required fields" (or equivalent) list it,
   and does this play's "Where this is recorded" name it? All three,
   not just the value definitions above — a carrier added without all
   three is exactly how the chain carrier's first attempt fell short.
```

A "no" to (1), and a genuine "no" to (3) (or an explicit, checked
disclosure), are what keep this field evidence rather than a decision;
(4) is what keeps a new carrier actually reachable in practice.

## Where this is recorded

This play is invoked from `skills/security-review/SKILL.md`'s workflow
(step 7), `AGENTS.md`'s routing summary (steps 7 and 9), and
`plays/security-remediation.md`'s mandatory re-validation question —
that wiring is done. `templates/finding.md`'s "Validation" section,
`plays/security-remediation.md`'s re-validation result block, and
`templates/attack-chain.md`'s chain record each have a dedicated
`Adversarial Validation:` field for the structured result above, plus
room for the supporting evidence — see those files for the exact
field.

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
the finding's or control's existing status stand unexamined
(`CONTROL_INCONCLUSIVE`/`FIX_INCONCLUSIVE` in the structured field
above, which supports the same conclusion).

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

## Output

No new artifact, and the outcome still uses this kit's existing
finding/remediation vocabulary — see "Results use existing vocabulary,
not a new one" above. The checklist's own conclusion is additionally
recorded via the dedicated field described in "Where this is recorded"
above; a finding or remediation this checklist was applied to is still
reported using `templates/finding.md`/`plays/security-remediation.md`'s
existing format otherwise, same as always.
