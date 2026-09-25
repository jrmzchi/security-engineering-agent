# Context Manifest & Adaptive Project Security Intelligence — Data Contracts

**Status: design proposal, not implemented. Revised across three
rounds of independent review, plus nine direct correction batches: the
first added section 3a (DEEP domain applicability) and applied
`v4-design.md`'s Option A decision here; a fourth independent review
round then found that first correction batch's own domain floor still
wrong in two ways (excluding two of DEEP's own mandatory activities,
and reintroducing a presence-based exclusion on exactly the three
domains whose risk IS a control's absence) — the second correction
batch fixes both (`round4-disposition.md`); a fifth independent review
round then found the second correction batch's own Case 1b worked
example got exactly the authentication/authorization exclusion
backwards when invocation context is unconfirmed, plus Case 2's premise
still conceding browser-rendered content while excluding web-security —
the third correction batch fixes both (`round5-disposition.md`); a
sixth independent review round then found Case 2's fix still only
defeated six of `plays/web-security.md`'s eight Scope items (CORS
misconfiguration and open redirect need no HTML to apply) — the fourth
correction batch fixes this (`round6-disposition.md`); a seventh
independent review round then found this same case's `data-security`
justification did not satisfy its own domain's condition, and traced
the recurring web-security defect to the Group 3 table's own
under-specified `web-security` row, not merely Case 2's prose — the
fifth correction batch fixes the table row directly and rewrites Case
2 to point at it instead of re-deriving the answer a fourth time
(`round7-disposition.md`); an eighth independent review round then
found the corrected `web-security` row still missing a CSRF disjunct,
and — stress-testing the other three Group 3 rows for the first time —
found the identical under-specification pattern in all three
(`api-security`/`data-security`/`file-security`), plus a false
"kept unedited" correction note in `round6-disposition.md` — the sixth
correction batch fixes all four rows against their cited plays'
complete Scope sections, adds a default-inclusive safety net for any
gap still undiscovered, and restores the falsified historical note
(`round8-disposition.md`). A ninth independent review round then found
that safety net itself ambiguous (it conflicted with this file's own
fixed domain counts under one reading) and — checking all 42 Scope
items across the four Group 3 plays for the first time — found three
more uncovered items, the third occurrence of this exact shape after
round 8 itself: **per your explicit decision on the structural question
round 8 raised, the seventh correction batch removes the Group 3
condensed condition table entirely**, replacing it with a direct
pointer to each play's own Scope section as the sole authoritative
source, an execution rule requiring every item to be checked (default
to applicable on any uncertainty), and an executable, symmetric
coverage check in `implementation-batches.md` Batch 0 — not a table
this document maintains by hand, and not a fixture test that merely
re-guards a copy (`round9-disposition.md`; full original review report
preserved verbatim in `round9-full-report.md`). A tenth independent
review round then confirmed the redesign closes the recurring pattern,
but found the risk had partly relocated to two Majors introduced by
that same batch — `implementation-batches.md`'s own criterion 6(a)
still hardcoded a fact count for Case 1 that the same commit had
changed, and criterion 7 never defined "discriminating" as requiring
per-item fixture isolation (the manifest's flat `domains` array makes
a shared fixture pass every mapped item trivially) — the eighth
correction batch fixes both, decides fixture isolation over a manifest
schema change, and closes two smaller gaps in Case 1 itself so it
remains valid as criterion 6(a)'s own fixture source
(`round10-disposition.md`; full original report preserved verbatim in
`round10-full-report.md`). An eleventh independent review round then
independently recomputed Case 1's and Case 1b's domain counts from all
42 Scope items, confirmed both prior Majors fully closed, could not
construct a new counterexample against the isolation mechanism, and
found only two Nits and one Minor completeness gap in the
`consistency-check` trigger-host wording — the ninth correction batch
fixes all three and stops the review cycle here, per three consecutive
rounds confirming the redesign holds with only self-inflicted edge
issues remaining (`round11-disposition.md`; full original report
preserved verbatim in `round11-full-report.md`). See
`v4-design.md`'s own status header for the full revision
history; this file carries the actual mechanics for every fix named
there, but the Option A decision itself is made and owned by
`v4-design.md` section 4.2, not here — this file only applies it. See
`v4-staging-decisions.md` for what V3 Slim actually proved and what
that does and does not change about this plan. Requirement source:
[`v4-position-paper.md`](v4-position-paper.md) (immutable snapshot).
Design narrative: [`v4-design.md`](v4-design.md) — read that first;
this document is the field-level schema for the concepts it names.
Same tagging convention as `v4-design.md`: `[REQUIRED]` / `[PROPOSED]`
/ `[OPEN]`.

## 1. Context Manifest

One record per review invocation. Produced by exactly one of the two
manifest-producing layers (`v4-design.md` section 4); consumed
identically by `skills/security-review`'s existing workflow regardless
of which one produced it.

```jsonc
{
  "manifestVersion": "1.0",              // [PROPOSED] semver, so a
                                          // future incompatible change
                                          // is detectable the same way
                                          // baseline.json/attack-surface.json
                                          // already handle schemaVersion
  "reviewId": "string",                  // [PROPOSED] stable id for
                                          // this review invocation
  "producedAt": "ISO-8601 timestamp",
  "producedBy": "jev | built_in",        // [REQUIRED concept, PROPOSED field name]

  "targetChange": {
    "diffSummary": "string",             // short, human-readable
                                          // convenience field ONLY --
                                          // [PROPOSED, clarified after
                                          // Jev-assisted review] section
                                          // 3's independently-recomputed
                                          // sensitivity/domain floor
                                          // (item 0) never reads this
                                          // field as evidence; it reads
                                          // the actual repository diff
                                          // via the "files" list below,
                                          // the same way any producer
                                          // is expected to have done --
                                          // trusting a self-reported
                                          // summary for a floor check
                                          // would defeat the point of
                                          // an independent recomputation
    "files": ["path", "..."],            // includes untracked files,
                                          // per plays/secure-development-workflow.md's
                                          // existing "Post-implementation
                                          // inspection" requirement --
                                          // this is the pointer the
                                          // validity checker follows
                                          // back to the real diff
                                          // content on disk/in git
    "techStack": ["string", "..."],
    "scannerAvailability": {"semgrep": true, "gitleaks": true, "...": false}
  },

  "reviewMode": "TARGETED | QUICK | STANDARD | DEEP",  // [NEW, PROPOSED,
                                          // added after independent
                                          // review found check 7 below
                                          // could reject a legitimate
                                          // explicit-mode manifest] --
                                          // per plays/review-budget.md's
                                          // own Applicability matrix,
                                          // TARGETED is sensitivity-
                                          // driven but QUICK/STANDARD/
                                          // DEEP are NOT -- they have no
                                          // sensitivity input at all.
                                          // The validity checker MUST
                                          // know which regime produced
                                          // this manifest before it can
                                          // pick the right floor rule
                                          // (item 7 below) -- there is
                                          // no way to infer this from
                                          // sensitivity/domains/budget
                                          // alone once both regimes can
                                          // coexist in the same schema
  "sensitivity": "NONE | LOW | MODERATE | HIGH | N/A",   // [REQUIRED —
                                          // same vocabulary as
                                          // skills/security-change-detection,
                                          // not a new scale. "N/A" when
                                          // reviewMode is QUICK/STANDARD/
                                          // DEEP, per the Applicability
                                          // matrix's own "sensitivity
                                          // not computed for an explicit
                                          // request" row -- a manifest
                                          // must not invent a sensitivity
                                          // value it was never given
  "domains": ["authorization", "file-security", "..."],  // [REQUIRED —
                                          // same domain names as
                                          // skills/security-review/SKILL.md's
                                          // "Where to look next" table
  "reviewBudget": "MINIMAL | FOCUSED | ELEVATED | AUDIT", // [REQUIRED —
                                          // same vocabulary as
                                          // plays/review-budget.md.
                                          // Computed by whichever entry
                                          // point v4-design.md section 7
                                          // resolves to use — this field
                                          // does not itself decide that
                                          // open question.

  "scannersSelected": ["semgrep", "..."],
  "scannersSkipped": [
    {"tool": "trivy", "reason": "not relevant to current change (domains: authorization)"}
  ],
  "coverageGaps": [
    {"tool": "semgrep", "reason": "unavailable in this environment"}
  ],                                      // [PROPOSED, added after
                                          // independent review --
                                          // mirrors
                                          // plays/scanner-selection.md's
                                          // skippedTools/coverageGaps
                                          // distinction FULLY now, not
                                          // just half of it: a tool that
                                          // was relevant but unavailable
                                          // (coverageGaps) must not be
                                          // indistinguishable from one
                                          // that was never relevant
                                          // (scannersSkipped) -- check 6
                                          // below now requires this
                                          // distinction explicitly

  "priorityOrder": ["path/or/domain", "..."],  // [PROPOSED] ordered
                                          // hint for which
                                          // domain/file to examine
                                          // first — advisory ONLY.
                                          // [PROPOSED constraint, added
                                          // after Jev-assisted review,
                                          // human-verified — see section
                                          // 3's note]: this field must
                                          // NEVER cause a domain listed
                                          // in "domains" to be skipped
                                          // entirely. V3's own execution
                                          // model (skills/security-review/
                                          // SKILL.md step 5) has no
                                          // "ran out of budget mid-list"
                                          // truncation mechanism today,
                                          // so no new check enforces this
                                          // yet — it is recorded here as
                                          // a binding constraint on any
                                          // future execution mechanism
                                          // that DID introduce a hard
                                          // per-review time/token cap.

  "intelligenceConsulted": {
    "baselineFactsUsed": ["fact-id", "..."],
    "attackSurfaceNodesUsed": ["node-id", "..."],
    "feedbackRecordsConsulted": ["record-id", "..."]
  },                                      // [PROPOSED] references by ID
                                          // into the existing/new
                                          // .security/*.json stores —
                                          // never a duplicated copy of
                                          // their content

  "degradation": {
    "jevAttempted": true,
    "jevOutcome": "success | no_token | invalid_token | timeout | incomplete_output | below_floor",
    "fallbackUsed": false,
    "fallbackReason": "string | null"
  },                                      // [PROPOSED] the audit trail
                                          // for v4-design.md section 4.3.
                                          // Six values -- an earlier
                                          // draft added a seventh
                                          // ("indeterminate_floor") for
                                          // an uncovered-signal case
                                          // that no longer exists after
                                          // section 3's second revision
                                          // (item 0 is now a reasoning-
                                          // based classification that
                                          // always produces a definite
                                          // answer, per its own
                                          // "default higher when
                                          // unclear" rule -- there is
                                          // no separate indeterminate
                                          // outcome to represent)

  "validity": {
    "checkedBy": "deterministic_validator",
    "passed": true,
    "failedChecks": []
  }                                       // [PROPOSED] see section 3
}
```

