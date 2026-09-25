# V4 Design — Adaptive Security Intelligence & Orchestration

> **V4 release note.** This document is kept as the design specification
> that `tools/context_manifest/` and `tools/feedback_store/` cite by section
> number. The "Status" paragraph below is historical: the design was
> implemented in V4 (see `README.md`'s "V4 components" for what ships and
> what is experimental). Statements here about token, cost or efficiency
> benefits are design hypotheses, not release claims; none was
> demonstrated. Other planning records it names (`implementation-batches.md`,
> `measurement-plan.md`, review-round dispositions and verification logs)
> are not part of this release.

**Status: design proposal, not implemented, not approved for
implementation. Revised across three rounds of independent review,
plus nine direct correction batches (the second through ninth
responding to independent review rounds four through eleven in order —
see `context-manifest-schema.md`'s header, `round4-disposition.md`
through `round11-disposition.md` for the item-by-item record of what
each round found and how each item was fixed). **Five consecutive
rounds (4-8) found a defect in the same mechanism** — the Group 3
domain-applicability condensed condition table and the worked examples
that applied it — each time a condition or restatement checked against
a subset, not the complete list, of another file's content. Round 8
recommended a structural change rather than a seventh prose-patching
round; **you decided**: remove the condensed condition table entirely,
point directly at each play's own Scope section as the sole
authoritative source, and back this with an executable coverage check
in `implementation-batches.md` Batch 0 rather than a fixture test that
merely re-guards a copy. This is implemented in the seventh correction
batch — see `context-manifest-schema.md`'s "Authoritative source, per
domain" table and execution rule, and `implementation-batches.md`
Batch 0's new criterion 7. **A tenth independent review round then
confirmed the redesign itself closes the recurring pattern, but found
two Majors at its edges — both self-inflicted within that same
batch**: Batch 0's own criterion 6(a) still hardcoded a fact count for
Case 1 that the same commit had changed, and criterion 7 never defined
"discriminating" as requiring per-item isolation (the manifest's flat
`domains` array makes a shared, non-isolated fixture pass trivially).
The eighth correction batch fixes both, decides the isolation-vs-
schema-change question round 10 raised (isolation, no schema change —
Occam's razor, criterion 7b already permits parameterized fixtures to
absorb the cost), and closes two smaller gaps in Case 1 itself
(ZIP/archive extraction, storage location) so it remains valid as
criterion 6(a)'s own fixture source. **An eleventh independent review
round then confirmed both Majors fully closed and found only two Nits
(a stale count in a correction note, a summary line naming half of what
its own fact covers) plus a Minor completeness gap in criterion 7e's
trigger-host wording (naming the two `consistency-check` scripts didn't
address that neither has an automatic trigger today, or that their own
authoritative play treats every existing category as advisory while
this new check is a hard fail) — the ninth correction batch fixes all
three and explicitly stops the review cycle on this text**, per three
consecutive rounds (9, 10, 11) confirming the redesign holds with only
progressively smaller self-inflicted issues remaining; the next
productive step is implementing and running Batch 0's criterion 7, not
a twelfth reading.** See
`v4-staging-decisions.md` for what V3 Slim actually proved and what
that does and does not change about V4's own plan — this document does
not restate that narrative. First revision: the original manifest
validity check could
not detect a manifest that omitted an entire required security domain.
**Second revision**: the domain/sensitivity floor redefined as an
independent, non-Jev *reasoning* pass (never a mechanical check);
Evidence Reuse gained a check for whether a rejection's specific cited
reason, not just its own location's code pattern, still holds. **Third
revision**: section 4.1's built-in-layer table corrected to match
section 3's item 0 rather than contradict it; a `reviewMode` field
added; item 0's Jev-path cost stated honestly as additional, not free;
Evidence Reuse's occurrence identity redefined over the full
reachability path to a sink, not the sink alone. **Fourth revision,
after a third independent-review round confirmed the reachability-path
fix works but found a different axis of the same identity definition
still had gaps, and found that keeping review-budget's two entry points
conceptually separate inside the manifest schema had produced three
more real defects at their seam**: occurrence identity also requires
matching `candidateShape.category` and exact `{path, symbol}` pairs
(not file paths alone), and may only be built from a HIGH-confidence
trace; and — **the review-budget dual-entry-point question (formerly
section 7's open item) is now `[DECIDED]`**: merged into one
`computeReviewBudget` function, per your explicit choice, after three
independent-review rounds converged on this exact seam as the recurring
source of defects. **Fifth revision, a direct correction batch (not
prompted by a new review round) responding to explicit instruction to
re-check against V3's actual text rather than this design's own prior
descriptions**: section 4.1's DEEP row (and section 3a of
`context-manifest-schema.md`) corrected from "all ten domains,
unconditionally" to "every domain the target project's own architecture
evidence shows applicable," matching `plays/code-review.md`'s actual
"every security-sensitive area" wording rather than a count this design
had invented; section 4.2 now `[DECIDED]`s Option A for Jev's domain
role (never fewer than the floor, full stop) with the Option A/B
comparison and rejection reasoning made explicit rather than left
implicit; `measurement-plan.md` gained an early feasibility gate
(section 3a there) and `implementation-batches.md` gained Batch 2.5 to
enforce it before further batches proceed. **Sixth revision, fixing a
fourth independent review round's 2 Blocker + 7 Major findings against
the fifth revision**: section 3a's algorithm split into three groups
instead of one uniform rule — `code-review`/`configuration-security`/
`dependency-security` unconditionally applicable to DEEP (matching
`plays/code-review.md`'s own DEEP mandatory-activity list, which the
fifth revision had still excluded `configuration-security` from);
`authentication`/`authorization`/`secrets-security` changed from
presence-based to applicable-by-default-unless-positively-confirmed-
absent (the fifth revision's presence-based rule for these three
reintroduced, at DEEP's repo-wide scope, the exact "absence of a
control IS the risk" defect this design already fixed once at the
item-0/diff-scope level); Case 2's domain count corrected from an
under-loading 7-of-10 to the case's own premise's actual 9-of-10;
section 4.2's Option A floor citation corrected to name item 0 for
TARGETED/QUICK/STANDARD and section 3a for DEEP, since item 0 alone
does not bind a DEEP manifest at all; `implementation-batches.md`'s Batch 2 criterion 4 corrected
from requiring domains to match EXACTLY to requiring never fewer than
the floor (matching what section 4.2 already permits — a superset);
Batch 0 gained explicit acceptance criteria for section 3a and for
wiring `skills/security-review/SKILL.md` step 5's actual budget/depth
consumption; Batch 2.5's go/no-go criterion corrected to require a PASS
(or a PARTIAL with the losing case descoped) before batches 3-5
proceed, not merely a recorded verdict of any kind; `measurement-plan.md`'s
recall condition corrected to run against the actual `tests/fixtures/`
corpus rather than a claim that the smaller representative task set
already spans it; a new `v4-staging-decisions.md` document was added,
recording that V3 Slim proved an architecture cleanup with one small
content reduction and a net kit-wide increase, not a token-efficiency
result, and that no V4-Slim phase is scheduled or required before V4
implementation begins. Full item-by-item record: `round4-disposition.md`.
**Seventh revision, fixing a fifth independent review round's 1
Blocker + 2 Major + 1 Minor findings against the sixth revision**:
section 3a's Group 2 rule for `authentication`/`authorization` now
requires the invocation-context fact (confirmed local-only/
already-authorized invocation) explicitly, not only the "no session
code"/"no restricted resource" facts — Case 1b's own worked example
had shown these two domains "unaffected" by that invocation-context
fact becoming `UNKNOWN`, which was wrong on the corrected rule's own
terms (authorization's exclusion argument already implicitly assumed
confirmed local invocation; the earlier text just didn't say so), and
reproduced the exact "absence isn't evidence of safety" failure this
whole correction round exists to close, in the single most common
real-world case (invocation context genuinely undocumented); Case 2's
premise rewritten from "no *separate* browser-rendered UI" (which
conceded some existed) to an unambiguous bearer-token, no-HTML-anywhere
API, so its 9-of-10 count is actually supported by its own premise;
Batch 2 gained a fifth criterion running an explicit DEEP request
through both producers, since the existing criterion 4's task set
(T1-T5/T4b, all diff-scoped) could never actually exercise section 3a's
floor on the Jev path despite an earlier draft citing it as covered.
Full item-by-item record for this round: `round5-disposition.md`.
**Eighth revision, fixing a sixth independent review round's 2 Major +
1 Minor findings against the seventh revision**: Case 2's "renders no
HTML anywhere" premise defeated six of `plays/web-security.md`'s eight
Scope items but silently left CORS misconfiguration and open redirect
(neither of which requires HTML) unaddressed while still claiming the
whole domain excluded — the premise now explicitly addresses all eight
items (no cookie-based auth for CSRF, no CORS headers/cross-origin
browser caller for CORS, no redirect responses of any kind for open
redirect, no HTML for the rest); `v4-staging-decisions.md`'s claim that
the snapshot has "general silence" on V3 Slim's numbers was verified
false against the snapshot's own `定位` section, which states those
exact numbers and the same no-overall-reduction constraint verbatim —
corrected to state the snapshot is the ORIGINAL source of that
constraint, not silent on it; Batch 2's new criterion 5 had a false
attribution ("measurement-plan.md's T-series already uses this
combination elsewhere") corrected to state it plainly as a new sample
choice. Full item-by-item record: `round6-disposition.md`. **Ninth
revision, fixing a seventh independent review round's 1 Major + 2
Minor + 1 Nit findings against the eighth revision, plus a structural
fix**: Case 2's `data-security` justification ("SQL/database") was
verified to satisfy neither Group 3's own condition, `plays/data-security.md`'s
actual scope (cryptography-only, no database item), nor
`skills/security-review/SKILL.md`'s domain table (SQL injection routes
to `plays/code-review.md`) — corrected to state the actual flagged
sensitive-data fact the domain's condition requires. **Root-cause fix,
not another Case 2 patch**: the Group 3 table's `web-security` row
itself was found under-specified — "renders HTML" does not cover CORS
misconfiguration or open redirect, which is the actual reason Case 2's
web-security exclusion needed patching three consecutive times; the
row is now corrected to state all three disjuncts its own target
play's scope actually requires, and Case 2 is rewritten to point at
this corrected row instead of re-deriving the answer from
`plays/web-security.md` a fourth time, per two independent reviewers'
(rounds 6 and 7) identical recommendation to stop patching this one
worked example prose-by-prose. Full item-by-item record:
`round7-disposition.md`. **Tenth revision, fixing an eighth independent
review round's 3 Major + 1 Minor findings against the ninth revision**:
the corrected `web-security` row was still incomplete (missing a
disjunct for CSRF, which needs no HTML, only ambient/cookie credentials
plus a state-changing operation — the same "condition checked against a
subset" shape recurring a fifth time); independently, the SAME
under-specification pattern was found, for the first time actually
stress-tested, in all three of the other Group 3 rows
(`api-security`/`data-security`/`file-security`) — all four rows
corrected against each cited play's complete Scope section, plus a
standing safety net (an unmatched Scope item now defaults the domain to
applicable, not excluded); a correction note in `round6-disposition.md`
was found to be itself false (it claimed a deleted sentence was "kept
unedited," when it had been deleted in that same commit) — restored.
Round 8 recorded an explicit open question for you (reduce the affected
table to pointers with no condition copy, versus keep the copies backed
by an executable fixture test). Full item-by-item record:
`round8-disposition.md`. **Eleventh revision, implementing your decision
after a ninth independent review round's 2 Major findings against the
tenth revision (both in the area round 8 flagged as unresolved)**: a
ninth round found the standing safety net added in the tenth revision
was itself ambiguous and conflicted with this document's own fixed
domain counts, and — stress-testing all 42 Scope items across the four
Group 3 plays for the first time — found three more uncovered items
(`data-security`'s "Insecure random generation," `api-security`'s
"Request smuggling indicators," one `file-security` "Temporary files"
sub-case), the third defect of this shape independently confirmed after
round 8 itself. **You decided the structural question round 8 raised**:
option 3 — pure pointer as the design document's authoritative
relationship, with an executable per-item coverage check in
`implementation-batches.md` Batch 0, rather than either keeping a
condition copy (with or without a fixture backstop) or a bare pointer
with no verification mechanism at all. `context-manifest-schema.md`'s
Group 3 section no longer states any condensed condition — it names
each domain's authoritative source (the cited play's own Scope section)
directly, states the execution rule (check every item, default to
applicable on any uncertainty), and the worked examples are explicitly
relabeled illustrative rather than authoritative. Case 2 recomputed
under this rule, fixing a Minor round 9 found in the same pass (the
prior premise's "renders no HTML" did not establish "serves no
browser-executed content," since a download response could still serve
inline-renderable content without an explicit attachment disposition).
`implementation-batches.md` Batch 0 gains criterion 7: a symmetric,
both-directions coverage check between each play's live-parsed Scope
section and a maintained fixture map, with the three round-9 gaps
required as regression entries from Batch 0's first implementation.
Full item-by-item record: `round9-disposition.md` (full original
review-agent report preserved verbatim in
`round9-full-report.md`, per explicit instruction not to keep only a
summary). **Twelfth revision, fixing a tenth independent review round's
2 Major + 3 Minor findings against the eleventh revision — the redesign
itself confirmed sound, two gaps found at its edges, both introduced by
the eleventh revision's own changes**: Batch 0's criterion 6(a) still
hardcoded "all five positive-confirmation facts" for Case 1 after this
same batch had extended it to eight facts — a copy-vs-source drift
inside the very acceptance criterion meant to guard against that
pattern, now fixed by never hardcoding a count; criterion 7 never
defined "discriminating" as requiring per-item isolation, which the
Context Manifest's flat `domains` array (no per-item attribution) makes
necessary — a shared, non-isolated fixture would pass every mapped item
trivially. **Decided**: require fixture isolation (removing an item's
specific evidence must remove the domain), not a manifest schema
change, per round 10's own Occam's-razor recommendation. Also fixed:
the `api-security` "Request smuggling" regression entry's "independent
of whether it exposes [a surface]" literally permitted a
non-discriminating fixture, reversed round 9's own counterexample, and
is corrected to "must NOT expose"; criterion 7's run-frequency clause
named no trigger host, now wired to the two `consistency-check`
scripts; Case 1 gained two more facts (ruling out archive extraction
and predictable storage locations) so it remains a valid, fully-
supporting fixture source for criterion 6(a)'s own 3-of-10 claim, since
its prior "item-by-item" claim was self-contradicted and had a genuine
gap. Full item-by-item record: `round10-disposition.md` (full original
report preserved verbatim in `round10-full-report.md`). **Thirteenth
revision, fixing an eleventh independent review round's 2 Nit + 1 Minor
findings against the twelfth revision, and stopping the review cycle on
this text**: an eleventh round independently recomputed Case 1's
3-of-10 and Case 1b's 6-of-10 from every one of the 42 Scope items and
confirmed both Majors from round 10 fully closed, could not construct a
new counterexample against the isolation-fixture mechanism, and found
only two Nits (a correction note's own stale fact-count, a summary line
naming one of the two Scope items its own fact already covered) plus a
completeness gap in criterion 7e's trigger-host wording — naming the
two `consistency-check` scripts didn't address that neither has an
automatic trigger today, or that `plays/repository-consistency.md`
(their authoritative procedure, out of scope for this planning batch to
edit) treats every existing category as advisory recall while this new
check is a hard fail. All three fixed. **No twelfth review round is
dispatched**: three consecutive rounds (9, 10, 11) confirmed the
redesign holds with only progressively smaller, self-inflicted issues
remaining, and round 11's own remaining finding surfaced only from
reading the check's *target* (the scripts and their authoritative play),
not from re-reading this design document again — the next productive
step is implementing and running Batch 0's criterion 7, not further
prose review. Full item-by-item record: `round11-disposition.md` (full
original report preserved verbatim in `round11-full-report.md`). See
`context-manifest-schema.md` sections 3, 3a, and 5.1 for the full
mechanics and every concrete counterexample each revision was built to
catch, and section 7 below for the merge decision itself. Sections 5
(Jev's permission boundary), 6 (AD/SSO scope), and the position paper's
own requirements are unchanged across all thirteen
revisions. The sole
authoritative requirement source is
[`v4-position-paper.md`](v4-position-paper.md) (immutable snapshot;
`[CORRECTED, per a ninth-round independent review Nit]`: this line
previously labeled `d356a2f1484afb72a8a8b9c67f4900962cdadc187dfa2aafd64518628a82baeb`
as the snapshot file's own hash — it is actually the hash of the
*original source file* the snapshot was copied from, exactly as
`v4-position-paper.md`'s own header already states; the snapshot file
itself (header block plus verbatim copy) hashes differently, since it
is a larger file. The two were independently verified byte-for-byte
identical after the header block during round 9's review — this was a
labeling error, not evidence of tampering).
This document elaborates and proposes; it never overrides that
snapshot. Every claim below is tagged:

```text
[REQUIRED]     stated directly in the position paper — not open for
               this document to reinterpret
[PROPOSED]     this document's own recommendation, not yet confirmed
[OPEN]         one of the position paper's six 待設計決策, or a new
               question this design surfaced — requires your decision
```

Untagged prose is explanatory framing, not a claim of any of the three
kinds above.

## 1. Overall architecture and data flow

```text
Deterministic input layer
  user task, git diff (incl. untracked files), files, tech stack,
  scanner availability (skills/security-change-detection +
  plays/scanner-selection.md's existing discovery, unchanged)
  + existing Adaptive Project Security Intelligence records
  (.security/baseline.json, .security/attack-surface.json,
  new .security/feedback.json -- see context-manifest-schema.md)
        |
        v
Manifest-producing decision layer (exactly one of the two runs per
review; see section 4)
  [Jev Runtime Decision Layer]   or   [Built-in deterministic layer]
        |                                    |
        +------------------+-----------------+
                           v
              Context Manifest (typed, checkable --
              see context-manifest-schema.md)
                           |
                  Manifest validity check
                  (deterministic, never Jev -- section 4.3)
                    pass |         | fail
                         |         v
                         |   fall back to built-in layer,
                         |   log degradation reason,
                         |   re-validate (always passes,
                         |   since built-in IS the floor)
                         v
              skills/security-review's existing workflow
              (Scope -> Architecture discovery -> Attack surface
              identification -> Automated scanners -> Manual semantic
              analysis -> Potential findings -> Validation ->
              Final findings) -- UNCHANGED authoritative procedure,
              now driven by the manifest's domains/budget/priority
              instead of computing them inline every time
                           |
              +------------+-------------+
              v                          v
   Candidate findings              Adaptive Project Security
   (scanners: candidate                Intelligence updated
   evidence only, per                (new/changed baseline facts,
   plays/finding-validation.md,        attack-surface nodes,
   unchanged)                          feedback records --
              |                        Selective Invalidation/
   Independent Validation              Revalidation, section 3)
   (skills/security-validate,
   unchanged authority)
              |
   Attack chain / adversarial
   validation where triggered
   (unchanged authority)
              |
   Security Gate (unchanged
   authority: PASS/BLOCK/...)
              |
              v
   Completion + feedback: Validator REJECTED reasons, and any
   human-found false negative's root-cause layer, are written into
   the Feedback Learning record (section 3.4) for the *next* review's
   Intelligence layer to consult.
```

The loop closes: Core 2 (Intelligence) feeds Core 1 (Orchestration)'s
next decision; Core 1's execution results feed back into Core 2. This
is not two sequential phases — see section 2.

**Nothing in the execution half of this diagram (candidate findings
onward) is new or changed by V4.** `plays/finding-validation.md`,
`skills/security-validate`, `plays/attack-chain-analysis.md`,
`plays/adversarial-validation.md`, and `plays/security-gate.md` remain
exactly as authoritative and exactly as unmodified as the position
paper requires [REQUIRED — "Scanner 提供候選和機械證據；Claude／Codex、
獨立 Validator 與 Adversarial Validator 負責深度推理與驗證；Security
Gate 依其權威規則給出結果"]. V4's entire footprint is upstream of
"Candidate findings": deciding how much to load and look at, never
deciding what a finding's status is.

## 2. How the two cores interact

The position paper's own structure keeps these as two named cores
(section "兩大核心"), and this design keeps that as its main organizing
axis — a requirement restated directly in chat when this correction
batch was commissioned ("請保持附件的兩大核心為設計主軸"), not a
verbatim phrase from the snapshot itself [CORRECTED, per independent
review: an earlier draft mislabeled this citation's source]. They are
not two independent subsystems that happen to ship together — each is
the other's input and output:

```text
Adaptive Project Security Intelligence  --(facts/nodes/feedback,
    (Core 2: persistent store)           read as decision input)-->
                                                                      Adaptive Security
    <--(new/updated facts, nodes,                                    Orchestration
    feedback records, written as                                     (Core 1: per-review
    execution output)--------------------------------------------    decision + execution)
```

Concretely, this is not a new coupling — V3 already built half of it:
`plays/review-budget.md`'s "Baseline confidence" and "Changed
attack-surface centrality" Factors already read Core-2-shaped data
(`.security/baseline.json`, `.security/attack-surface.json`) to inform
a Core-1-shaped decision (how much budget a review gets). V4's design
job is to (a) make that consultation happen through the Context
Manifest rather than ad hoc, (b) add the write-back direction (Core 1's
execution results updating Core 2, which V3 already does for baseline/
attack-surface facts via freshness re-evaluation, but not yet for
Feedback Learning records — that store doesn't exist yet), and (c)
make Feedback Learning records a first-class Core-2 citizen alongside
baseline facts and attack-surface nodes, not a separate, uncoordinated
mechanism.

## 3. Adaptive Project Security Intelligence

Builds on `plays/project-security-baseline.md`, `plays/attack-surface-mapping.md`,
and `plays/security-impact-analysis.md`'s existing mechanisms rather
than replacing them. See [`context-manifest-schema.md`](context-manifest-schema.md)
for the actual field-level schema; this section covers the four
named mechanisms at a design level [REQUIRED naming, PROPOSED
mechanics].

### 3.1 Evidence Reuse

When a candidate or a decision the Orchestration layer needs to make
matches an existing, still-fresh, in-scope record (a baseline fact, an
attack-surface node, or a feedback record), reuse its conclusion
instead of re-deriving it. This is the same "reuse, don't rebuild"
principle `plays/project-security-baseline.md` and
`plays/attack-surface-mapping.md` already apply to their own facts and
nodes — V4 generalizes it to Feedback Learning records specifically
(V3 has no place to reuse a *rejection reason* today; that gap is what
this batch actually adds).

### 3.2 Selective Invalidation

Reuses `plays/security-impact-analysis.md`'s existing `freshnessOf`
lookup mechanism (a changed-files-set lookup, not a rebuild) as the
default mechanism for every Core-2 record type, including the new
Feedback Learning records. **This is not sufficient on its own for
every Feedback record** — see section 3.5's `invalidationConditions`
discussion; some invalidation conditions are not file-diff-detectable
(a dependency version bump, a configuration flag flip that isn't in a
tracked file). This is flagged as an open design gap, not silently
assumed solved by extending `freshnessOf`.

### 3.3 Selective Revalidation

A record marked `STALE` (existing status name, reused per V3's own
precedent in `plays/project-security-baseline.md`/`plays/attack-surface-mapping.md`)
is not treated as correct, and not treated as automatically wrong
either — it goes back through the same Validator/reasoning procedure a
fresh candidate would, per `plays/finding-validation.md`'s unchanged
authority. **Cached results are never treated as permanently correct**
[REQUIRED, verbatim from the position paper] — this is the mechanical
enforcement of that requirement: a `STALE` record cannot be consulted
by Evidence Reuse (3.1) until it has been Selectively Revalidated back
to a fresh status.

### 3.4 Feedback Learning

When `skills/security-validate` produces a `REJECTED` result (per
`plays/finding-validation.md`'s existing Result vocabulary, unchanged),
record it as a Feedback record: the reason, the evidence, and — new —
an explicit `scope` describing what this rejection does and does not
generalize to (see 3.5). Before treating a new candidate of a similar
shape as fresh, check for a matching, still-valid Feedback record
first; if one exists and passes the stale-reason re-review check
(section 3.5 / `context-manifest-schema.md` section 5), reuse its
conclusion — **the reason must still hold against current evidence
before it can be reused; it is never assumed to hold indefinitely**
[REQUIRED, directly from the position paper's Feedback Learning
bullet].

When a human finds a missed vulnerability (a false negative this
system produced), the required response is not "add one more fixture"
— it is root-cause attribution across four possible failure layers
[REQUIRED framing, PROPOSED attribution mechanics]:

```text
Routing        the classifier/manifest never selected the right
               domain/play for this change at all
Attack surface the map was missing the entry point, control, or sink
               involved
Cross-file flow the flow existed in the map/domain but the multi-hop
               trace (plays/cross-file-data-flow.md) didn't connect it
Reasoning      everything was in scope and traced correctly, but the
               manual semantic analysis step itself missed the
               vulnerability
```

**[PROPOSED]** Recording which of these four a given escalation
resolved to is itself a Feedback-adjacent record (not a rejection
record — a *miss* record), so that a recurring pattern in one layer
(e.g. repeated routing misses for a specific framework's convention)
becomes visible across incidents instead of each one being handled as
an isolated one-off. `implementation-batches.md`'s batch 1 proposes
one representative fixture per layer specifically to prove this
attribution mechanic actually discriminates between the four causes,
not just that a miss got logged somewhere.

### 3.5 Reuse eligibility, stale-reason re-review, and the Validator boundary — revised a third time

V3's `freshnessOf` mechanism answers "did a file this record depends on
change." That is necessary but not sufficient for deciding whether a
Feedback record may be reused, for four distinct reasons — the third
and fourth each found only after a further round of independent review
against the fix for the one before it: (1) a rejection can stop being
true for a reason that is not a tracked file change at all; (2) **a
candidate that merely resembles a rejected pattern at a *different*
code location must never be treated as the same, reusable occurrence**
— reuse requires re-inspecting the actual current code, not matching by
file/method name or vulnerability category alone; (3) **re-verifying
the candidate's own location is not the same as re-verifying *why it
was rejected*** — a rejection frequently depends on code elsewhere (an
upstream caller's validation), and a change to that elsewhere-code can
silently invalidate the rejection while the candidate's own location
remains untouched; (4) **the sink's own location is not the same thing
as the path used to reach it** — a genuinely new caller can reach an
already-`REJECTED` sink through a route the original rejection never
covered, with the original path's own control completely intact, and a
sink-only identity check cannot tell this apart from "the same,
already-vetted occurrence." Reasons (3) and (4) were each demonstrated
with a working counterexample by an independent reviewer, in two
separate rounds — (4) specifically survived the fix for (3), which is
why occurrence identity now has to be defined over the full
reachability path to the sink, not the sink alone.

The full eligibility rule — occurrence identity checked over
`reachabilityPath` (an ordered chain of callers, not just the sink) as
a precondition, followed by pattern/scope match, invalidation
conditions, dependency-diff, and re-inspecting the specific control
along that path, each with a fail-closed default — and five concrete
discriminable test cases (safely reusable; a stale reason from a
same-path code change; a superficially similar but genuinely different
candidate at a different sink; the same path's control removed; and a
genuinely new path to the same sink) are specified in
[`context-manifest-schema.md`](context-manifest-schema.md#5-feedback-record-schema)
sections 5.1-5.2, using `tests/fixtures/cross_file_object_authz_safe/`
and the `cross_file_sql_safe`/`cross_file_sql_unsafe` pair — already-
existing V3 fixtures, re-read in full for this revision rather than
described from memory, after an earlier revision was found to have
asserted a fixture detail (an allowlist in `UserSearchService.cs`) that
does not actually exist in that file. This design document states the
requirement and defers the schema-level mechanics there to avoid two
documents each half-defining the same check. **Unchanged by all
revisions**: every HIGH/CRITICAL candidate that is not eligible for
reuse under that rule still goes through `skills/security-validate`'s
full, independent procedure — Feedback Learning never gains authority
to waive that requirement for a genuinely new or substantively
different candidate. **`[OPEN, disclosed residual risk]`**: this
mechanism's job is to never wrongly exempt a different path from
validation, which it now does by construction — it was never
responsible for guaranteeing a new path gets discovered and reviewed in
the first place; that remains `skills/security-review`'s own diff-aware
workflow, unchanged by this design.

## 4. Adaptive Security Orchestration — the two manifest-producing entry points

### 4.1 The no-Jev path is not a fallback tier, it is the product

**[REQUIRED, verbatim]**: "沒有 Jev token 的使用者仍須能直接安裝並使用
完整 V4 安全審查，不需設定替代服務." This is not phrased as an
acceptable degraded experience — it is a hard product requirement.
Consequently, the built-in decision layer is not a stub or a "good
enough" placeholder; it is a full manifest producer in its own right,
and it already mostly exists. **Terminology note, after independent
review**: "deterministic" throughout this document means *not Jev* —
never informed by, or dependent on, Jev's output — not literally
"computed by keyword matching with no reasoning involved." The built-in
layer's own classification work (via `skills/security-change-detection`)
is reasoning-based, the same way it always has been in V3; what makes
it the reliable floor is that it is never Jev, not that it is
mechanical. An earlier draft of `context-manifest-schema.md` section 3
conflated these two meanings and produced a check that failed its own
headline test case — see that section's revision history for the
concrete counterexample.

**[PROPOSED]** The built-in decision layer *is* V3's existing
deterministic machinery, repackaged to emit the Context Manifest shape
instead of being invoked ad hoc at each step:

```text
reviewMode         <- TARGETED for the proactive-workflow path, or the
                      explicitly requested QUICK/STANDARD/DEEP
                      (unchanged from V3's own mode selection)
sensitivity        <- item 0's classification pass
                      (context-manifest-schema.md section 3) when
                      reviewMode is TARGETED; N/A otherwise -- `[FIXED,
                      per independent review]` an earlier draft of this
                      table described this as a separate mechanical
                      signal-category lookup, which directly
                      contradicted section 3's own description of item
                      0 as a reasoning pass -- there is exactly ONE
                      classification procedure, and this table and
                      section 3 must describe the same one
domains            <- context-manifest-schema.md section 3 item 5's
                      merged rule (per section 7's decision): item 0's
                      diff-scoped domain implication for TARGETED and
                      QUICK; a repo-wide architecture pass's findings
                      for STANDARD; for DEEP, every domain the target
                      project's own architecture evidence actually shows
                      applicable (section 3a's algorithm -- NOT "all ten,
                      unconditionally," which was itself found wrong per
                      explicit instruction) -- NOT a "mode-to-domain
                      table," which a third-round independent review
                      found does not exist anywhere in the kit
reviewBudget       <- the single merged computeReviewBudget function
                      (section 7's decision, corrected a third time):
                      starting point by reviewMode, Factors adjustment
                      capped at one level for TARGETED, uncapped for
                      QUICK/STANDARD/DEEP
scannersSelected    <- plays/scanner-selection.md's domain-to-tool
                      table (unchanged)
intelligenceConsulted <- .security/baseline.json / attack-surface.json
                      lookups (unchanged) + .security/feedback.json
                      (new, section 3)
```

This framing matters for scope control, **with one disclosed
exception, per a fourth-round independent review**: most of the
built-in decision layer packages existing, already-tested V3 logic
into one manifest-shaped output rather than writing new decision
logic — `sensitivity`/`reviewBudget`/`scannersSelected`/
`intelligenceConsulted` all rest on mechanisms this kit has already
validated through two Golden Baseline rounds. **`domains` for DEEP
mode is the exception**: `context-manifest-schema.md` section 3a's
architecture-applicability algorithm (and the two new baseline-fact
keys it needs — "cryptographic operations" and "externally-invoked /
trusted-input-only," neither of which exists in
`templates/project-security-baseline.md` today) is genuinely new logic
this design introduces, not a repackaging of something V3 already had
and tested — V3's own DEEP mode simply loaded every domain the
target's stack presented per `skills/security-review/SKILL.md`'s
"Where to look next" table, with no separate applicability-decision
step of its own to repackage. `implementation-batches.md`'s Batch 0
acceptance criteria now name section 3a as its own, separately-tested
item for exactly this reason, rather than being covered by the "already
validated" claim the rest of this framing correctly makes.

### 4.2 What the Jev path is allowed to change — DECIDED: Option A, never fewer domains

**`[DECIDED, per explicit instruction, after independent analysis and a
Jev-assisted cross-check]`**: the *domain set* the floor computation
requires — item 0's classification for TARGETED/QUICK/STANDARD, or
`context-manifest-schema.md` section 3a's architecture-applicability
algorithm for DEEP — is a strict, unconditional floor — Jev is **never**
permitted to produce a manifest with fewer domains than that floor
requires. `[CORRECTED, per a fourth-round independent review Major]`:
an earlier revision of this decision named only "item 0's
classification" as the floor source; item 0 is diff-scoped (per section
3's own item 2a/3) and does not apply to an explicit DEEP request at
all (there is frequently no diff to classify for a repo-wide DEEP
review) — the actual DEEP floor is section 3a, not item 0, and any
statement of this decision (here, and in section 4.3 below) must name
both, not item 0 alone, or the decision is inoperative for the one mode
this correction batch spent the most effort getting right. This
closes out, cleanly, a tension the design's earlier revisions never
fully resolved: they said "the domain floor is a strict lower bound"
(true) while separately implying Jev's savings came partly from
"picking a narrower scope" (not actually possible once the floor is
strict) — those two statements cannot both be true, and this decision
removes the second, incorrect one.

**Two options were considered, per instruction**:

```text
Option A (chosen): the required-domain floor is identical for every
  producer. Jev's only measurable efficiency contribution is
  reviewBudget (within its own floor), reference depth, priorityOrder,
  and Intelligence reuse. `[CORRECTED, per a fourth-round independent
  review Minor]`: an earlier revision also listed "scanner selection
  within the required domains" here -- per plays/scanner-selection.md's
  domain-to-tool table, scanner selection is a total function of the
  domain set alone (a tool runs if any selected domain maps to it), so
  once domains are identical across producers, scanner selection is
  also identical by construction; it was never an independent savings
  surface once this decision was made, and listing it inflated the
  remaining surface by one item that could never actually differ. Jev
  may still ADD domains beyond the floor if it judges them relevant --
  only going below the floor is prohibited.

Option B (rejected): some independently-verifiable condition would let
  Jev safely omit a domain the floor requires, with a defined fallback
  when that condition can't be confirmed.
```

**Why Option B was rejected, not merely left unexplored**: any
condition precise and reliable enough to safely certify "this domain
can be skipped" would, by that same reliability, already qualify to be
built directly into item 0's own floor computation — at which point
Jev's involvement in that specific decision adds nothing (the
condition, not Jev, is doing the safety-relevant work). The only
remaining alternative is trusting Jev's own unverified judgment that a
domain is safe to skip, which reintroduces exactly the
self-certification problem three rounds of independent review already
spent this whole design closing for domain selection generally (see
`context-manifest-schema.md` section 3's revision history — the
mechanical-signal-match floor failed for precisely this reason: it
could not verify the absence of a control was itself the risk). An
offline Jev-assisted check on this same question, independently posed,
returned the same conclusion at full confidence (1.0) — used here only
as a corroborating second opinion on reasoning already reached, not as
the basis for the decision itself.

**Cost of this decision, stated plainly, per instruction not to hide
it in other sections**: with domain selection now identical across
producers, Jev's *measurable* token/latency savings are confined to a
narrower surface than an earlier draft implied — `reviewBudget` (whose
own margin was separately found narrow for the TARGETED path, per
section 7), reference depth, `priorityOrder`, and Intelligence reuse
(Core 2's reuse mechanism, which has no domain-count dimension at all
and is unaffected by this decision). `[CORRECTED, per a fourth-round
independent review Minor]`: "scanner selection" is removed from this
list for the same reason given above — it is not an independent
surface once domains are identical. Whether this remaining surface is
large enough to produce a genuine net efficiency gain is exactly what
`measurement-plan.md`'s new early feasibility gate (section **3a**
there — `[CORRECTED, per a fourth-round independent review Minor: an
earlier draft of this cross-reference said "4a"]`) is designed to
actually check, rather than assumed here.

**`[DISCLOSED, per a fourth-round independent review]`**: narrowing
Jev's domain role to additive-only is a real departure from
`v4-position-paper.md:51,55`'s own framing, which names "受影響的
security domains" as one of the decisions Jev participates in and
expects its routing to "應能實際減少 AI token 使用量." Per the
snapshot's own preamble (its "已確定要求/建議方案/待我決定" framing),
a departure of this kind should be recorded as a disclosed deviation
rather than left implicit in section 4.2's cost paragraph alone: this
design does depart from treating domain selection itself as one of
Jev's reducible levers, while remaining within the paper's own "Jev
路徑可以產生更精簡的計畫" latitude for the surfaces this section lists
instead (budget/depth/priority/reuse). Which framing is the right one
to carry forward — record this as a disclosed deviation, or treat it
as already within the paper's stated latitude — is left to you; both
readings are defensible, and this design does not pick one
unilaterally.

It may **never** produce a manifest that falls below what the floor
requires — for domains, budget, or sensitivity alike; **[PROPOSED]**
this is enforced by running the exact same manifest validity checker
(section 4.3) against Jev's output as against the built-in layer's
output — there is no separate, more lenient check for the Jev path.

### 4.3 Manifest validity check and degradation

**[PROPOSED, revised]** Before any manifest reaches
`skills/security-review`'s execution pipeline, a validator that is
never Jev and never the manifest's own producer marking its own output
checks it against a fixed rule set — schema completeness, enum-value
validity, and, critically, that the manifest's `sensitivity`/`domains`/
`reviewBudget`/`scannersSelected` are not below what the applicable
independent floor computation requires. `[CORRECTED, per a fourth-round
independent review Major]`: that floor computation is item 0
(`context-manifest-schema.md` section 3 — the same reasoning-based
procedure `skills/security-change-detection` already performs, never
Jev) for `sensitivity` always, and for `domains` on TARGETED/QUICK/
STANDARD manifests; for a DEEP manifest, the `domains` floor is section
3a's architecture-applicability algorithm instead, since item 0 is
diff-scoped and has no defined output for a repo-wide DEEP request with
no diff to classify. An earlier revision of this section named item 0
alone as the floor source for every mode, which left this checker
undefined for exactly the mode this correction batch spent the most
effort correcting. A manifest that fails any check is discarded, not
repaired in place (repairing a partially-wrong manifest risks silently
keeping an unsound piece of it) — see `context-manifest-schema.md`
section 3 for the exact checklist and its full revision history.

Degradation path, in order:

```text
1. Jev token missing/empty          -> built-in layer, no Jev call made
2. Jev token present but rejected
   by the API (invalid/expired)      -> built-in layer, degradation
                                        reason: "invalid_token"
3. Jev call times out                -> built-in layer, degradation
                                        reason: "timeout"
4. Jev responds but output is
   incomplete/malformed              -> built-in layer, degradation
                                        reason: "incomplete_output"
5. Jev output is well-formed but
   fails the validity check (under
   the applicable floor -- item 0's
   classification, or section 3a's
   algorithm for a DEEP manifest)     -> built-in layer, degradation
                                        reason: "below_floor"
6. Jev output passes validity check  -> used as-is
```

Six outcomes, not seven — an earlier draft added a separate
"indeterminate floor" outcome for an uncovered-signal case that no
longer exists after the second revision: item 0 is now a
reasoning-based classification pass (like V3's own classifier) that
always produces a definite, if conservatively-rounded-up, answer via
its existing "default higher when unclear" rule, so there is nothing
left that is genuinely indeterminate for a separate outcome to
represent.

Every degradation is recorded on the Context Manifest itself (see
schema's `degradation` field) — not silently absorbed. This is what
makes "no Jev token" testable as a first-class scenario rather than an
untested edge case: the same manifest shape, the same downstream
pipeline, a recorded reason for which producer actually ran.

## 5. Jev's permission boundary

**[REQUIRED, verbatim from the position paper]**: Jev may participate
in classification, domain/routing/context/scanner selection,
prioritization, and budgeting. It may never, on its own, declare a
CONFIRMED vulnerability, final exploitability, a valid attack chain,
correct remediation, or a Security Gate PASS/FAIL. Those remain
exclusively the authority of `plays/finding-validation.md` +
`skills/security-validate`, `plays/attack-chain-analysis.md`,
`plays/adversarial-validation.md`, and `plays/security-gate.md` —
**none of which this design proposes changing in any way**. Framed
against what already exists: V4 does not introduce a new
decision-maker for outcomes; it adds one more, optional contributor
(alongside the existing deterministic Factors) to the pre-existing
question of how much effort a change justifies before those outcomes
are even reached — the exact question `plays/review-budget.md` already
asks, just now with an additional, optional input.

## 6. Enterprise AD/SSO integration security check — scope overview

**[REQUIRED, position paper's own framing]**: an independent capability
batch, not a replacement for either core; focuses on whether an
internal application correctly uses the identity result from an
existing AD/SSO integration, not a full enterprise AD/Entra audit.
First-version checks (verbatim, position paper): trusted, correctly
verified login result/token; role/group/function/object-level
authorization still checked after login; safe AD/LDAP connections,
service accounts, credentials, and queries; fail-closed on SSO/AD
connection, verification, or group-query failure; and distinguishing
safe/unsafe fixtures for each.

**[PROPOSED]** Design starting point: check reuse before invention.
`plays/authentication.md` already has sections on authentication
bypass, session fixation/hijacking, and insecure password reset;
`plays/authorization.md` already covers object- and function-level
authorization. AD/SSO's genuinely new material is protocol-specific:
LDAP injection and LDAP service-account/credential handling, SAML/OIDC
token validation specifics (signature verification, audience/issuer
checks, replay), and Kerberos/NTLM-specific pitfalls — none of which
any existing reference currently covers.

**[OPEN]** Whether this becomes a new play
(`plays/enterprise-identity-security.md`) or a new section inside
`plays/authentication.md` is deferred to `implementation-batches.md`'s
batch 4, pending your decision — the position paper's own item #6 asks
this same question about protocol/integration scope, and the answer to
"new play or extend an existing one" should follow from which
protocols get in-scope for the first version, not be decided
independently of that.

**`[DECIDED, 2026-09-25 — by the user (repository owner) in the coordinating
session, answering batch4-preflight.md section 4; the [OPEN] text above is kept
verbatim as the record of the question]`** First-version protocol scope (D1):
**OIDC/OAuth 2.0 including JWT-bearer APIs** (Entra ID / ADFS as the issuer),
**direct LDAP/LDAPS** (the application binds to and queries the directory
itself), and **Windows Integrated Authentication** (Negotiate: Kerberos with
NTLM fallback). **SAML 2.0 / WS-Federation are not in the first version.**
Placement (D2): a **new play, `plays/enterprise-identity-security.md`, routed
inside the existing `authentication` domain** — no new Context Manifest domain,
no schema change; the generic rules stay in `plays/authentication.md` /
`plays/authorization.md` and are referenced, not copied.

**[REQUIRED]** This capability's cost (context, maintenance) is
measured and reported **separately** from Jev/Adaptive-Intelligence
efficiency numbers — it must never be blended into those figures.
`measurement-plan.md` reflects this as a hard separation, not a
reporting nicety.

## 7. review-budget's two parallel entry points — DECIDED: merged (Option B)

V3 Slim's own Golden Baseline report already recorded this as "open,
not a proven defect, deferred to V4" — this section is where V4 is
actually asked to weigh in, per your explicit correction: **the
existing 17-case (plus this session's attack-chain/design-routing)
execution passing is evidence about the specific cases tested, not
proof that no scenario in the whole space produces a contradiction
between the two entry points.** This design does not resolve the
question; it lays out the comparison you asked for.

**Current state** (unchanged from V3 Slim): `plays/secure-development-workflow.md`'s
"Determine review budget" step (TARGETED path, sensitivity-driven) and
`skills/security-review/SKILL.md`'s Scope step "Explicit mode" branch
(QUICK/STANDARD/DEEP, mode-driven) each independently compute a budget
level and each cites `plays/review-budget.md`'s shared level
definitions.

### Option A: keep two entry points

```text
Benefit   Each entry point's own prose stays local to its own caller —
          the workflow file only has to describe the sensitivity-driven
          path, SKILL.md only the mode-driven path. No cross-file
          redesign needed to accommodate V4.

Cost      Every new manifest producer V4 adds (Jev decision layer,
          built-in decision layer) has to decide which of the two
          existing paths it is, or whether it needs a third path of
          its own -- the applicability matrix (already 2 rows after
          V3 Slim) risks growing into an N-way matrix. This is exactly
          the "multiple documents describing one mechanism, one gets
          stale" shape that produced 2 of V3 Slim's own findings (F1
          citation drift, and the N1 finding that was a fresh instance
          of the same shape introduced by the very fix for F1) -- a
          demonstrated, not hypothetical, recurrence risk in this
          specific area of the kit.

Regression Low for existing V3 behavior (nothing about the two current
risk       paths changes). Risk instead shifts onto V4's new producers
          correctly classifying themselves into the right existing
          path -- a new occurrence of the same class of bug, on new
          code, rather than elimination of the class.
```

### Option B: merge into a single authoritative entry point

```text
Benefit   The Context Manifest already needs exactly one place that
          computes reviewBudget for *any* producer, Jev or built-in.
          A single entry point maps directly onto "the manifest's
          reviewBudget field is computed by exactly one function,
          called by every producer" -- closing the structural gap the
          two-entry-point design otherwise has to route every new
          caller around. This could fall out of building the manifest
          layer as a natural byproduct rather than requiring a
          dedicated refactor -- worth testing empirically in batch 0
          before deciding to invest in a standalone merge (see
          recommendation below).

Cost      Touches plays/secure-development-workflow.md,
          skills/security-review/SKILL.md, plays/review-budget.md, and
          AGENTS.md -- a genuine multi-file redesign, not a small edit,
          with the same class of regression-testing burden the
          two-round F1-F5/F7 + N1-N11 remediation already went through
          once in this exact area.

Regression All 17 existing tests/validation/v3-review-budget-test-cases.md
risk       cases would need re-verification against the merged entry
          point (not just the ones exercised so far), plus new
          V4-specific cases (a Jev-driven manifest requesting a budget,
          a built-in-layer manifest requesting a budget) added before
          the merge could be considered complete and independently
          re-reviewed, mirroring the process V3 Slim's remediation
          already required for a smaller version of this same file.
```

### Decision: Option B — merge into a single authoritative entry point

**`[DECIDED, by you, after this batch's third independent-review
round]`.** The empirical evidence the original "Recommendation" below
said this design couldn't obtain by reasoning alone arrived earlier
than expected: three rounds of independent review, working through the
consequences of adding `reviewMode` to the Context Manifest (a
consequence of trying to keep the two entry points logically separate
within one schema), found three real, distinct defects exactly at the
seam between them — an explicit mode's *starting point* was
incorrectly hard-coded as a *floor* (contradicting `plays/review-budget.md`'s
own "Factors can move it all the way down" rule and
`tests/validation/v3-review-budget-test-cases.md` cases 7/7b); the
explicit-mode domain-selection rule the design cited did not exist
anywhere in the kit; and the TARGETED floor was shown to always equal
the built-in layer's own answer by construction, leaving `reviewBudget`
with no real savings margin on that path. This is Option A's own
predicted cost (the "multiple documents/branches describing one
mechanism, one gets stale" shape) materializing a third time in this
exact area of the kit, now inside V4's own design rather than only
cited from V3 Slim's history — treated as sufficient evidence to
decide now rather than defer further.

**What the merge actually is**: one function,
`computeReviewBudget(reviewMode, sensitivity, factorsEvidence)`,
called by every manifest producer (built-in and Jev alike) and by both
the TARGETED and explicit-mode call sites, replacing the two
separately-described computations:

```text
1. Starting point:
   reviewMode == TARGETED  -> plays/review-budget.md's Default
                              starting point table, keyed on
                              `sensitivity` (NONE->MINIMAL,
                              LOW->MINIMAL/FOCUSED, MODERATE->FOCUSED,
                              HIGH->ELEVATED)
   reviewMode in
   {QUICK, STANDARD}        -> FOCUSED
   reviewMode == DEEP        -> AUDIT

2. Factors adjustment (plays/review-budget.md's "Factors" section,
   unchanged):
   reviewMode == TARGETED  -> move AT MOST ONE level up or down from
                              the starting point (the existing cap,
                              protecting a considered sensitivity
                              classification from being silently
                              overridden)
   reviewMode in
   {QUICK, STANDARD, DEEP}  -> UNCAPPED movement (per that play's
                              "Explicit mode" section: "It does not
                              apply here, since these three modes'
                              defaults have no sensitivity
                              classification to bound movement
                              against" -- an explicit DEEP request that
                              touches nothing sensitive can move all
                              the way down to MINIMAL, the exact
                              scenario cases 7/7b test)

3. Output: the adjusted level, used as reviewBudget.
```

This single function is what `context-manifest-schema.md` section 3's
checks now validate against (replacing the previous split
TARGETED-only / not-yet-defined-for-explicit-modes checks) — see that
section for the corrected check text. Domain selection for explicit
modes is resolved the same way, using `plays/code-review.md`'s actual
mode descriptions rather than a table that was found not to exist:
QUICK reuses item 0's own diff-scoped domain-implication reasoning
(the same mechanism TARGETED already uses, just without a sensitivity
classification attached to it); STANDARD requires the domains
implicated by a repo-wide architecture pass (`skills/security-review`'s
own "Architecture discovery" step) across whatever the target
repository's own stack actually presents, not a fixed list; DEEP
requires every domain `context-manifest-schema.md` section 3a's
architecture-applicability algorithm finds actually present in the
target project — corrected from an earlier "all ten, unconditionally"
claim, per explicit instruction, since `plays/code-review.md`'s own
DEEP description ("every security-sensitive area") is scoped by what
is actually there, not a fixed count; DEEP's mandatory *activities*
remain unconditional and unaffected by this correction.

**Cost accepted**: this touches `plays/secure-development-workflow.md`,
`skills/security-review/SKILL.md`, `plays/review-budget.md`, and
`AGENTS.md` when actually implemented (batch 0/3, not this planning
document) — the multi-file redesign Option B's own cost section named.
**Regression risk accepted**: all 17 existing
`tests/validation/v3-review-budget-test-cases.md` cases need
re-verification against the merged function before Golden-Baseline-
style sign-off, in addition to the new manifest-producer cases this
design already requires.

## 8. The six open decisions (position paper's own list, addressed in order)

`[CORRECTED, per a fourth-round independent review Minor: an earlier
draft of this preamble said "every item below is OPEN... none is
treated as resolved," directly contradicted by item 5's own
`[DECIDED]` tag two paragraphs below it]`. Two of the six are now
`[DECIDED]` (items 2 and 5, both below); the remaining four are
`[OPEN]`, with a `[PROPOSED]` direction offered where this session's
reading of the existing V3 mechanism gave a concrete basis for one.

1. **Context Manifest schema/fields/validity check, Jev-vs-built-in
   responsibility split** — `[PROPOSED]` full schema in
   `context-manifest-schema.md`. `[OPEN]`: the exact required-vs-optional
   field list, and whether a manifest that fails validation is itself
   logged as an Intelligence fact (a repeated pattern of Jev failures
   for a given repo/task shape would itself be useful signal) or
   discarded without a trace beyond the one review's own record.
2. **Which minimum requirements are deterministic-guaranteed vs.
   Jev-selectable; recovery when Jev under-scopes** —
   `[DECIDED, per this correction batch: the mechanism is now fully
   specified, superseding the earlier "[PROPOSED, revised a second
   time]" tag]` the guaranteed floor is exactly what
   `plays/review-budget.md`'s "floor this play cannot lower",
   `plays/finding-validation.md`'s mandatory validation,
   `plays/security-gate.md`'s outcomes, and an independently-computed
   *sensitivity and domain floor* — `context-manifest-schema.md`
   section 3, items 0/2a/3/4/5 for TARGETED/QUICK/STANDARD, and item 0
   plus **section 3a's architecture-applicability algorithm** for DEEP
   specifically (`[CORRECTED, per a fourth-round independent review
   Major]`: an earlier revision of this item cited "items 0/3/4/5" for
   every mode, which does not name a floor source for DEEP at all,
   since item 0 is diff-scoped and DEEP's actual floor is section 3a)
   — already guarantee, unmodified; Jev's selectable range is
   everything *within* that floor: `reviewBudget` above its own floor,
   reference depth, and `priorityOrder` (`intelligenceConsulted`'s own
   contribution is Core 2's, not this floor/Jev split — see item 4
   below). Recovery is section 4.3's validity checker, which is never
   Jev and never itself depends on Jev being available or correct.
   `[OPEN, disclosed limitation, not resolved by this DECIDED status]`:
   the floor's own reliability is bounded by the same limits
   `skills/security-change-detection`'s classification already has
   today (its category lists are "examples, not an exhaustive
   taxonomy"), plus section 3a's own disclosed indirect-reachability
   limitation for DEEP — this is inherited, not solved, and there is no
   separate "indeterminate" outcome distinct from that classifier's own
   existing "default higher when unclear" behavior.
3. **Persistence format/scope/confidence/invalidation/version
   compatibility for Intelligence records** — `[PROPOSED]` schema in
   `context-manifest-schema.md`, modeled on the existing
   `baseline.json`/`attack-surface.json` 5-part fact schema plus their
   existing unrecognized-schema-version fallback. `[OPEN]`: whether
   Feedback records live in a new `.security/feedback.json` (this
   design's proposal, to avoid growing the two already-tested existing
   files' schema surface) or as a new section inside one of the
   existing two files.
4. **Proving evidence reuse doesn't increase false negatives; separating
   Jev's savings from Intelligence reuse's savings** — methodology in
   `measurement-plan.md` section 4; `[OPEN]` whether the current
   representative-task set (five tasks in the 2x2 factorial — T2, T3,
   T4, T4b, T5 — plus T1 as a separate interface-only check;
   `[CORRECTED, per a fourth-round independent review Minor: an earlier
   draft of this item said "3-5 tasks," which undercounted the set
   `measurement-plan.md` section 4 already specifies]`) is sufficient
   or needs expansion once real tasks are chosen. Separately,
   `measurement-plan.md` section 3a's early feasibility gate now binds
   its recall/false-negative/false-positive check to the full existing
   `tests/fixtures/` corpus rather than this narrower factorial set
   (see that section for why) — this item's own `[OPEN]` question is
   about the factorial's sufficiency for *attribution* (separating
   Jev's contribution from Intelligence reuse's), not about recall
   coverage, which section 3a's gate now checks more broadly.
5. **review-budget's two entry points** — `[DECIDED]` merged into a
   single authoritative entry point (Option B) after three rounds of
   independent review found real defects at the seam between them; see
   section 7 above for the merged design and the evidence behind it.
6. **AD/SSO first-version protocol/integration scope, and what's
   verifiable without real enterprise access** — see section 6;
   `[PROPOSED]` reuse-first design direction, `[OPEN]` the actual
   protocol list and whether it becomes a new play or an extension of
   `plays/authentication.md`, deferred to `implementation-batches.md`
   batch 4. `[DECIDED, 2026-09-25, by the user]` see section 6's
   decision note: OIDC/OAuth 2.0 + JWT, direct LDAP/LDAPS, Windows
   Integrated Authentication; SAML/WS-Federation out of the first
   version; a new play inside the existing `authentication` domain.

## 9. What this document does not do

It does not modify any file under `plays/`, `skills/`, `references/`,
`agents/`, `templates/`, `scripts/`, or `tools/` in this kit. It does
not begin any V4 implementation. `[CORRECTED, per a fifth-round
independent review Minor: an earlier draft of this sentence still said
"it does not resolve any of the six [OPEN] items above," contradicting
section 8's own [DECIDED] tags on items 2 and 5]` it does not resolve
the four items section 8 still marks `[OPEN]` (1, 3, 4, 6) — each
remains yours to decide, with a `[PROPOSED]` direction offered only
where this session's reading of the existing V3 mechanism gave it a
concrete basis to offer one.
