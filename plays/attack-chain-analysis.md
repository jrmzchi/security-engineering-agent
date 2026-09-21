# Play: Attack Chain Analysis

Authoritative procedure for `skills/attack-chain-analysis`. Formalizes
`plays/finding-validation.md`'s "Vulnerability chaining" section
(individually moderate findings that combine into something more
serious) into a structured record, with explicit fields — it does not
replace or duplicate that section, it gives it a concrete output
format.

## Two other things in this kit already use words this play reuses

- `plays/finding-validation.md`'s "Attack path model" and
  `plays/attack-surface-mapping.md`'s own "Not the same thing as an
  attack-path chain" section both use "chain"/"attack path" for a
  **single finding's** evidence trail (attacker -> input -> ... ->
  impact). This play's "chain" is a **different, larger** unit: a
  sequence of multiple, independently-confirmed *findings* that
  combine. A single finding's attack-path chain is one input to this
  play, not the same thing this play produces.
- `NEEDS_VERIFICATION` is reused here for a chain whose linkage can't
  currently be confirmed (see "Confidence" below) — the same status
  `plays/attack-surface-mapping.md` already reuses for an unresolvable
  graph node/edge. Same collision test as that reuse and
  `plays/review-budget.md`'s renaming decisions
  (`plays/review-budget.md`'s "Levels" section): would the same object
  ever carry two conflicting meanings at once? A chain, a finding, and
  a map node are three different objects that never merge into one, so
  a `NEEDS_VERIFICATION` chain, a `NEEDS_VERIFICATION` finding, and a
  `NEEDS_VERIFICATION` map node can all exist in the same report at the
  same time without any of them being ambiguous about which one is
  meant.

## When a chain is real

`plays/finding-validation.md`'s existing guardrail already says the
core rule: **do not artificially combine unrelated findings just to
inflate severity — a real chain requires that exploiting the first
finding actually enables reaching the second.** Keep that "enables
reaching" requirement — it is what makes this a *necessity* test, not
just a *helpfulness* test. State it per consecutive pair of steps as a
concrete precondition: not "this seems related" but "step 1 puts an
attacker-controlled file on disk; step 2's execution behavior is what
turns that file into running code, and step 2 has nothing to execute
without step 1 having put something there first." If a step would
still be reachable and still produce its own impact with an earlier
step removed, that earlier step isn't a required link in this chain —
it may still be worth reporting as its own finding, just not as part of
this chain.

## Required fields

```text
Chain ID              stable identifier, e.g. AC-001 (see "Stable IDs"
                      below)
Preconditions         for each consecutive pair of steps, the specific
                      fact the earlier step establishes that the later
                      step's reachability actually depends on — not
                      merely something the later step benefits from
Ordered steps         the component findings, in the order exploiting
                      them actually proceeds — reference each by its
                      existing finding ID/title, do not restate its
                      content (see "Deduplication" below); every step
                      must be an actual finding with its own record,
                      not a non-vulnerable fact folded into the chain
Boundary transitions  which trust boundaries (see
                      plays/attack-surface-mapping.md's TRUST_BOUNDARY
                      node type, when a map exists) the combined path
                      crosses that no single step crosses alone
Combined impact         what the full chain achieves that no individual
                      step achieves by itself
Confidence              HIGH / MEDIUM / LOW, or NEEDS_VERIFICATION —
                      see "Confidence" below
Chain severity          see "Chain severity" below — not simply the
                      highest severity among the component findings
```

## Confidence: reuses `finding-validation.md`'s scale, not a new one

Same discipline as `plays/cross-file-data-flow.md`'s hop-by-hop
confidence: this is not a fourth scale, and the illustrations below are
examples of what commonly drives each level for a chain specifically,
not an exhaustive redefinition — `plays/finding-validation.md`'s own
definitions remain authoritative for anything these don't cleanly
cover.

A chain's confidence is bounded by the **lower** of two things: (a) the
weakest confidence among its own component findings, and (b) how
directly evidenced the preconditions linking them are. A chain built on
a MEDIUM-confidence component finding cannot itself be HIGH confidence,
no matter how solid the linkage between steps is — the chain can never
be more certain than its shakiest individual link:

```text
HIGH      every component finding is itself HIGH-or-better confidence,
          and every precondition linking consecutive steps is directly
          evidenced, with no gap

MEDIUM     most of the above holds, but one component finding is only
          MEDIUM confidence, or one linking precondition is inferred
          rather than directly observed

LOW        a component finding is LOW confidence, or a required linking
          precondition can't currently be confirmed
```

A `LOW`-confidence chain follows the same rule as any other
LOW-confidence claim in this kit: don't present it as a confirmed
combined impact — use `NEEDS_VERIFICATION` and state which component
finding or which precondition needs resolving. A chain still gets a
record in that case (see "Output" below) — `NEEDS_VERIFICATION` is a
result, not the absence of one.

## Chain severity ≠ max(component severities)

`plays/security-gate.md`'s aggregation across a batch of *unrelated*
findings is legitimately worst-of-N (see that play's precedence order
and worked examples) — that's the right rule when findings don't
interact. A chain is different: the findings *do* interact, so their
combination can produce an impact more severe than any component's
individual severity, and severity must be assessed against the combined
path, not computed by taking the max:

```text
Component findings:
  Unrestricted file upload (no type/content validation)
      MEDIUM alone — an attacker can store an arbitrary file, but
      impact depends entirely on where it ends up and whether anything
      will ever execute it
  Uploaded files served from a directory the web server will execute
  as code (a static-file-handler misconfiguration)
      MEDIUM alone (or LOW/INFORMATIONAL — a configuration exposure
      with no attacker-supplied content to point at yet) — this alone
      doesn't demonstrate any concrete impact, since it needs
      something an attacker actually controls in that directory

Chain AC-001: unrestricted upload -> execution-enabled upload
directory
  Precondition: step 1 is what puts attacker-controlled content on
  disk at all; step 2's execution behavior is what turns that stored
  file into running code — neither step alone reaches "arbitrary code
  runs," only the combination does
  Combined impact: remote code execution
  Chain severity: CRITICAL — RCE is CRITICAL under
  plays/finding-validation.md's severity model (system privileges,
  potentially full compromise) even though neither component finding
  reached that severity by itself
```

Weigh, for the chain as a whole, the **same factors**
`plays/finding-validation.md`'s severity model already lists for a
single finding — exploitability, required privileges, user
interaction, data sensitivity, blast radius, system privileges,
internet exposure, business impact — applied to the combined path
rather than to any one step (e.g. "internet exposure" asks whether the
*full chain* is reachable from the internet, not just its first step).
This play adds exactly one factor that model doesn't have, because it
doesn't apply to a single finding: **persistence** — whether the access
or capability gained by completing the chain outlives the specific
request/session that triggered it (a chain that plants a persistent
backdoor is worse than one whose effect ends when the connection
closes, even at the same nominal impact). Everything else is that
model's existing list, not a new one.

A chain is not automatically more severe than its worst component — a
chain of two LOW findings that combine into a still-LOW outcome is a
real chain with an unremarkable severity; don't inflate severity just
because a chain exists.

## Deduplication

Report each component finding once, in the normal findings list, using
`templates/finding.md` as always. The chain is an *additional
interpretation layer* on top, not a restatement:

```text
## Findings

[MEDIUM] Unrestricted file upload (no type/content validation)
[MEDIUM] Uploaded files served from an execution-enabled directory

## Attack Chain AC-001

Steps: Unrestricted file upload -> execution-enabled upload directory
Combined impact: remote code execution
Chain severity: CRITICAL
```

Do not paste each finding's full content into the chain record — a
reader who wants the detail behind "Unrestricted file upload" reads
that finding, not a duplicate embedded in the chain.

## Stable IDs

`AC-` prefix. This borrows only
`plays/attack-surface-mapping.md`'s "don't renumber existing IDs when
the map grows" rule, not its preference for a semantic key over a bare
sequence number — a chain has no natural semantic key the way a route
path or symbol name gives a map node one, so a plain sequence number
(`AC-001`, `AC-002`, ...) is the right choice here specifically.

## Relationship to Adversarial Validation

A multi-finding attack chain is one of the cases
`plays/adversarial-validation.md` requires its bypass checklist for by
default — applied to the **preconditions and controls between steps**
(can step 2 be reached some other way that skips step 1? does a
sibling path bypass whatever makes this chain work?), not to
disproving the chain's already-established combined impact — that's
this play's own confidence/severity assessment above, not adversarial
validation's job (see that play's "A different objective from ordinary
validation, not more of the same" section for why confirming plausibly
and hunting for a bypass are different objectives assigned to
different places). This play establishes the chain record that
checklist would be applied to; it does not itself perform that
checklist.