## 2. Why `intelligenceConsulted` is references, not copies

Same discipline `plays/project-security-baseline.md` already applies
("Keep the baseline out of every prompt" — a compact summary for
routing, full detail loaded only when a specific fact is actually
relevant): the manifest names *which* facts/nodes/records informed its
decision, so the decision is auditable, but does not inline their full
content into every manifest. The execution pipeline loads the
referenced record's detail only if the step that needs it actually
needs it — this is the same progressive-disclosure principle the whole
kit already follows, applied to the manifest's own footprint.

## 3. Manifest validity check (never Jev, never self-certified by the built-in layer) — `[PROPOSED, revised a second time after independent review]`

Applied identically to a Jev-produced or built-in-produced manifest —
there is no separate, more lenient check for either producer.

**This section was revised twice.** The first revision (an
independently-recomputed sensitivity/domain floor) was itself found by
an independent code-reviewer to still fail on its own headline
counterexample — the reviewer's finding is adopted below, not
papered over. **The core mistake in the first revision**: it assumed
item 0's floor could be computed *mechanically* ("no LLM call," plain
keyword/API-name matching against the diff). That assumption is wrong,
and it is wrong for the same reason `plays/security-change-detection.md`
itself is not a mechanical lookup table: that play's own worked example
— "Add an endpoint for downloading machine reports by filename" ->
"HTTP input + filesystem access + **potential object authorization** +
potential path traversal = HIGH" — reasons that authorization is
implicated *because of what kind of operation this is* (an HTTP-exposed
file-serving endpoint), not because any authorization-related keyword
appears in the code. A mechanical signal-match check, run against a
diff whose actual defect is a **missing** `[Authorize]` attribute, finds
zero authorization-related tokens and legitimately concludes
authorization was never required — this is not an edge case, it is
*the exact shape of the counterexample this check exists to catch*,
which is why the first revision failed against its own headline example.

**The fix**: item 0 is not a mechanical check. It is an independent
*classification pass* — the same reasoning-based procedure
`skills/security-change-detection` already performs (using the
Detection Signals list as illustrative evidence, per that play's own
"reason about implied behavior, not just literal words" framing, and
its "default to the higher of the plausible levels" rule for an
unclear case), run identically whether or not a diff exists yet
(diff-based re-classification, or pre-implementation intent
classification — the same two modes V3 already has). **The invariant
this design actually needs to preserve is not "no LLM call ever" — it
is "this classification pass is never Jev, and is never informed by
what Jev's manifest claims."**

**Cost accounting, corrected a second time after independent review**:
on the **built-in-only path**, item 0 costs nothing beyond what the
built-in layer was always going to compute — it *is* the built-in
layer's own classification work, run once. On the **Jev path**, this
is honestly an **additional** cost: per `v4-design.md` section 1,
exactly one producer runs per review, so when Jev produces the
manifest, the built-in layer does not otherwise run at all, and item 0
is extra classification work spent purely to floor-check Jev's output.
**`measurement-plan.md` must count item 0's own token cost as part of
the Jev path's total cost** (its section 4's Condition C/D), not treat
it as free just because it is "the same procedure" — an earlier
revision of this document claimed the Jev path's classification pass
was costless, which was true only for the built-in-only path and
should not have been generalized. **Where V4's savings still come
from, restated honestly a second time**: not from skipping
classification (which now has a real, counted cost on the Jev path),
but from Jev's own choices for `reviewBudget` (down to its existing
floor), reference depth, `priorityOrder`, and `intelligenceConsulted`
outweighing that added classification cost in the common case — an
empirical claim for `measurement-plan.md` to actually verify, not an
assumption this design gets to make for it.

```text
0. Independent classification pass (the input every floor check below
   depends on): re-run skills/security-change-detection's existing
   procedure — reasoning-based, using the Detection Signals list as
   evidence and its own "default higher when unclear" rule for an
   ambiguous case — performed by a non-Jev agent (in practice, the
   built-in layer's own classification work; there is no separate,
   cheaper implementation of this step). Output: a sensitivity level
   AND, per the [OPEN, PROPOSED] extension below, the set of domains
   that classification's own reasoning implicates.

   `[OPEN, disclosed limitation, corrected after independent review]`:
   `skills/security-change-detection/SKILL.md` already names "what
   security domains are affected" as one of the four things it answers,
   and its output already determines which domains
   `skills/security-review` loads — so this is not a missing skill-level
   capability. What is actually missing is narrower: `plays/security-change-detection.md`
   itself (the authoritative *procedure*, not the skill wrapper) only
   documents a *signal token* list, not a *signal-to-domain reasoning*
   procedure that reliably produces the file-download-without-`[Authorize]`
   conclusion from a diff with no authorization token present. This
   design does not modify that play (out of scope — no security-rule
   changes in this batch) — it proposes that V4's item-0 pass asks the
   underlying classifier the same style of question its worked examples
   already answer informally in prose, without requiring a change to
   the play's own text. This remains a real, disclosed gap: two
   engineers implementing item 0 from this description alone, with no
   further specification, could reasonably diverge — see the `[OPEN]`
   note in section 3's introduction for the concrete failure this can
   produce if item 0's output is not made to agree with every other
   place in this design that also claims to compute `domains`.

1. Schema completeness: every required field present, no field of the
   wrong type.
2. Enum validity: reviewMode/sensitivity/reviewBudget/domains/producedBy
   values are all within their defined vocabularies (no invented level
   name).
2a. [NEW, closes a third-round Major] `reviewMode`/`sensitivity`
   coupling: `reviewMode == TARGETED` requires `sensitivity != N/A`;
   `reviewMode` in `{QUICK, STANDARD, DEEP}` requires `sensitivity ==
   N/A`. This is a cross-field condition item 2's plain enum-membership
   check cannot express on its own (an earlier draft claimed item 2
   already covered this; membership-in-vocabulary and this pairing
   constraint are different questions) — it is its own explicit check,
   run before item 3 relies on the pairing being correct.
3. Sensitivity floor: **only applies when `reviewMode` is `TARGETED`**
   (per item 2a above, a non-TARGETED manifest's `sensitivity` is
   already guaranteed `N/A` and this check simply does not apply to
   it — see the `reviewMode` field's own note: `plays/review-budget.md`'s
   Applicability matrix has no sensitivity input at all for
   QUICK/STANDARD/DEEP, so there is nothing for this check to floor
   against). For a TARGETED manifest: the
   declared `sensitivity` must be at least the value independently
   classified in item 0 (NONE < LOW < MODERATE < HIGH ordering) — a
   manifest may declare a *higher* sensitivity than the floor (never a
   failure), only a lower one is a violation. Because item 0 already
   applies "default to the higher of the plausible levels" for an
   unclear case, there is no separate indeterminate outcome to handle
   here.
4. Domain non-emptiness: `[CORRECTED, per independent review]` domains
   is non-empty unless item 0's classification reasoning implicates NO
   domain at all — checked directly against item 0's own implicated-
   domain output, not against whether sensitivity happens to equal
   NONE. (An earlier draft tied this exemption to sensitivity == NONE,
   which would have forced a LOW-sensitivity, no-implicated-domain
   change — e.g. a pure internal refactor — to invent a domain just to
   pass this check.)
5. Domain floor: `[REVISED, per the section-7 decision to merge
   review-budget's two entry points into one — see v4-design.md section
   7]`. For a TARGETED manifest: `domains` must be a **superset** of the
   domain set item 0's classification reasoning implicates (not a
   signal-presence lookup — see the worked-example counterexample
   above: the file-download-without-`[Authorize]` shape's item-0
   classification reasons "HTTP input + filesystem access -> object
   authorization is implicated," independent of whether an `[Authorize]`
   token is present or absent in the diff). For QUICK: `domains` must be
   a superset of item 0's own diff-scoped domain implication (the same
   reasoning mechanism, reused directly — QUICK has no sensitivity
   classification attached to it, per `plays/review-budget.md`'s
   Applicability matrix, but domain implication from the diff is a
   separate question item 0 already answers regardless of sensitivity).
   For STANDARD: `domains` must cover every domain a repo-wide
   architecture pass (`skills/security-review`'s "Architecture
   discovery" step) finds actually present in the target repository's
   stack — not a fixed table, since `plays/code-review.md`'s own STANDARD
   description is "semantic review of security-sensitive code paths
   across the repository," scoped to what's actually there. For DEEP:
   `[CORRECTED, per explicit instruction — an earlier draft's "all ten,
   unconditionally" was itself wrong]` `domains` must cover every domain
   actually applicable to the target project's real architecture, per
   the applicability algorithm in section 3a below — not a fixed count.
   `plays/code-review.md`'s own DEEP description requires "manual
   semantic review of **every security-sensitive area**," which is
   scoped by what is actually present, the same way its own "Where to
   look next" table already instructs ("A .NET project should not pull
   in IIS or Windows-specific guidance unless it is actually deployed
   there. A pure Python CLI should not load ASP.NET or browser guidance
   at all.") — DEEP's mandatory *activities* (architecture analysis,
   threat model, full scanner run, independent validation, configuration
   and dependency review, a complete report) are unconditional and
   unchanged; which *domains* those activities are performed within is
   not. `[CORRECTED, per a third-round independent review]`: an earlier
   draft cited "`plays/code-review.md`'s mode-to-domain rules" as the
   source for QUICK/STANDARD/DEEP domain selection — that table does not
   exist anywhere in the kit; the rules above are derived directly from
   that play's actual QUICK/STANDARD/DEEP prose descriptions instead of
   a table that was never real.

### 3a. DEEP domain applicability — the algorithm and why it isn't "all ten"

