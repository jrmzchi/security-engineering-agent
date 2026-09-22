# Play: Review Budget

Determines how much security-review effort a change actually justifies
— a second, independent dimension from `plays/security-change-detection.md`'s
NONE/LOW/MODERATE/HIGH sensitivity. Not a replacement for that
classification, and not a precise numeric score — the point is a
proportionate amount of effort, not a false sense of mathematical
rigor.

## Levels: `MINIMAL` / `FOCUSED` / `ELEVATED` / `AUDIT`

```text
MINIMAL    lightest possible touch — confirm the classification and move on
FOCUSED    proportionate, scoped effort — this is the common case
ELEVATED   more scrutiny than the classification alone would suggest:
           broader context, stricter validation requirements
AUDIT      full audit-grade effort
```

**Renamed from the naming this concept is commonly given elsewhere**
(`MINIMAL`/`TARGETED`/`ELEVATED`/`DEEP`): both `TARGETED` and `DEEP` are
already taken in this kit as **review mode** names (`plays/code-review.md`,
`plays/scanner-selection.md`) — a fixed set of activities a review must
perform (for `DEEP`: architecture analysis, a full scanner run, a threat
model, independent validation of every HIGH/CRITICAL candidate, a full
security report), not a strength dial. Budget and mode are a different
kind of thing entirely: budget is how much effort to spend, mode is
which activities/domains a review consists of. They can vary
independently — a `FOCUSED`-budget change and an `ELEVATED`-budget
change might both run under `TARGETED` review mode (same domains
loaded), just with different rigor once there.

This kit's own collision test (`plays/attack-surface-mapping.md`'s
"Evidence-backed mapping" section, applied when deciding whether
`NEEDS_VERIFICATION` was safe to reuse there) is: would the same object
ever need to carry both meanings at once? A single review always has
both a mode and a budget assigned to it at the same time — so reusing
either `TARGETED` or `DEEP` for a budget level fails that test the same
way. Calling a change "under DEEP review" would leave genuinely
ambiguous whether that means the mode's mandatory-activity checklist
or just the budget's effort level — a `MINIMAL`-budget, `DEEP`-mode
change (an explicit release audit that turns out to touch nothing
security-sensitive) and a `FOCUSED`-budget, `DEEP`-mode change are
different situations that "DEEP" alone couldn't distinguish. Renaming
both avoids it instead of relying on a "the meanings happen to agree"
argument that doesn't actually hold once mode and budget can vary
independently.

## Factors

None of these alone determines the level — weigh them together:

```text
External exposure          internet-reachable, or internal-only?
Attacker control            how much of the input is attacker-controlled?
Privilege                   does this touch a privileged operation?
Sensitive data               what's actually at risk?
Blast radius                 one user, all users, the whole system?
Security-boundary change     does this change what crosses a trust
                            boundary, or how?
Complexity                   how hard is this to reason about correctly?
Novelty                      is this a well-understood pattern in this
                            codebase, or something new?
Baseline confidence          see below
Changed attack-surface
centrality                   see below
```

Several of these names overlap with `plays/finding-validation.md`'s
severity factors (`Blast radius` is identical; `External exposure`/
`Sensitive data`/`Privilege` are close cousins of that model's
`Internet exposure`/`Data sensitivity`/`Required privileges`/`System
privileges`). That's a deliberate, safe reuse, not an oversight: that
model measures how bad a *confirmed vulnerability* is; this one
measures how much effort a *change* justifies before any vulnerability
is even known to exist. Same underlying intuitions, different question,
different object — apply the version that matches which question is
actually being asked.

### Baseline confidence

When `.security/baseline.json` exists (see
`plays/project-security-baseline.md`), low confidence in a relevant
fact pulls the budget up — reviewing a component whose security
posture rests on an `UNKNOWN`/`LOW`-confidence baseline fact deserves
more scrutiny than the same change against a `HIGH`-confidence one,
because the reviewer has less to rely on and more to independently
verify.

### Changed attack-surface centrality

`plays/security-impact-analysis.md`'s "Incremental invalidation"
section named this factor and deferred scoring it to this play. Score
it from `.security/attack-surface.json` (see
`plays/attack-surface-mapping.md`) when it exists — note the two node
kinds need opposite edge directions, because
`plays/attack-surface-mapping.md`'s "Control edge direction" section
makes a control node's own edges point *outward* (`from` the control,
`to` what it protects):