## Relationship to the Security Gate

A chain's severity independently drives a gate outcome — the
worked example above is exactly this case: two MEDIUM component
findings, neither of which alone reaches `plays/security-gate.md`'s
BLOCK threshold, combine into a CRITICAL chain that does. See that
play's "Default policy" table (the chain-record rows) and its "Inputs
this play consumes" section for how a chain's severity is gated in
addition to, not derived from, its component findings' severities —
including how an unresolved (`NEEDS_VERIFICATION`-confidence) chain is
gated the same as an unresolved HIGH/CRITICAL candidate.

## Wired consumers

`agents/security-team-lead.md`'s step 10 ("Identify chained
vulnerabilities") now references this play for the structured `AC-NNN`
record, alongside `plays/finding-validation.md`'s "Vulnerability
chaining" for the core concept.

`templates/security-report.md` has an `## Attack Chains` section,
placed directly after the severity-tier findings sections and before
`## Rejected Candidate Findings` — matching "Deduplication" above,
and covering a chain at any Confidence level, including
`NEEDS_VERIFICATION` (see "Confidence" above for why that's a result,
not an absence of one — a chain carries no `CONFIRMED` status of its
own to gate inclusion on).

`skills/security-review/SKILL.md`'s workflow (step 7) and `AGENTS.md`'s
routing summary (step 7) both call this play once multiple findings
are CONFIRMED in the same area, before deciding which of them
additionally need `plays/adversarial-validation.md`'s checklist — see
that play's "Relationship to Adversarial Validation" above for why a
discovered chain is itself one of that checklist's triggers.

## Output

Use `templates/attack-chain.md`. A chain record references component
findings (`templates/finding.md`) by ID/title; it does not replace
them, and every component finding is still reported and gated
individually regardless of whether it's also part of a chain.