**`[PROPOSED, revised across four independent review rounds (4-8) --
`[CORRECTED, per an eighth-round independent review Nit: an earlier
revision of this line stopped counting at "a second time after a
fourth independent review round," stale by three more rounds]`]`**:
the first version of this algorithm (below, in the revision history)
treated every one of the ten domains the same way — "applicable if
baseline evidence shows the concern is present." A fourth independent
review round found this wrong for two disjoint
groups of domains, for two different reasons. **This algorithm now has
three groups, not one uniform rule**:

**Group 1 — DEEP's own mandatory activities, unconditionally
applicable**: `code-review`, `configuration-security`,
`dependency-security`. `[CORRECTED, per a fourth-round independent
review Blocker]`: `plays/code-review.md`'s own DEEP activity list
names "configuration review (`plays/configuration-security.md`)" and
"dependency review (`plays/dependency-security.md`)" as mandatory
DEEP activities, on the same line as "full scanner run" and
"independent validation" — for these two, the *activity* and the
*domain* are the same object, so there is no separate applicability
question to ask; excluding either one (as the first version of this
table did for `configuration-security`) does not merely under-load
reference material, it skips a DEEP-mandatory activity outright, and —
via `plays/scanner-selection.md`'s domain-to-tool mapping (Trivy maps
only from `configuration-security`, OSV-Scanner/ecosystem-audit only
from `dependency-security`) — silently cancels part of DEEP's
"full scanner run" guarantee at the same time. `dependency-security`'s
own presence criterion ("a dependency manifest exists") was already
true for nearly every real project in practice, but this batch makes
it structurally unconditional for DEEP rather than relying on that
practical near-universality, for the same reason as
`configuration-security`: the activity is mandatory regardless of what
the target project's own manifest situation happens to be (even a
project with zero declared dependencies still gets a — possibly
trivial — dependency-review activity performed, the same way a project
with no configuration files still gets a configuration-review activity
performed, its output simply being "nothing found to flag" rather than
the activity being skipped).

**Group 2 — domains whose risk IS a control's absence, applicable by
default, excluded only by positive evidence the concern does not
exist**: `authentication`, `authorization`, `secrets-security`.
`[CORRECTED, per a fourth-round independent review Blocker, per
explicit instruction — this is a design decision, not merely a text
fix]`: the first version of this table required baseline evidence that
a mechanism (an authentication scheme, an access-control decision, a
credential source) is *present* before including the corresponding
domain — this reintroduces, at DEEP's repo-wide scope, the exact
defect this design already fixed once at the item-0/diff-scope level
(section 3's revision history above: "a mechanical signal-match check
... concludes authorization was never required — this is not an edge
case, it is the exact shape of the counterexample this check exists to
catch"). For these three domains specifically, *absence* of a
mechanism is not evidence the concern doesn't apply — it is frequently
the vulnerability itself (missing authentication, missing
authorization, an undiscovered hardcoded secret). The corrected rule:

```text
Domain            Excluded from DEEP only when baseline evidence
                  POSITIVELY confirms, with evidence whose scope
                  covers the entire component under review, that
                  the underlying concern has no context to apply in
                  at all -- never merely that a mechanism for it was
                  not found.
------------------ -----------------------------------------------------
authentication    Excluded only when the baseline positively confirms,
                  with EVERY fact below at source ∈ {USER_CONFIRMED,
                  CODE_EVIDENCE, CONFIG_EVIDENCE} AND confidence == HIGH
                  (confidence UNKNOWN/LOW/MEDIUM, or source INFERRED/
                  NONE, on ANY of the facts below makes the whole
                  exclusion fail): (i) this component is invoked ONLY
                  by a trusted local operator or a single, already-
                  authenticated caller whose identity is established
                  by something OUTSIDE this component's own scope --
                  i.e. no remote or cross-boundary invocation this
                  component itself is responsible for distinguishing
                  callers on; AND (ii) no scenario requiring
                  distinguishing between different possible actors
                  exists anywhere in this component's own code (no
                  session/identity concept of any kind). BOTH are
                  required -- (ii) alone is NOT sufficient, because a
                  component can genuinely contain no session code and
                  still be the wrong place to skip authentication if
                  something OUTSIDE it (an unconfirmed caller) is what
                  actually needed distinguishing; this is why fact (i)
                  is load-bearing, not decorative. NOT sufficient to
                  exclude: no authentication mechanism was found; the
                  baseline's `authentication` fact is UNKNOWN or NONE;
                  no login/session code was located; whether this
                  component is invoked only locally is UNKNOWN or
                  unconfirmed. Each of those is exactly the shape of
                  the vulnerability this domain exists to catch
                  (authentication that should exist but doesn't), not
                  evidence the domain doesn't apply.

authorization     Excluded only when the baseline positively confirms,
                  under the SAME source/confidence bar as authentication
                  above: (i) this component is invoked ONLY by a
                  trusted local operator or an already-authorized
                  caller (same reasoning as authentication's fact (i) --
                  without this, "the operator already has direct access"
                  reasoning below cannot be trusted to describe who is
                  actually calling); AND (ii) no object, resource, or
                  operation whose access should ever be restricted by
                  identity/role exists anywhere the review's scope
                  reaches, given who is confirmed to be calling under
                  (i) -- nothing to authorize at all. BOTH required, for
                  the same reason as authentication above. NOT
                  sufficient to exclude: no access-control decision was
                  found; no ownership/role check was located; an
                  endpoint exists with no visible authorization logic;
                  whether this component is invoked only locally is
                  UNKNOWN. Each of those is exactly the BOLA/IDOR/
                  missing-authorization shape this domain exists to
                  catch.

secrets-security  Excluded only when the baseline positively confirms
                  (same source/confidence bar) that no credential, key,
                  token, or connection secret of any kind is used
                  anywhere the review's scope reaches -- fully public,
                  no database/service/integration requiring a
                  credential, no signing or encryption key. Unlike
                  authentication/authorization above, this condition
                  does NOT depend on who invokes the component -- a
                  component either uses a credential somewhere in its
                  own code/config or it does not, regardless of caller
                  identity -- so no separate invocation-context fact is
                  required here. NOT sufficient to exclude: the
                  baseline's `secretSources` fact is empty, UNKNOWN, or
                  NONE; no explicit "credential source" was catalogued.
                  A baseline that has not yet found a credential source
                  is exactly the situation an undiscovered hardcoded
                  secret (the vulnerability this domain exists to
                  catch) would produce -- indistinguishable, from the
                  baseline's own perspective, from "there really is
                  none."
```

**`[CORRECTED, per a fifth-round independent review Blocker]`**: an
earlier revision of this table let authentication/authorization be
excluded on facts (ii)/(iii) alone (no session code; no visible
resource needing restriction), treating the invocation-context fact
(now (i) in each row above) as relevant only to Group 3's file-security
mitigation. That earlier revision's own Case 1b then correctly noticed
invocation-context becoming `UNKNOWN` and concluded — wrongly — that
authentication/authorization were "unaffected," because its own rule
text never actually required that fact for those two exclusions in the
first place. But the reasoning each row already gave for its own
exclusion condition depends on invocation context being confirmed: a
component with no session code can still be the exact place
authentication is missing if something OUTSIDE it, uncertain whether
trusted, is what actually reaches it; "the operator already has direct
access" is not a safe authorization argument if it is not confirmed
that the operator is who is actually calling. Making fact (i)
explicitly required (not merely relevant to a different domain's
mitigation) closes this — see Case 1b below for the corrected
conclusion this produces.

**Why "evidence whose scope covers the entire component under
review" is a separate requirement, not decoration**: a positive
confirmation that one file, module, or endpoint has no identity concept
does not license excluding `authentication` for the whole review if
the review's scope includes other code the confirmation never
examined. The exclusion must be as wide as the thing being excluded
from, never wider than what was actually checked.

**Group 3 — domains whose risk requires a mechanism or surface to be
present**: `web-security`, `api-security`, `data-security`,
`file-security`. `[REDESIGNED, per explicit instruction, after a ninth
independent review round found yet another gap even after five rounds
(4-8) of revising this group's condensed conditions]`: this group no
longer states a natural-language condition summarizing each cited
play's Scope section. Five consecutive independent-review rounds found
a gap between a condensed condition stated here and the actual,
complete Scope section it was meant to summarize —
`web-security`'s row alone was revised three times (rounds 6, 7, 8) and
round 9's own fresh, item-by-item re-derivation still found it missing
a case (Case 2's own conclusion, not the row itself, overclaimed what
its premise supported); `api-security`, `data-security`, and
`file-security` were each found to have the identical defect the first
time any round checked them item-by-item at all (round 8), and round
9's item-by-item pass over all 42 items across the four plays found a
further uncovered item in two of them (`data-security`'s "Insecure
random generation," `api-security`'s "Request smuggling indicators,"
and one `file-security` "Temporary files" sub-case). This was never a
one-round diligence gap — it is what happens every time a condensed
copy of another file's list is maintained by hand: some review round
finds the specific place it has drifted, gets it re-synchronized, and
a later round finds a different place it has drifted again, because
nothing structurally ties the copy to its source. The fix is
structural, not another revision of the same table: **this table names
the domain and points directly at the authoritative source; it does
not summarize that source's content.**

**Authoritative source, per domain — read directly, never restated
here**:

```text
web-security       plays/web-security.md's own Scope section
api-security        plays/api-security.md's own Scope section
data-security         plays/data-security.md's own Scope section
file-security          plays/file-security.md's own Scope section
```

**Execution rule (replaces the four condensed conditions this section
used to state)**: to decide whether a Group 3 domain is applicable,
consider EVERY item currently listed in the cited play's own Scope
section against the target project's actual architecture evidence —
not a subset, not a representative sample, and not whatever a worked
example below happens to walk through. A domain is applicable UNLESS
every one of its play's Scope items can be positively ruled out for the
target project, under the same evidentiary discipline Group 2 already
requires: positive evidence that the item's underlying scenario has no
context to apply in, never merely that a signal or mechanism for it was
not found. **Insufficient evidence, a Scope item whose applicability is
genuinely unclear, or a gap in what this document itself says about
that item, is never a valid reason to exclude the domain** — "this
table doesn't mention that Scope item" cannot be a rule-out, because
this table intentionally states no items for anything to be silently
missing from; the play's own Scope section is the complete and only
source of what must be checked. This is the same default-toward-
inclusion stance Group 2 already uses, extended here from "one concern
per domain" to "every item in a list, per domain." An implementer that
cannot enumerate a play's current Scope items reliably (a novel or
future play format, a parsing failure) must default the domain to
applicable rather than skip the check silently.

**What this table used to state, and why it is not restated here**: a
condensed condition for each of these four rows existed through this
section's revision history (see `round4-disposition.md` through
`round9-disposition.md` for exactly what each one said and every defect
found in it). Maintaining a second, hand-written copy of four plays'
Scope sections inside this design document produced five independent
defects across five rounds; the only mechanism that reliably catches a
copy diverging from its source is a copy-vs-source comparison run every
time, not another human re-reading it once more. That comparison is
`implementation-batches.md` Batch 0's new coverage-check acceptance
criterion — an executable check against the plays' actual, current
Scope sections, not more prose here.