```text
For an ordinary node (SERVICE, DATA_STORE, FILESYSTEM, etc.): count
distinct nodes that reach it via an INCOMING edge (directly, or
through one intermediate node) — the more of the map that structurally
depends on this node, the more central it is.

For a control node (AUTHENTICATION_CONTROL/AUTHORIZATION_CONTROL/
VALIDATION_CONTROL): count its OUTGOING AUTHENTICATES/AUTHORIZES/
VALIDATES edges instead — a control's incoming-edge count says nothing
about how many things it protects, since its edges point away from it
by definition. A control backing many such edges is central regardless
of raw count elsewhere — one authentication middleware with only a
handful of outgoing edges can still back every protected route in the
map.
```

Without a map, judge qualitatively: routing/bootstrap configuration,
shared authentication/authorization middleware, a shared path
resolver, a shared HTTP client factory, a shared repository/data-access
layer, and a shared deserialization helper are the kinds of components
that are usually central even without a map to confirm it. This is a
**broader** list than `plays/security-impact-analysis.md`'s
"Incremental invalidation" exception, which is deliberately narrower
(routing/authentication-authorization bootstrap/other *configuration*
only, to keep that specific mechanism's blast radius bounded) — the two
lists serve different purposes and are not the same list: use this
broader one for sizing effort, that narrower one for deciding what to
invalidate. A component many other components depend on gets ELEVATED
treatment on that basis alone, even if the change itself looks small.

## Examples

```text
CSS color change
    -> MINIMAL

EF Core query change (ordinary, already-authorized report)
    -> FOCUSED

Authenticated file-download change
    -> ELEVATED

Authentication middleware rewrite
    -> AUDIT

Small internal endpoint, but the endpoint's auth state is UNKNOWN in
the baseline
    -> ELEVATED (uncertainty itself justifies more scrutiny)
```

### Default starting point, before weighing other factors

This is a lookup definition, exercised only when a live review actually
reaches this play — see "Applicability matrix" under "Output" below for
exactly which sensitivity/mode combinations that is. A `NONE`- or
`LOW`-classified change typically has no live review to apply the NONE/LOW
row to at all — the rows exist for completeness, not because every
sensitivity value is computed and applied on every change. When a
lightweight `LOW` check surfaces something suspicious
(`plays/security-change-detection.md`'s own "Re-classify from the actual
diff" step), the change gets re-classified to whatever the evidence now
supports — `MODERATE` or `HIGH` — and *that* row applies; the original
`LOW` row is never itself applied to a live review, escalated or not.

```text
NONE sensitivity      -> MINIMAL
LOW sensitivity        -> MINIMAL or FOCUSED
MODERATE sensitivity    -> FOCUSED
HIGH sensitivity         -> ELEVATED
```

Nothing here defaults straight to `AUDIT` — that level is reserved for
when the Factors above (not sensitivity alone) justify full audit-grade
effort, or for an explicit DEEP-mode/release-audit request. Move at
most one level up or down from this default per the Factors — moving
further than that means the factors driving it are severe enough to
warrant explicitly saying so, not applying this table mechanically.

Budget and sensitivity can disagree in *degree* this way — a related,
but not identical, precedent to `plays/security-change-detection.md`'s
MODERATE section's relationship with `skills/security-design`'s
activation list (that one is a one-directional trigger — design either
runs or it doesn't, and a MODERATE label can only add the requirement,
never remove one `security-design`'s own list already imposed; budget
can move in either direction, since effort-sizing has no equivalent
"already triggered, can't be un-triggered" floor of its own — the
actual floor budget can't cross is "The floor this play cannot lower"
below, not classification itself):

```text
HIGH sensitivity (default: ELEVATED)
+ internal-only admin tool
+ strong baseline confidence
+ small, localized change
+ well-understood framework control
    -> FOCUSED budget — moved one level down from the HIGH default.
       Note what this does NOT do: an admin-only tool still touches a
       privileged operation (the Privilege factor) and typically has a
       whole-admin-surface blast radius if compromised — those factors
       argue for staying at ELEVATED or higher. This example only holds
       when the specific change is narrow enough (e.g. a copy-editing
       fix to an admin page's label) that Privilege/Blast radius don't
       apply with any force to the change itself, separately from the
       surface it lives in.

MODERATE sensitivity (default: FOCUSED)
+ internet-facing endpoint
+ sensitive customer data
+ low baseline confidence
+ shared, central service
    -> ELEVATED budget — moved one level up from the MODERATE default.
       "Shared, central service" alone already justifies ELEVATED per
       "Changed attack-surface centrality" above; the other three
       factors reinforce that same conclusion rather than pushing
       further to AUDIT, since AUDIT is reserved for when the change
       itself (not just the surface it touches) warrants full
       audit-grade treatment.
```

## The floor this play cannot lower

**Budget refines effort allocation — it never reduces a mandatory
requirement.** `plays/finding-validation.md`'s independent validation
for every HIGH/CRITICAL candidate, `plays/security-gate.md`'s
BLOCK-level outcomes, `plays/security-change-detection.md`'s
HIGH-sensitivity required workflow, and an explicitly requested `DEEP`
review mode's own mandatory *activity* checklist (`plays/code-review.md`'s
architecture analysis, threat model, full scanner run, manual review of
every security-sensitive area, independent validation of every
HIGH/CRITICAL candidate, configuration review, dependency review, and
complete security report) all apply in full regardless of what level
this play assigns. A `MINIMAL`-budget change that unexpectedly turns up
a HIGH/CRITICAL *candidate* still requires full independent validation
before it can be called `CONFIRMED` (skipping straight to `CONFIRMED`
without that step is exactly the shortcut `plays/finding-validation.md`
exists to prevent), and still gates the same way once validated. A
`MINIMAL`-budget change reviewed under an explicitly requested `DEEP`
mode still performs every one of that mode's activities and still loads
everything those activities require (see "Context budget" below for the
loading guarantee specifically — this section covers *whether an
activity happens at all*, not how much it loads, which is that other
section's claim alone, to avoid two sections making overlapping claims
about the same thing). Budget affects how much scrutiny is applied
within an activity that happens regardless, not whether it happens, and
never removes an activity a mode already committed to performing.

## Context budget

**Review mode decides *which* domains are in scope; this play only
decides how much material to load *within* that scope — it never
expands the domain set mode already fixed.** For a `TARGETED`-mode
review, that set is whatever `skills/security-change-detection`
identified; for QUICK/STANDARD, whatever `skills/security-review/SKILL.md`'s
"Where to look next" table calls for at that mode (the same table
`plays/code-review.md` itself points to for this — see that play's
`TARGETED` note); for DEEP mode, everything DEEP mode already requires.
This play's levels only control *depth* within that fixed set:

```text
MINIMAL/FOCUSED   the play(s) for the identified domain(s), reference
                  material only as needed to resolve a specific
                  question — this is the baseline depth, not a
                  reduction from anything

ELEVATED          the identified domain(s)' full depth of reference
                  material, plus directly-connected attack-surface map
                  neighbors of the changed node — consumed at
                  skills/security-review/SKILL.md's "Attack surface
                  identification" step, where map data is actually read.
                  When a neighbor falls inside the domains mode already
                  selected, this adds depth and immediately-adjacent
                  context, not new domains. When a neighbor falls
                  *outside* those domains, do not silently load it
                  (budget never expands the domain set) and do not
                  silently drop it either (it is still a real structural
                  signal) — since domain selection
                  (`plays/secure-development-workflow.md`'s "Select
                  relevant security domains" step / this skill's Scope
                  step, both already completed by the time this step
                  runs) does not re-run mid-review, record the neighbor
                  as a noted, unresolved cross-domain signal in this
                  review's completion summary or the relevant finding's
                  evidence section (whichever exists), the same way
                  `plays/security-impact-analysis.md`'s `POTENTIAL`
                  classification surfaces something for confirmation
                  rather than deciding it either way — do not silently
                  drop it just because there is no automatic re-selection
                  mechanism

AUDIT             whatever DEEP review mode already requires loading;
                  this level doesn't add anything mode wasn't already
                  going to load
```

A `MINIMAL`-budget change under `DEEP` review mode (an explicit
release audit that happens to touch nothing security-sensitive) still
gets everything DEEP mode requires — budget never overrides what mode
already committed to loading, in either direction. See "The floor this
play cannot lower" above for the equivalent guarantee over DEEP's
*activities*, not just what gets loaded — the two are different claims
and both hold.

## Applicability matrix: which sensitivity/mode combinations actually compute and apply a budget

`skills/security-change-detection` is usually invoked from
`plays/secure-development-workflow.md`'s proactive workflow, but it also
has its own independent entry points (its own `SKILL.md` "When to use,"
a directly-callable subagent wrapper) — a user or agent *can* run it on
its own outside that workflow. What this play's computation actually
depends on is narrower: **this play's own workflow-driven computation
point** (`plays/secure-development-workflow.md`'s "Determine review
budget" step) only ever receives a sensitivity value from that
workflow's own classification step, and an explicitly requested
`QUICK`/`STANDARD`/`DEEP` review (`plays/code-review.md`'s "Review
modes") never passes through that workflow step at all — see that
workflow's own "This does not replace explicit workflows" section and
`plays/code-review.md`'s `TARGETED` note ("Not something a user picks
explicitly... it's the mode the proactive workflow uses on its own").
So *this play's* sensitivity-driven computation and an
explicitly-requested mode do not combine, even though the classifier
itself can be invoked independently for other purposes; the table below
reflects that narrower claim rather than forcing 16 independently-computed
cells, and does not restate the actual MINIMAL/FOCUSED/ELEVATED/AUDIT
values already defined in "Default starting point" above — only where
(or whether) that lookup is ever reached. If a sensitivity value from an
independent classifier invocation is available when an explicit
`QUICK`/`STANDARD`/`DEEP` review is also requested, "Explicit mode"
below's Factors-adjustment step is where a reviewer can fold that
information in manually — it does not change which entry point computes
the starting default.

```text
          QUICK/STANDARD/DEEP (explicit)     TARGETED (proactive workflow)
NONE      N/A — sensitivity not computed     No live review exists to scope:
          for an explicit request; see       security-change-detection's NONE
          "Explicit mode" below              action is "no security workflow...
                                              do not run a scanner, do not load
                                              a play." The NONE row above is a
                                              lookup definition, never applied.
LOW       N/A, same reason                   Only a lightweight diff check
                                              runs, not a formal targeted
                                              review — no live review to scope
                                              unless the check surfaces
                                              something that re-classifies the
                                              change higher first.
MODERATE  N/A, same reason                   REACHABLE — computed at
                                              plays/secure-development-
                                              workflow.md's "Determine review
                                              budget" step, applied at
                                              skills/security-review/SKILL.md's
                                              Scope, Attack surface
                                              identification (ELEVATED's map-
                                              neighbor pull, when reached —
                                              see "Context budget" below), and
                                              Manual semantic analysis steps.
                                              Value: "Default starting point"
                                              above.
HIGH      N/A, same reason                   REACHABLE, same entry point and
                                              same three consuming steps.
                                              Value: "Default starting point"
                                              above (typically ELEVATED,
                                              making the Attack surface
                                              identification step's
                                              map-neighbor pull actually
                                              apply here in practice).
                                              Mandatory security-design
                                              (pre-code HIGH) is a separate,
                                              budget-independent gate — see
                                              "The floor this play cannot
                                              lower".
```

### Explicit mode: computed directly at the Scope step, not via the workflow

`QUICK`/`STANDARD`/`DEEP` never reach `plays/secure-development-workflow.md`'s
"Determine review budget" step — that step only exists on the proactive
workflow's path. `skills/security-review/SKILL.md`'s own "Scope" step is
the one entry point these three modes do reach, and computes a budget
directly there, without a sensitivity input:

```text
QUICK (explicit)      -> FOCUSED — no sensitivity signal exists to
                          escalate or de-escalate from; see "Levels"
                          above for why FOCUSED is the right default
                          absent one
STANDARD (explicit)    -> FOCUSED, same reasoning
DEEP (explicit)         -> AUDIT — see "Context budget" above for why
                          this is a no-op safety cap, not a new
                          restriction, and "Default starting point"
                          above ("...or for an explicit DEEP-mode/
                          release-audit request") for AUDIT already
                          being defined to cover exactly this case
```

The Factors above can still adjust this starting point if information
relevant to them is available (e.g. a known baseline confidence fact).
**The "move at most one level up or down" cap in "Default starting
point" above applies to the *sensitivity*-driven default specifically —
it exists to keep a Factor from silently overriding a considered
sensitivity classification. It does not apply here**, since these three
modes' defaults have no sensitivity classification to bound movement
against. An explicit `DEEP` request that turns out to touch nothing
security-sensitive can move from the `AUDIT` starting point all the way
down to `MINIMAL` if the Factors genuinely support it (this is the exact
scenario "Renamed from the naming..." above and `tests/validation/v3-review-budget-test-cases.md`'s
case 7/7b exist to test) — absent such a case, `FOCUSED`/`AUDIT` remain
the defaults for these three modes, not derived from a sensitivity label
that was never computed for them.

## Output

This play doesn't introduce its own artifact or finding format — its
output is a level (`MINIMAL`/`FOCUSED`/`ELEVATED`/`AUDIT`) that informs
how much of `skills/security-review`'s workflow to actually spend, and
how much reference material to load while doing it — see "Applicability
matrix" above for exactly which sensitivity/mode combinations reach a
live computation, and where. `AGENTS.md`'s "Before implementing a
meaningful software change" step 6 (proportional targeted review) names
this play as the thing computed from step 5's (re-)classification, not
as an input that itself refines that classification — project
baseline/attack-surface map (also named in that routing summary, at
step 1) are the actual classification-refining inputs; this play is
downstream of classification, not alongside it. See
`tests/validation/v3-review-budget-test-cases.md` for worked traces
through every reachable cell above.