**`[DISCLOSED, per a fourth-round independent review]` `[UPDATED,
Batch 0 implementation]`**: checking some Group 3 Scope items requires
baseline facts that, at the time this section was written, did not
exist in `templates/project-security-baseline.md`'s key list (`runtime`,
`framework`, `hosting`, `authentication`, `authorization`, `database`,
`orm`, `frontend`, `externalServices`, `fileStorage`, `secretSources`,
`backgroundJobs`, `adminSurfaces`, `publicSurfaces`,
`securityMiddleware`, `sensitiveData`) — for example, `data-security`'s
Scope items require a "cryptographic operations present" fact, and the
disclosed-limitation mitigation below requires an "externally-invoked /
trusted-input-only" fact. **Both have since been added** to that
template as `cryptographicOperations`/`externallyInvokedTrustedInputOnly`
during Batch 0's own implementation (see that file's own `[ADDED, V4
Batch 0]` note) — this paragraph is left in place, not deleted, as the
historical record of why they were added; `tools/context_manifest/domains.py`
is the actual, executable consumer of the resulting per-item facts (a
further reasoning step beyond these two coarse baseline keys alone —
see that module's and the template's own notes on why there is no 1:1
field mapping). Checking every Scope item, not just these two,
genuinely extended the baseline fact schema in places; it did not
merely consult existing keys throughout.

**`[OPEN, disclosed limitation, found via Jev-assisted check, human-
verified]`**: this algorithm reads the TARGET repository's own
architecture facts — it cannot see how that repository is invoked from
OUTSIDE itself. A component with "no web framework, no network access"
in its own baseline can still be attacker-reachable if something not
visible in this repository's own scan (a separate web application
shelling out to it, a CI pipeline passing it externally-sourced input)
supplies its arguments. Per `plays/project-security-baseline.md`'s own
"Unknowns are valid" principle, when a project's baseline cannot
positively confirm that its inputs are exclusively human-operated
(trusted-only), that is an `UNKNOWN`, not a confirmed safe fact — the
applicability algorithm must not silently treat an absent
"externally-invoked" signal as evidence of safety. Mitigation: when
this specific fact is `UNKNOWN` rather than `USER_CONFIRMED`/
`CODE_EVIDENCE` as genuinely human-operated-only, `file-security`
(Group 3) remains applicable by default — the same "default to higher
scrutiny when unclear" bias `plays/security-change-detection.md`
already applies elsewhere in this kit, not a new principle invented
here. `code-review` needs no such mitigation, since Group 1 already
makes it unconditionally applicable regardless of this fact. Group 2's
own rule (above) already builds the same "default to scrutinized,
evidence required to exclude" bias directly into `authentication`/
`authorization`/`secrets-security` for a different reason (their risk
IS a control's absence, not merely unclear reachability) — this
disclosed limitation and Group 2's rule are two applications of the
same underlying principle to two different gaps, not one mechanism
covering both.

**`[PROPOSED, added per a fourth-round independent review Minor]` No
baseline, or a stale one**: this algorithm depends on baseline facts
existing. Per `plays/project-security-baseline.md`'s own "When to
build one" guidance, a DEEP-mode review is exactly the "security-
sensitive work needs project context" case that guidance already says
justifies building the relevant subset — so a DEEP-mode manifest
producer must trigger that build (or refresh a stale one) before this
algorithm runs, rather than deferring discovery to
`skills/security-review/SKILL.md` step 2's own "if it exists and is
fresh" check, which is written for the ordinary case where a manifest
is consumed downstream of architecture discovery, not produced
upstream of it. Until a fresh baseline exists: Group 2's domains
already default to applicable under their own rule with no baseline at
all (no positive confirmation is possible without facts, so the
inclusive default applies automatically, unaffected by this
paragraph). Group 3's four domains cannot yet be confirmed present OR
absent — per this kit's existing "default to higher scrutiny when
unclear" bias, they also default to applicable until the fresh build
completes; evidence not yet gathered is a different state from
evidence gathered and showing absence, and only the latter can exclude
a Group 3 domain.

**`[PARTIALLY MITIGATED in Batch 0, per round-5/6/7 independent
review]`**: this paragraph's requirement was written (fourth review
round) long before Batch 0's actual code existed, and Batch 0's own
`skills/security-review/SKILL.md` step 1 wiring for DEEP did not
originally carry it forward — a stale (`status: "STALE"`) baseline fact
could still be read as a fresh HIGH-confidence positive exclusion
(round 5). Two further independent-review rounds each found the
previous fix's own claim about what was mechanically guaranteed was
narrower than stated (round 6: "regardless of what the calling step
does" was false for the great majority of this algorithm's facts,
which `templates/project-security-baseline.md` itself discloses have
no 1:1 raw-baseline-key mapping at all; round 7: even the remaining
narrow claim was false, since `producer.build_manifest()` accepts
already-built `Fact` objects, so nothing stops a caller from
hand-building one without ever going through the conversion helper).
Given two successive attempts to draw a "this part is code-enforced,
this part is prose-only" line each turned out to be wrong, this note
stops drawing one: **no part of this is a mechanical guarantee.**
`domains.py`'s `fact_from_baseline_entry()` is a safe conversion helper
available to whoever builds `baseline_facts` — using it prevents one
specific, common way of misreading a stale raw baseline entry — but
freshness discipline for every fact this algorithm reads is
fundamentally a requirement on the reviewing agent's own judgment, the
same way item 0's sensitivity classification already is, not something
this batch's code can verify was followed. `SKILL.md` step 1's DEEP
branch now states this plainly rather than implying a stronger
guarantee. See `fact_from_baseline_entry()`'s own docstring and
`tests/test_domains.py`'s `BaselineFreshnessGatingTests` for exactly
what the helper itself does and does not cover.

**Worked examples — illustrative of the algorithm's reasoning pattern,
not an authoritative or certified audit** `[REDESIGNED, per explicit
instruction]`: these four cases demonstrate how Group 1/2/3's rules
combine; they are not, and cannot be, a substitute for checking a real
project's evidence against the plays' current Scope sections directly.
Round 9 found Case 2's own conclusion had quietly overclaimed beyond
what its premise supported (see Case 2 below) — a direct demonstration
that even a worked example describing its own reasoning is not immune
to the same drift a condensed table row was. These examples may become
stale if a cited play's Scope section changes after this revision; that
is a documentation-maintenance question for this file, not a security
gap in the algorithm, because the algorithm's own authoritative check
(the execution rule above, and `implementation-batches.md` Batch 0's
coverage check) always reads each play's current Scope section
directly and never consults these examples.

```text
Case 1 -- negative example, pure Python CLI. `[CORRECTED, per a tenth-
round independent review Minor: an earlier revision claimed every
excluded domain was ruled out "item-by-item," which its own text
directly contradicted for api-security ("rules out most items") and
did not actually address for file-security's ZIP/archive items at
all -- fixed by adding the missing fact rather than by weakening the
claim, since this example is also Batch 0's fixture source for
criterion 6(a) and needs to actually support the count it asserts]`.
Baseline positively confirms (source: CODE_EVIDENCE + USER_CONFIRMED,
confidence: HIGH) ALL of: (a) it is only ever invoked interactively by
a trusted local operator, not wrapped by any other system; (b) no code
anywhere in it implements a session, login, or identity-distinction
concept of any kind; (c) it accesses no object or resource whose
access should ever be restricted by identity/role -- it operates only
on files the invoking operator already has direct filesystem access
to; (d) it uses no credential, key, token, or connection secret of any
kind; (e) it performs no cryptographic operations and handles no data
the baseline's "Sensitive data" fact would flag; (f) it generates no
security-relevant random values of any kind (no tokens/keys/nonces) and
makes no outbound TLS/HTTPS connections; (g) it deserializes no objects
and parses no XML from any source; (h) it creates no files, temporary
or otherwise, whose name, path, or storage location an attacker --
including a co-located, lower-privileged local process -- could
predict, influence, or write to, and creates none in a shared or
world-writable location; (i) it extracts no archives (ZIP or otherwise)
and creates none. No network access, no web framework, reads/writes
only files named in its own command-line arguments, a small
requirements.txt.
  Applicable: code-review, configuration-security, dependency-security
  (Group 1, unconditional for DEEP).
  NOT applicable: authentication (Group 2 -- (a)+(b) together positively
  confirm both required facts); authorization (Group 2 -- (a)+(c)
  together); secrets-security (Group 2 -- (d) alone, independent of (a));
  web-security (Group 3 -- no network access/web framework rules out
  every item in plays/web-security.md's Scope, since none of them have
  any HTTP/browser surface to act on with no network interface at all);
  api-security (Group 3 -- no API/outbound call rules out every item
  requiring one; (g) additionally rules out insecure
  deserialization/XXE specifically, independent of whether an API
  exists; the two remaining items (rate limits, request smuggling) also
  require an HTTP-facing surface this CLI does not have); data-security
  (Group 3 -- (e) rules out the cryptographic-primitive items; (f)
  additionally rules out insecure random generation and
  certificate-validation bypass, neither of which (e) alone covers);
  file-security (Group 3 -- (a) rules out the attacker-influenced-input
  items; (h) additionally rules out the temporary-file and
  storage-location items, which (a) alone does not cover; (i) rules out
  ZIP extraction and archive creation specifically (`[CORRECTED, per an
  eleventh-round independent review Nit: an earlier revision's summary
  named only "extraction," though the fact itself already covered both
  -- "and creates none"]`), since the attacker there is the archive's
  own content, not the invoking caller (a) already covers).
  3 of 10 applicable. This is the case demonstrating the corrected
  algorithm still allows genuine exclusions under the new execution
  rule -- every excluded Group 3 domain here is ruled out item-by-item
  against its play's actual Scope section, not by a condensed
  condition.

Case 1b -- the same CLI, but fact (a) is UNKNOWN rather than positively
confirmed (the more common, realistic case for most real projects) --
facts (b)-(i) remain positively confirmed:
  Applicable: code-review, configuration-security, dependency-security
  (Group 1, unchanged) PLUS authentication and authorization (Group 2 --
  (a) is UNKNOWN, so their required two-fact confirmation fails; an
  unconfirmed invocation context does NOT license excluding either
  domain) PLUS file-security (Group 3 -- per the disclosed-limitation
  mitigation above, an unconfirmed invocation context keeps
  file-security applicable regardless of (h)/(i), since the
  mitigation's own concern -- attacker-reachable input this repository's
  own scan cannot see -- does not depend on temp-file or archive
  behavior specifically).
  NOT applicable: secrets-security (Group 2 -- (d) alone, never
  depended on (a)); web-security, api-security, data-security (Group 3
  -- none of their ruling-out facts above ((e)/(f)/(g), "no network
  access/web framework") depend on (a) either; only file-security's
  exclusion did, via the disclosed-limitation mitigation specifically).
  6 of 10 applicable here, not Case 1's 3 -- this is the case
  demonstrating that Group 2's and Group 3's domains do not all move
  together as a block when a single fact becomes uncertain.

Case 2 -- positive example, partial set, ASP.NET file-download app
(the fixed-case-3 shape). `[CORRECTED, per a ninth-round independent
review Minor]`: an earlier revision's premise established "renders no
HTML anywhere" but concluded web-security was excluded because "no
browser-executed content" existed -- the premise does not support that
broader claim (a download endpoint could still serve an attachment
whose content type is HTML/SVG, which a browser may render inline
without an explicit disposition header). Premise, each fact sourced:
bearer-token authentication, an `Authorization: Bearer <token>` header,
verified server-side, never a cookie (`CODE_EVIDENCE`, `HIGH`); renders
no HTML anywhere in its own code (`CODE_EVIDENCE`, `HIGH`); every
downloadable response is sent with `Content-Disposition: attachment`,
never inline, regardless of content type (`CODE_EVIDENCE`, `HIGH` --
this is the fact the premise was missing); ships no browser-side script
of any kind, server-only codebase (`CODE_EVIDENCE`, `HIGH`); sets no
CORS headers and does not register itself for cross-origin browser
access (`CODE_EVIDENCE`, `HIGH`); issues no HTTP redirect whose target
is influenced by user input (`CODE_EVIDENCE`, `HIGH`); whether any
browser-based client, same-origin or not, actually calls this API is
`UNKNOWN` (this is the genuinely external, unconfirmable fact; it does
not defeat any of the CODE_EVIDENCE facts above, all of which are
directly observable in this codebase's own source regardless of who
calls it); per-object authorization checks; a file-download endpoint
(also the application's only exposed API surface); a SQL database whose
downloadable records the baseline's "Sensitive data" fact flags as
containing customer financial records; deployed via web.config (and
therefore a connection string in application configuration, per
`plays/secrets-security.md`'s own "Manual fallback" section's "Also
inspect" list -- that file has no `## Scope` section).
  Applicable: code-review, configuration-security, dependency-security
  (Group 1); authentication, authorization, secrets-security (Group 2 --
  each applicable via ordinary positive evidence of presence); api-security,
  data-security, file-security (Group 3 -- each applicable because at
  least one item in its play's Scope section is positively evidenced:
  the file-download endpoint for api-security, the flagged sensitive-data
  fact for data-security, the download operation itself for
  file-security -- Group 3 domains need only one Scope item to apply,
  unlike an exclusion, which needs every item ruled out).
  NOT applicable: web-security only (Group 3 -- checked against
  plays/web-security.md's own Scope section directly, item by item: XSS
  and CSP weaknesses (no HTML/script ever produced, and the new
  attachment-disposition fact closes the inline-content route the prior
  revision missed); CSRF (bearer-token only, never a cookie);
  Clickjacking (no page produced to embed); Unsafe postMessage and
  Unsafe DOM operations (no browser-side script exists at all); Open
  redirect (no redirects issued); CORS misconfiguration (no CORS
  headers, no cross-origin browser registration). All eight items
  individually ruled out by a specific fact above, not by a condensed
  condition).
  9 of 10 apply here.

Case 3 -- positive example, full set, cross-domain application: a
full-stack product with a browser-rendered admin UI, a public REST API,
user authentication and role-based authorization, payment/PII handling,
file uploads, a dependency manifest, credential-based integrations, and
deployment configuration.
  Applicable: all ten -- every Group 3 domain has at least one Scope
  item positively evidenced (the browser-rendered admin UI alone
  satisfies web-security; the rest follow from the premise directly).
  This is the case proving the algorithm does not artificially cap
  below ten either.
```
6. Scanner-domain consistency: `[TIGHTENED, per independent review]`
   every domain in `domains` maps (per `plays/scanner-selection.md`'s
   domain-to-tool table) to a tool that is either in `scannersSelected`,
   in `scannersSkipped` with a reason (tool was never relevant), or in
   `coverageGaps` with a reason (tool was relevant but unavailable/
   failed) — a domain whose mapped tool is silently missing from all
   three lists is a validity failure. Distinguishing `scannersSkipped`
   from `coverageGaps` matters: a manifest that mislabels an
   unavailable-but-relevant tool as merely "skipped" hides a real
   coverage hole behind wording that reads like an intentional
   optimization.
7. Budget floor: `[REVISED, per the section-7 decision]` recompute
   `reviewBudget` via the single merged `computeReviewBudget(reviewMode,
   sensitivity, factorsEvidence)` function `v4-design.md` section 7
   defines (starting point by `reviewMode` -- TARGETED keys off item 0's
   classified `sensitivity` via the Default starting point table;
   QUICK/STANDARD default to FOCUSED; DEEP defaults to AUDIT -- then
   Factors adjustment, capped at one level for TARGETED, UNCAPPED for
   QUICK/STANDARD/DEEP per `plays/review-budget.md`'s own "Explicit
   mode" section), and confirm the manifest's `reviewBudget` is not
   *below* that recomputed value. `[CORRECTED, per a third-round
   independent review]`: an earlier draft treated the explicit-mode
   *starting point* (FOCUSED/AUDIT) as an unconditional *floor*,
   directly contradicting `plays/review-budget.md`'s own text ("An
   explicit `DEEP` request that turns out to touch nothing
   security-sensitive can move from the `AUDIT` starting point all the
   way down to `MINIMAL`") and `tests/validation/v3-review-budget-test-cases.md`
   cases 7/7b, which exist specifically to test that downward movement.
   The single merged function now applies Factors identically regardless
   of which `reviewMode` produced the starting point, with only the
   movement CAP differing by mode -- there is one computation, not two
   separately-described ones that can disagree with the play's actual
   rules in different ways. `[ALSO CORRECTED]`: for TARGETED
   specifically, this floor is computed by the exact same function the
   built-in layer itself calls to produce its own `reviewBudget` — an
   earlier draft claimed this meant the floor "always equals the
   built-in layer's own answer, leaving no savings margin," which is
   true only if Jev is given no additional Factors evidence beyond what
   the built-in layer already used. Jev's actual savings opportunity in
   `reviewBudget` (as opposed to reference depth/`priorityOrder`/
   `intelligenceConsulted`, which retain their own savings margins
   regardless) is now honestly narrow for TARGETED specifically, and
   this is disclosed rather than reasserted as "fully intact" the way an
   earlier draft claimed.
8. degradation field self-consistency: if jevOutcome is anything other
   than "success," fallbackUsed must be true and producedBy must be
   "built_in" — a manifest cannot claim a Jev failure occurred while
   still being attributed to Jev.
```

**`[OPEN, disclosed limitation]`**: item 0's classification quality is
bounded by the same limits `skills/security-change-detection`'s own
classification already has today (its four sensitivity lists are
"examples, not an exhaustive taxonomy," and an uncovered stack or novel
pattern relies on the classifier's own judgment rather than a lookup
table) — V4 inherits this limitation rather than solving it, and its
"default higher when unclear" bias is the same existing mitigation V3
already relies on, not a new one invented here.

**Why the domain floor and the built-in layer's own domain selection
coincide by construction, and what "coincide" does and does not mean**
`[CORRECTED, per a fourth-round independent review Minor — the earlier
heading here ("do not force the Jev path to always match") stated the
opposite of what this paragraph's own body says]`: because item 0's
classification work (for TARGETED/QUICK/STANDARD) and section 3a's
algorithm (for DEEP) are identical regardless of producer — both the
built-in layer and the floor check consult the *same* non-Jev
classification/algorithm — the domain floor and the built-in layer's
own domain selection coincide by construction, not by coincidence:
there is exactly one classification result, used both to produce the
built-in manifest and to floor-check Jev's. "Coincide" means the floor
and the built-in layer's own domains are identical; it does not mean
Jev's own manifest must be identical to the built-in layer's — per
`v4-design.md` section 4.2's Option A, Jev may still declare a superset
(more domains than the floor, never fewer), so a Jev-produced manifest
matching the floor exactly and one adding an extra domain out of
caution are both valid, and both differ from "always match" in the
sense the earlier heading implied.

**`[CORRECTED, per a third-round independent review]` `reviewBudget`'s
own savings margin is honestly narrower than an earlier draft claimed
for the TARGETED path specifically.** Item 7's floor is now computed by
the exact same merged function (`v4-design.md` section 7) the built-in
layer itself calls — so for TARGETED, Jev's `reviewBudget` savings
opportunity depends entirely on Jev supplying Factors evidence the
built-in layer's own pass did not already have (a real but narrower
opportunity than "the floor never constrains it," which was the
previous claim). For QUICK/STANDARD/DEEP, the uncapped Factors
adjustment gives Jev meaningfully more room (the same function, but
without TARGETED's one-level movement cap), so the savings claim holds
more strongly there. The token-saving opportunity that remains
unconditionally available on every `reviewMode`, regardless of this
narrowing, is reference *depth* within a domain
(`plays/review-budget.md`'s Context budget section — untouched) and
`priorityOrder` — neither of which item 7 or item 5 constrains.

**Positive test cases (must pass), alongside the negative one above**:
a manifest declaring exactly the item-0-implicated domain set; a
manifest declaring a superset of it (extra domains, e.g. also including
"authentication" out of caution — corrected from an earlier draft's
invalid "session-management" example, which is not one of
`skills/security-review/SKILL.md`'s ten domain names); a manifest for a
genuinely non-security-relevant change, where item 0 classifies NONE
and requires nothing further.

Any failure -> discard the whole manifest (do not attempt to patch the
one failing field in place — see `v4-design.md` section 4.3 for why) ->
fall back to the built-in layer -> re-run this same check against its
output (expected to always pass, since the built-in layer's own
manifest IS item 0's classification result, by construction).

**`[OPEN]`**: whether a manifest that fails validity is itself
recorded as an Adaptive Project Security Intelligence fact (so a
recurring pattern of, say, Jev consistently under-scoping a specific
repo/task shape becomes visible over time) or discarded with no trace
beyond that one review's own log — named in `v4-design.md` section 8,
item 1.

## 4. Security fact / control record schema (Core 2's general record shape)

Extends `plays/project-security-baseline.md`'s existing 5-part fact
schema (`Value`/`Confidence`/`Source`/`Evidence`/`Freshness`) with the
fields your original request required: evidence, scope, confidence,
dependencies, last validation, invalidation conditions. Mapping:

```text
Existing V3 field  ->  V4 field            Change
-----------------      -----------------   ------------------------------
Value                  value                unchanged
Confidence             confidence           unchanged scale: HIGH / MEDIUM
                                            / LOW / UNKNOWN — still NOT
                                            plays/finding-validation.md's
                                            HIGH/MEDIUM/LOW vulnerability-
                                            confidence scale (same
                                            distinction V3 already draws;
                                            V4 does not reintroduce that
                                            collision)
Source                 source               unchanged: USER_CONFIRMED /
                                            CODE_EVIDENCE / CONFIG_EVIDENCE
                                            / INFERRED / NONE
Evidence               evidence             unchanged: {path, observation}
Freshness              (subsumed by         see dependencies below —
                       dependencies)        generalized, not renamed away
(none)                 scope                [NEW] see 4.1
(none)                 dependencies         [NEW] see 4.2
(none)                 lastValidation       [NEW] see 4.3
(none)                 invalidationConditions [NEW] see 4.4
```

### 4.1 `scope` — what this record does and does not generalize to `[NEW, PROPOSED]`

A plain-text (or short structured) boundary statement: what code
shape, pattern, or condition this record's conclusion actually covers.
Example: *"applies to EF Core parameterized queries following this
project's `UserRepository` pattern; does not generalize to raw ADO.NET
usage elsewhere in this codebase."* This directly answers the
requirement that a Feedback-Learning rejection reason must not be
silently over-generalized to a candidate that merely looks similar —
see section 5.

**`[PROPOSED, corrected a second time after independent review]`**:
the general rule for *this* section (the generic fact/control record,
which has no `safetyPattern` — that field exists only on the Feedback
record subtype in section 5) is: `scope`'s width must never exceed what
`evidence.observation` actually demonstrates. For the Feedback record
subtype specifically, the sharper version of this rule and its actual
enforcement mechanism live in section 5.1's check (a) — an earlier
draft stated this enforcement claim here, referencing a field
(`safetyPattern`) that does not exist at this general level, and
described (a) as doing something its own written text did not actually
do (see section 5.1 for the corrected mechanics: a scope-width bound is
now an explicit, separate condition within check (a), not an implied
side effect of "falls within scope" — which, left unqualified, gets
*easier* to satisfy as scope widens, the opposite of what this
paragraph needs).

### 4.2 `dependencies` — generalized `freshnessOf` `[NEW, PROPOSED]`

V3's `freshnessOf` is a list of *files*. `dependencies` keeps that
(Selective Invalidation still runs the same changed-files-set lookup,
unchanged mechanism) but allows a dependency to also name something
narrower than a whole file — e.g. "the parameterization pattern in
`UserRepository.cs`'s `FindByNameLike` method" rather than just
"`UserRepository.cs`" — because a file can change in ways that don't
touch the specific pattern a record actually depends on. **`[OPEN]`**:
whether sub-file dependency granularity is actually implementable
reliably (it requires more than a changed-files-set diff — likely a
symbol- or line-range-level diff) or whether this stays file-level for
V4's first version and the extra precision is deferred. Flagged, not
assumed solved.

**`[PROPOSED, added after Jev-assisted review, human-verified]`**: a
plain file-list `dependencies` check has a structural blind spot —
a change to a file the record's author never thought to list (a shared
base class, a shared repository helper, a global configuration file)
would not trigger re-validation even though it may genuinely affect
the record's continued validity. Rather than inventing new machinery
for this, reuse `plays/security-impact-analysis.md`'s and
`plays/review-budget.md`'s existing "broader invalidation for
central/load-bearing components" exception (the same one that already
covers routing/auth-bootstrap/config for baseline facts and
attack-surface nodes, and the same "shared authentication/authorization
middleware, shared path resolver, shared HTTP client factory, shared
repository/data-access layer, shared deserialization helper" qualitative
list `plays/review-budget.md`'s "Changed attack-surface centrality"
section already names): when a changed file is this kind of central
component, flag every Feedback record whose `candidateShape.category`
or evidence path falls within a domain the central component touches
for re-check, even if that specific file was never in the record's own
`dependencies` list — the same bounded-widening principle already
governs this exception elsewhere in the kit, not a new, separately
unbounded one invented for Feedback records specifically.

### 4.3 `lastValidation` `[NEW, PROPOSED]`

```text
timestamp
commit (or equivalent state marker)
validatedBy: "human | code_reviewer_subagent | validator_procedure"
```

**Jev is never a valid value for `validatedBy`** — this is the schema-
level enforcement of the permission boundary in `v4-design.md` section
5: Jev may have *consulted* or *referenced* a record (see
`intelligenceConsulted` in section 1), but consulting is not
validating, and the schema must not make it possible to record Jev as
the thing that last validated a security-relevant fact.

### 4.4 `invalidationConditions` `[NEW, PROPOSED]`

Explicit, checkable conditions under which a record must be treated as
stale even though no file in `dependencies` literally changed —
example: "if the EF Core package version changes to one where this
parameterization default changed." **`[OPEN]`**: V3's entire
invalidation mechanism today is file-diff-driven
(`plays/security-impact-analysis.md`'s "Incremental invalidation").
A condition like a dependency-version bump needs either (a) treating
the dependency manifest file itself as a `dependencies` entry (works
today, no new mechanism needed, but coarse — *any* manifest change
would re-trigger, not just a change to the specific package), or (b) a
genuinely new periodic/triggered check outside the file-diff model.
This design does not resolve which; it names the gap so
`implementation-batches.md`'s batch 1 scopes it explicitly rather than
assuming `dependencies` alone already covers it.

## 5. Feedback record schema (Core 2's record for a Validator rejection)

A subtype of section 4's general record, specific to reusing a
`REJECTED` result from `plays/finding-validation.md`'s existing Result
vocabulary (unchanged).

```jsonc
{
  "recordType": "feedback_rejection",
  "candidateShape": {
    "category": "string",          // e.g. "SQL injection", matches a
                                    // CWE-shaped finding category.
                                    // [NOW LOAD-BEARING, per a
                                    // third-round independent-review
                                    // Blocker] this field is one of the
                                    // occurrence-identity conditions
                                    // (section 5.1) -- two candidates
                                    // at the identical sink and path
                                    // but DIFFERENT categories (e.g.
                                    // "SQL injection" vs. "missing
                                    // tenant isolation" on the same
                                    // query) are different occurrences
    "suspicionPattern": "string",  // [RENAMED, see note] the code
                                    // pattern that made the ORIGINAL
                                    // candidate look suspicious, e.g.
                                    // "user input reaches a raw SQL
                                    // string build"
    "safetyPattern": "string",     // [NEW, added after independent
                                    // review found a Blocker in the
                                    // original single-field design --
                                    // see the note below] the SPECIFIC
                                    // mechanism that makes this
                                    // occurrence NOT exploitable, e.g.
                                    // "query is bound via
                                    // command.Parameters.AddWithValue,
                                    // not string-interpolated"
    "reachabilityPath": [           // [NEW, added after a SECOND
                                    // independent-review Blocker --
                                    // see the note below] the ordered
                                    // chain of {path, symbol} this
                                    // candidate's rejection was
                                    // actually traced through, entry
                                    // point to sink, per
                                    // plays/cross-file-data-flow.md's
                                    // multi-hop procedure. THIS, not
                                    // evidence.path alone, is what
                                    // "the same occurrence" means for
                                    // any finding whose safety depends
                                    // on WHICH caller reaches the sink,
                                    // not just the sink itself
      {"path": "...", "symbol": "..."}
      // [CORRECTED, per Batch 1's qualifiedSymbol redesign, closing a
      // FIFTH recurrence of this same occurrence-identity-imprecision
      // pattern -- concrete counterexamples: two C# classes each
      // declaring an overload of the same method name distinguished
      // only by parameter type, and two Python classes each declaring
      // a same-named method]: this hop's bare `symbol` field is
      // RENAMED to `qualifiedSymbol` and schema.py now refuses the most
      // obviously bare shapes (no qualification marker at all, or only
      // one bare marker character) -- a SYNTACTIC FLOOR, per a Round 3
      // independent review Minor, not a guarantee that any
      // well-formed-looking value it accepts is actually unique for
      // the language in question (schema.py's own `_looks_unqualified`
      // docstring says this explicitly; it was this doc's summary here
      // that overstated it) -- see templates/feedback-store.md and
      // plays/finding-validation.md's own "Feedback Learning" section
      // for the actual rule text (not restated a third time here). An
      // optional `lineRange: {start, end}` may also be present per
      // hop -- evidence-location metadata only, never part of
      // occurrence identity. This is schema version 2; a store or
      // record still in the bare-`symbol` shape shown directly above
      // is schema version 1 and loads as audit-only, never reusable
      // (tools/feedback_store/identity.py's own per-record guard).
    ]
  },
  "rejectionReason": "string",     // reused text, same content as
                                    // plays/finding-validation.md's
                                    // existing "Rejected findings"
                                    // reason field — not reinvented.
                                    // [CLARIFIED, count corrected after
                                    // reachabilityPath was added] this
                                    // is prose for a human reader;
                                    // candidateShape's OTHER fields
                                    // (category, safetyPattern,
                                    // reachabilityPath) are what reuse
                                    // eligibility actually checks
                                    // against, not this one
  "evidence": {"path": "...", "observation": "..."},
                                    // [CLARIFIED] "path" is always the
                                    // FULL repository-relative path of
                                    // the candidate's own location --
                                    // never a bare filename -- so
                                    // identity comparisons can never
                                    // collide on two files sharing a
                                    // basename (e.g. two unrelated
                                    // UserRepository.cs files in
                                    // different fixture directories)
  "scope": "string",                // section 4.1
  "dependencies": ["path", "..."],  // section 4.2. [CLARIFIED] derived
                                    // directly from reachabilityPath
                                    // above (every path entry in that
                                    // chain is a dependency) PLUS any
                                    // additional file the trace
                                    // consulted without it being part
                                    // of the reachability chain itself
                                    // (e.g. a config value that gates
                                    // the control). reachabilityPath
                                    // answers "is this the same
                                    // occurrence"; dependencies answers
                                    // "which file changes should
                                    // trigger a re-check" -- related,
                                    // not identical, questions, and
                                    // dependencies is always at least
                                    // as large as reachabilityPath's
                                    // own path list
  "lastValidation": {"timestamp": "...", "commit": "...", "validatedBy": "..."},
  "invalidationConditions": ["string", "..."],  // section 4.4
  "reuseCount": 0                   // [PROPOSED, mechanics now defined
                                    // -- see 5.1] how many times this
                                    // record has been reused without a
                                    // full re-check
}
```

**Note on `candidateShape`'s split into two fields** (closes an
independent-review Blocker in the single-field design): a single
`patternDescription` describing only "what made the candidate look
suspicious" cannot discriminate between two occurrences that are
*equally* suspicious-looking but differ in the one detail that
actually matters — `tests/fixtures/cross_file_sql_safe/UserRepository.cs`
(parameterized) and `cross_file_sql_unsafe/UserRepository.cs`
(string-interpolated) both "look suspicious" by the same description
("user input reaches a raw SQL string build" fits both). Splitting into
`suspicionPattern` (why it was flagged at all) and `safetyPattern` (the
specific, checkable reason it was rejected) means section 5.1's reuse
check can require the *safety* mechanism specifically — not just the
suspicious shape — to still be present before reusing a rejection.

**Note on `reachabilityPath`** (closes a SECOND, later independent-
review Blocker, found only after the first was fixed): `evidence.path`
alone identifies *where the sink is*, not *how the candidate reaches
it*. For a finding whose safety depends on which caller reaches the
sink — authorization/BOLA findings are the clearest case, but not the
only one — two different callers reaching the identical sink can have
completely different safety properties (one goes through an
authorization check on its way in, another does not). An identity rule
based on `evidence.path` alone would treat a NEW caller that reaches an
old, already-`REJECTED` sink through a path the original record never
saw as "the same occurrence" — which is exactly backwards, since a new,
unvetted path to a sensitive sink is precisely the shape that most
needs fresh validation. `reachabilityPath` makes explicit that a
Feedback record's safety conclusion is scoped to *one specific path*,
never to "this sink, however it's reached" — abandoning any implicit
claim to the latter, broader (and unverifiable) proposition entirely,
rather than trying to detect every way it could later become false.

### 5.1 Reuse eligibility and stale-reason re-review — the acceptance mechanics `[PROPOSED, revised a third time]`

**`[PROPOSED, revised a third time after two rounds of independent
review]`**: round one tightened "same occurrence" to require
re-inspecting actual code rather than matching by file/method name.
Round two found that was not sufficient — a candidate at the exact same
*sink*, re-verified, could still pass every check while the reason it
was rejected quietly stopped being true elsewhere in the call chain —
and added check (d) plus mandatory `dependencies`. **A second
independent review then found round two's fix itself incomplete**: it
could still be defeated by a NEW caller reaching the same sink through
a path the original rejection never covered — the upstream control the
old record depended on stays completely intact, but a different route
to the same sink bypasses it entirely. This is fixed by changing what
"occurrence identity" is defined over: not the sink alone, but the full
`reachabilityPath` (schema section 5's note) — a record's safety
conclusion is now explicitly scoped to *the one path it was actually
traced for*, and a genuinely new path to the same sink is, by
construction, never eligible to match it at all.

**Occurrence identity, defined precisely** `[PROPOSED, revised a fourth
time after a THIRD independent-review round]`: a new candidate is *the
same occurrence* as an existing Feedback record only if **all** of:
(i) `evidence.path` (the sink) is identical (full path, never a bare
filename); (ii) `candidateShape.category` is identical — `[NEW, closes
a third-round Blocker]` the same sink reached the same way can still be
the subject of two *unrelated* candidates (e.g. the same query is both
"is this SQL-injectable" and, separately, "does this leak another
tenant's rows") — a record about one category must never be consulted
for a different category at the same location, even if every other
condition matches; (iii) `reachabilityPath` matches **exactly**: the
same ordered chain of `{path, symbol}` pairs, compared entry-by-entry
on both fields — `[CLARIFIED, closes a third-round Major]` a match on
file paths alone, ignoring `symbol`, is NOT sufficient (see the worked
counterexample in section 5.2's Case 6: a new method added to an
already-listed file, reachable through the same file-level chain but a
different symbol, must not match); and (iv) the current code at every
location the path covers, re-inspected directly, still matches
`candidateShape.safetyPattern` specifically (not merely
`suspicionPattern`, which two opposite-outcome fixtures can share
identically). Failing (i), (ii), or (iii) means the candidate is a
**different occurrence** and is never checked against this record at
all — it goes straight to full validation, the checks (a)-(d) below
never even apply. Only a candidate that already matches on sink,
category, and exact reachability path proceeds to (a)-(d) to decide
whether its *specific* rejection is still current.

**`[NEW, closes a third-round Major]` `reachabilityPath` may only be
recorded from a HIGH-confidence trace.** `plays/cross-file-data-flow.md`'s
own confidence model allows MEDIUM (one hop inferred, not directly
observed) and LOW (dynamic dispatch/reflection/DI indirection the play
itself says "can't be reliably confirmed") results. A `reachabilityPath`
built from anything less than a fully-observed, HIGH-confidence trace
must not be persisted as a Feedback record at all — a truncated or
inferred chain is *more* permissive to match against than the real one
would be (fewer entries to compare, less to disagree with), which is
exactly the wrong direction for an identity check whose entire purpose
is to be strict. When the trace cannot reach HIGH confidence, the
candidate's rejection (if any) is not cached for reuse; it is simply
re-derived every time it recurs, which is the safe default this
situation reduces to.

Before a Feedback record is *reused* (its conclusion applied to a new
candidate already confirmed to be the same occurrence, without
re-deriving it), all of the following must hold — failing any one
forces full re-derivation instead:

```text
(a) Pattern + scope match [RESTORED a third-round condition an earlier
    fix had accidentally dropped]: the current code along
    reachabilityPath, re-inspected directly, still matches
    candidateShape.safetyPattern, AND the specific candidate falls
    within the record's stated `scope` (section 4.1), AND `scope`
    itself is no wider than what safetyPattern and evidence.observation
    together actually demonstrate. These are TWO conditions, not one:
    "candidate falls within scope" bounds THIS candidate against the
    record's stated boundary; "scope is no wider than the evidence"
    bounds the record's own boundary against what was actually
    verified. Dropping either one independently reopens a reuse gap --
    the first without the second lets an author write an overly broad
    scope that still nominally "contains" everything; the second
    without the first (the state after the prior revision) checks the
    record's own width but never actually confirms the CANDIDATE is
    within it. This is NOT fully mechanically decidable in every case
    -- unlike (b)/(c)/(d) below, which are plain diff/condition/evidence
    checks, (a) requires re-inspecting actual code against a
    natural-language description.
    `[OPEN, disclosed limitation]`: where the match is genuinely
    ambiguous, the required default is FAIL CLOSED -- treat it as NOT
    matching, and go through full re-derivation -- never fail open by
    assuming a match to save effort. This is the same fail-closed
    default plays/security-design.md's own question 9 and
    plays/finding-validation.md's LOW-confidence handling already apply
    elsewhere in this kit, not a new principle invented here.

(b) No invalidationConditions have become true (section 4.4).

(c) No dependencies have changed per Selective Invalidation's existing
    diff-based check (section 4.2 / plays/security-impact-analysis.md,
    unchanged mechanism), including section 4.2's central-component
    broader-invalidation extension. Since dependencies now derives from
    reachabilityPath (schema section 5), this check covers every file
    along the verified path by construction, not by an author's
    separate, possibly-incomplete judgment call.

(d) [Re-scoped to use reachabilityPath's structured data, not free-text
    rejectionReason] the code at each intermediate {path, symbol} entry
    in reachabilityPath -- not just the terminal sink evidence.path --
    is re-inspected directly to confirm the control it represents is
    still present and unchanged. Because reachabilityPath is structured
    (file + symbol pairs), this check has a concrete, enumerable list of
    locations to re-visit, rather than depending on parsing what
    rejectionReason's free-text prose happens to name -- an earlier
    draft used rejectionReason as (d)'s input, which schema section 5
    itself documents as "prose for a human reader," not a field reuse
    eligibility was ever meant to parse. Same fail-closed default as
    (a) when ambiguous.
```

**`[OPEN, disclosed residual risk, not fully resolved]`**: this design
scopes every Feedback record to one specific, previously-traced
reachability path — it does not, and structurally cannot, protect
against a path that did not exist when the record was created. A new
caller added to the codebase that reaches an already-`REJECTED` sink
through a genuinely new route is never matched against the old record
(by the occurrence-identity definition above), so it is NOT silently
exempted from validation — but whether that new route is actually
*examined at all* depends on the review that introduces it correctly
generating a candidate for it in the first place (an ordinary
consequence of it being new code in that review's own diff, per
`skills/security-review`'s unchanged workflow), not on anything this
Evidence Reuse mechanism itself guarantees. This is disclosed as a
boundary of what Evidence Reuse is responsible for, not a gap silently
left in the reuse check itself: reuse eligibility's job is to never
wrongly *exempt* a genuinely different path, which this design achieves
by construction; it was never Evidence Reuse's job to guarantee a new
path gets discovered, and this document does not claim otherwise.

If (a), (b), (c), or (d) fails, the record is **not** reused — the
candidate is treated as fresh and goes through `skills/security-validate`'s
full procedure again, unchanged authority. If it resolves the same way
again, the record's `lastValidation`/`evidence` are refreshed (new
timestamp, re-confirmed evidence) rather than assuming the old text
still describes current reality — the record is never just
"re-stamped" without actually re-deriving.

**`[PROPOSED]` `reuseCount`'s actual effect** (an independent review
found the original draft named this field a "safety-valve" without
ever defining one): after a record has been reused a threshold number
of times (`[PROPOSED placeholder]` 20, tunable) without a full
re-derivation, force one full re-derivation through (a)-(d) and
`skills/security-validate` regardless of whether (a)-(d) would
otherwise have passed, then reset the counter. This bounds how long a
record can go without an actual fresh look, independent of whether its
own dependency/invalidation-condition tracking happens to be complete
for a given case.

**Feedback records never suppress scanner execution or candidate
generation.** `plays/scanner-selection.md`'s domain-to-tool mapping
runs unchanged regardless of any Feedback record's existence, and
`skills/security-review`'s workflow still generates a candidate for
anything matching a scanner hit or the manual semantic analysis step's
own reasoning. A Feedback record's *only* effect is deciding whether an
already-generated candidate that passes (a)-(d) above skips
re-derivation — it can never prevent a candidate from being generated
in the first place. This is the structural reason Feedback Learning
cannot evolve into permanently ignoring a scanner rule: the rule itself
is never disabled, only the last step (re-deriving an unchanged,
identical occurrence's already-known conclusion) is short-circuited,
and only after (a)-(d) all hold.

### 5.2 Acceptance test shape — five discriminable cases (for `implementation-batches.md` batch 1, not written now)

**`[CORRECTED, per Batch 1 implementation, itself per a round-1
independent review Nit]`**: this section's own title still says "five"
even though the body below adds a sixth case (Case 6, the same-file/
different-symbol check) after a third independent-review round —
`implementation-batches.md`'s and `measurement-plan.md`'s own "five"
references share this same drift. The body's own "Acceptance bar: all
six cases must resolve as described" is authoritative; this title was
simply never updated when Case 6 was added. Not rewritten in place
here, per this kit's own history-preservation discipline — flagged so
whoever next revises this section corrects the title too.

**`[PROPOSED, revised a third time]`**: grounded in fixtures this
session has actually re-read in full for this revision (not assumed
from memory — an earlier revision's Case 1/Case 4 asserted
`UserSearchService.cs` contains an allowlist that, on inspection, does
not exist in that fixture; corrected here by switching to
`tests/fixtures/cross_file_object_authz_safe/`, whose cross-file
control — `ReportService.GetReport`'s ownership check, verified present
in that file's current text — is exactly the shape these cases need). A
fifth case (Case 5) was added because an independent review's own
constructed counterexample (a new caller bypassing an untouched
upstream control) is not the same failure shape as Case 4 and neither
of the first four cases exercises it.

```text
Case 1 -- safely reusable ("可安全重用"):
  A Feedback record exists for the candidate at
  tests/fixtures/cross_file_object_authz_safe/ReportRepository.cs's
  FindById, reached via ReportsController.GetReport ->
  ReportService.GetReport -> ReportRepository.FindById (symbol names
  verified against the fixture's actual current text): evidence.path is
  FindById's full repository-relative path; category = "BOLA/IDOR";
  reachabilityPath = [{ReportsController.cs, GetReport},
  {ReportService.cs, GetReport}, {ReportRepository.cs, FindById}];
  candidateShape.suspicionPattern =
  "object reference taken from a caller-supplied ID with no visible
  ownership check at the sink itself"; candidateShape.safetyPattern =
  "ReportService.GetReport enforces report.OwnerUserId ==
  currentUserId before returning the result"; dependencies include all
  three files (derived from reachabilityPath). A LATER, unrelated
  review re-examines the same repository; nothing changed, the
  ownership check in ReportService.cs is still present and unchanged.
  Expected: (a)/(b)/(c)/(d) all hold -> reused, skills/security-validate
  is NOT re-invoked.

Case 2 -- stale rejection reason, SINK's OWN code changes ("舊拒絕理由已失效，sink 自身位置改變") [RESTORED, per third-round review: an
earlier draft of this case had drifted into duplicating Case 4's shape]:
  A SEPARATE Feedback record (not Case 1's) exists for
  tests/fixtures/cross_file_sql_safe/UserRepository.cs's
  FindByNameLike: evidence.path is that sink's own full path;
  reachabilityPath = [{UserSearchService.cs, SearchUsers},
  {UserRepository.cs, FindByNameLike}]; safetyPattern = "query bound
  via command.Parameters.AddWithValue, not string-interpolated". A
  LATER maintenance edit changes FindByNameLike's OWN implementation to
  reintroduce string concatenation for one parameter. Expected: (a)
  fails on direct re-inspection of the SINK's own entry in
  reachabilityPath (current code no longer matches safetyPattern) ->
  NOT reused -> full skills/security-validate procedure runs again ->
  correctly resolves CONFIRMED for the reintroduced concatenation ->
  lastValidation/evidence refreshed. This is the sink-local regression
  shape; contrast with Case 4 below, which is the same shape but for an
  INTERMEDIATE hop, not the sink itself -- both are needed since a
  naive implementation could special-case "the sink changed" without
  correctly generalizing to "any hop on the path changed."

Case 3 -- looks similar, different occurrence, must NOT be excluded
("看似相似但攻擊路徑不同"):
  The SAME Case-1 record exists. A genuinely different candidate
  arises using tests/fixtures/cross_file_sql_safe/ vs.
  cross_file_sql_unsafe/'s UserRepository.FindByNameLike pair (a
  different vulnerability category and a different fixture family
  entirely, at a different full evidence.path) -- included to confirm
  identity comparison is by full path, never by symbol/category
  resemblance alone. Expected: evidence.path alone already
  distinguishes this from Case 1 -> the two records are never compared
  at all -> full skills/security-validate procedure runs on the SQL
  candidate independently, correctly resolving CONFIRMED HIGH for
  cross_file_sql_unsafe (already hand-traced to this result during the
  V3 Slim Golden Baseline closeout) and REJECTED for cross_file_sql_safe.

Case 4 -- upstream control removed, candidate's own reachabilityPath
entries unchanged in isolation, but one of them changed
("同一條路徑上的控制被拿掉"):
  The SAME Case-1 record exists. A LATER change removes the ownership
  check from ReportService.GetReport specifically along the SAME
  reachabilityPath Case 1 recorded (this is a restatement of Case 2's
  shape phrased to confirm (c)/(d) also independently catch it, not
  only (a) -- multiple checks agreeing is expected here, not a sign
  one of them is redundant. All three -- ReportsController.cs,
  ReportService.cs, ReportRepository.cs -- are in dependencies per
  reachabilityPath; ReportService.cs changed -> (c) fails; (d)
  re-inspecting that same file's specific control independently finds
  it gone). Expected: NOT reused -> full skills/security-validate
  procedure runs -> correctly resolves CONFIRMED.

Case 5 -- [NEW] a genuinely NEW caller reaches the same sink through a
DIFFERENT path; the original path's control is completely untouched
("新增呼叫路徑繞過既有控制，原路徑本身未變") -- the second
independent-review counterexample, made concrete:
  The SAME Case-1 record exists, and ReportService.GetReport's
  ownership check remains completely intact and unchanged. A LATER
  change adds a NEW file (e.g. a background export job) that injects
  ReportRepository directly and calls FindById(reportId) with a
  caller-supplied ID from a queue message, with NO ownership check
  anywhere on this new path. Expected: reachabilityPath comparison
  (schema section 5.1's precondition, checked BEFORE (a)-(d)) finds
  this candidate's path -- {NewJob.cs, the handler} -> {ReportRepository.cs,
  FindById} -- does not match Case 1's recorded path at all (different
  entry point, missing the ReportService.cs hop entirely) -> this is a
  DIFFERENT occurrence by definition -> Case 1's record is never
  consulted, (a)-(d) never even run against it -> the new candidate is
  treated as entirely fresh -> full skills/security-validate procedure
  runs -> correctly resolves CONFIRMED (no ownership check on this
  path). This is exactly the shape Case 4's same-path re-check cannot
  catch (Case 1's own path is untouched), which is why identity had to
  be redefined over reachabilityPath rather than sink location alone,
  and why this case is not simply "another instance of Case 4."

Case 6 -- [NEW, third independent-review round] a NEW method is added
to an ALREADY-LISTED file, reachable through the SAME file-level chain
but a DIFFERENT symbol ("同一組檔案鏈，不同 symbol，必須視為不同路徑"):
  The SAME Case-1 record exists (reachabilityPath =
  [{ReportsController.cs, GetReport}, {ReportService.cs, GetReport},
  {ReportRepository.cs, FindById}]). A LATER change adds a NEW method
  ReportService.GetReportForExport(int reportId) that calls
  ReportRepository.FindById(reportId) directly with NO ownership
  check, called from a NEW ReportsController action. The new
  candidate's path -- [{ReportsController.cs, <new action>},
  {ReportService.cs, GetReportForExport}, {ReportRepository.cs,
  FindById}] -- shares every FILE with Case 1's recorded path, but
  every SYMBOL differs except the terminal sink. Expected: identity
  condition (iii) requires an exact {path, symbol} match at every
  position, not a file-path-only match -- the differing symbols at
  positions 1 and 2 mean this does NOT match Case 1's record -> DIFFERENT
  occurrence -> full skills/security-validate procedure runs ->
  correctly resolves CONFIRMED. This is the case a file-path-only
  implementation of reachabilityPath comparison would pass every one of
  Cases 1-5 while still failing -- included specifically because Case
  5's own distinguishing reason ("missing the ReportService.cs hop
  entirely") does not, by itself, rule out a file-path-only
  implementation, which this case does.
```

**Acceptance bar**: all six cases must resolve as described. Case 1
and Cases 4/5/6 specifically depend on `tests/fixtures/cross_file_object_authz_safe/`
actually having the cross-file ownership-check shape asserted above —
this was verified by reading `ReportService.cs`'s and
`ReportsController.cs`'s current text for this revision (symbol names
included), not assumed; Case 2 similarly depends on
`cross_file_sql_safe/`'s actual parameterization, also re-verified.
Case 3 requires full-path identity comparison. Case 5 requires
reachabilityPath comparison to run as a precondition BEFORE (a)-(d) are
even reached. Case 6 requires that comparison to match on **both**
`path` and `symbol` at every position, not file paths alone — an
implementation that only compares `evidence.path` and skips
`reachabilityPath` entirely would fail Case 5; one that compares
`reachabilityPath` but only its file-path components, ignoring
`symbol`, would pass Case 5 yet still fail Case 6. Both implementation
mistakes are distinct and both are now covered.

## 6. Storage and versioning

**`[OPEN]`** (named in `v4-design.md` section 8, item 3): whether
Feedback records live in a new `.security/feedback.json` or as a new
section inside one of the two existing files.

**`[PROPOSED]`** direction: a new `.security/feedback.json`, to avoid
growing `.security/baseline.json`'s and `.security/attack-surface.json`'s
already-tested schema surface and their own version-compatibility
history. Reuses, unchanged, both existing files' established fallback
rule for an unrecognized `schemaVersion`: treat the whole file as
untrustworthy, report that it needs rebuilding, fall back to building
the relevant subset fresh — the same handling `plays/project-security-baseline.md`
and `plays/attack-surface-mapping.md` already specify for their own
files, extended to this one rather than inventing a different rule for
a third file.

## 7. What this schema does not do

It does not replace or modify `.security/baseline.json`'s or
`.security/attack-surface.json`'s existing schemas. It does not
implement anything — every JSON shape above is a proposal for review,
not a committed contract.
