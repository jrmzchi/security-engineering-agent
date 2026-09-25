# Play: Finding Validation

Authoritative procedure for `skills/security-validate`, and the shared
confidence/severity models used across every other play.

## Purpose

The validator does not assume the reviewer (or a scanner) is correct. For
every HIGH/CRITICAL candidate, independently reconstruct the case for and
against it being real.

## Procedure, per candidate finding

```text
Reconstruct the attack path
    -> attacker capability -> entry point -> controlled data
       -> vulnerable operation -> boundary crossed -> impact
Confirm attacker control
    -> is the data at the sink actually traceable back to something an
       attacker supplies, or does it only look similar to attacker input?
Confirm code reachability
    -> is this code path actually reachable given routing, feature
       flags, authentication requirements already in front of it?
Confirm sink behavior
    -> does the sink actually do what the candidate assumes? (e.g. does
       this ORM method actually build raw SQL, or does it parameterize?)
Inspect sanitization
    -> is there an encoder/escaper/sanitizer between source and sink
       that the initial pass missed?
Inspect validation
    -> is there an allowlist/type check/schema validation that would
       reject the attack payload before it reaches the sink?
Inspect authorization
    -> even if the technical vulnerability is real, does an
       authorization check limit who can trigger it, changing the
       actual impact?
Inspect framework protections
    -> see plays/code-review.md's "Framework-provided protections"
Inspect environmental constraints
    -> is the vulnerable code path only reachable in a build/environment
       that never runs against real data (e.g. test-only, feature-flagged
       off in production)?
Determine realistic impact
    -> given all of the above, what can an attacker actually achieve?
```

## Result

Every candidate resolves to exactly one of:

```text
CANDIDATE             not yet validated — the state every finding starts
                      in when security-reviewer (or a scanner) produces
                      it, before this procedure runs
CONFIRMED             the attack path holds up under independent scrutiny
REJECTED              the attack path does not hold; state which link broke
NEEDS_VERIFICATION    plausible but a required fact could not be
                      established from available evidence (e.g. cannot
                      determine at review time whether a middleware runs
                      before this handler)
```

`CANDIDATE` is this procedure's input, not one of its outputs — every
candidate this procedure runs on must exit as one of the other three.
(Note the naming: `NEEDS_VERIFICATION` — with an underscore, matching
the ALL_CAPS convention used across every other machine-readable status
in this project. `plays/security-gate.md`'s `AWAITING_VALIDATION` and
`plays/security-remediation.md`'s `FIX_UNVERIFIED` are deliberately
different names, not typos — see those plays for why a candidate
awaiting its first validation pass, and a fix whose re-validation was
inconclusive, are kept distinct from this status rather than reusing
it. `plays/attack-surface-mapping.md` DOES reuse this exact name for an
unresolvable graph node/edge — that one is a safe reuse rather than
another instance of this collision, because a map node/edge and a
finding are never the same object, even though a finding's validation
can consult the map while it's in progress (a `NEEDS_VERIFICATION` map
node and a `NEEDS_VERIFICATION` finding can coexist at the same time
without ambiguity, precisely because nothing ever has to ask "which
one of these two do you mean?" about a single thing); see that play's
"Evidence-backed mapping" section for why it didn't need its own new
name the way the two above did. `plays/attack-chain-analysis.md`
similarly reuses it for a chain whose linkage can't currently be
confirmed — same reasoning: a chain and a finding are never the same
object either, so this is a third safe reuse, not a third instance of
the collision.)

Always state the reason. Worked example:

```text
Candidate: SQL injection in UserRepository.cs
Reviewer evidence: user input reaches a database query.
Validator discovers: Entity Framework parameterizes the value through
    a LINQ expression; the code does not use FromSqlRaw/ExecuteSqlRaw.
Result: REJECTED
Reason: attacker-controlled input does not modify query structure.
```

## Confidence model

```text
HIGH      attack path clearly demonstrated end-to-end with concrete
          evidence at every link (file/line for source, transformation,
          sink; no missing step)

MEDIUM    likely exploitable, but some environment/runtime detail is
          missing that would need to be confirmed to call it HIGH (e.g.
          reachability depends on a deployment configuration not visible
          from source)

LOW       a suspicious pattern exists (e.g. a dangerous sink with
          attacker-influenced input somewhere upstream) but exploitability
          cannot currently be demonstrated with the evidence at hand
```

**LOW confidence findings must not normally be presented as confirmed
vulnerabilities.** Use `NEEDS_VERIFICATION` instead, and say what
evidence would resolve it.

## Severity model

```text
CRITICAL
HIGH
MEDIUM
LOW
INFORMATIONAL
```

Severity considers, together, not any single factor in isolation:

```text
Exploitability          how hard is this to actually trigger?
Required privileges      does the attacker need to already have an
                        account, a specific role, or network position?
User interaction         does a victim need to click/open/run something?
Data sensitivity         what kind of data or capability is exposed?
Blast radius             one user's data, all users' data, the whole
                        system?
System privileges        does successful exploitation grant further
                        system access (RCE, admin)?
Internet exposure        is the vulnerable surface reachable from the
                        public internet, or only from an internal
                        network / requires prior internal access?
Business impact          financial, legal/compliance, reputational
```

**Do not assign CRITICAL simply because the vulnerability belongs to a
traditionally dangerous CWE category.** A textbook SQL injection with no
real exploitation path (e.g. gated behind an internal admin-only tool
requiring existing high privilege, on an air-gapped internal network) may
reasonably be MEDIUM. A seemingly minor information-disclosure bug that
leaks a session token to any unauthenticated caller can be CRITICAL.

## Attack path requirement (HIGH/CRITICAL)

Every HIGH or CRITICAL finding must be able to state the full chain:

```text
Attacker capability
  |
Entry point
  |
Controlled data
  |
Vulnerable operation
  |
Security boundary crossed
  |
Impact
```

If any link cannot be shown with evidence, downgrade confidence or mark
`NEEDS_VERIFICATION` — do not report it as confirmed HIGH/CRITICAL on the
strength of the parts that *can* be shown.

`skills/security-review/SKILL.md` states this same chain with a
seven-node breakdown (`Attacker -> Input source -> Data transformation ->
Validation -> Security controls -> Sensitive sink -> Security impact`) for
use while tracing a candidate during initial review. The two are the same
model at different granularity, not competing versions — the SKILL.md
version splits "Vulnerable operation" into the transformation/validation/
controls/sink steps that matter most for a data-flow vulnerability. Use
whichever granularity fits the finding; do not treat a mismatch in node
count between the two documents as a discrepancy.

**Exception — exposure-type findings.** Some finding categories are not
data-flow vulnerabilities and do not have a "Controlled data" or
"Vulnerable operation" node to fill in: a confirmed leaked credential, a
known-CVE dependency reachable at runtime, or a production deployment
with debug/verbose-error mode enabled. For these, the exposure itself —
plus its reachability and blast radius — is the evidence; do not
downgrade a confirmed active credential leak, a reachable known-CVE
dependency, or a confirmed production misconfiguration to LOW confidence
or NEEDS_VERIFICATION merely because it has no "Vulnerable operation"
step to cite.
Apply the full attack-path chain to data-flow vulnerabilities (injection,
XSS, SSRF, IDOR, deserialization, and similar); apply severity based on
exposure and blast radius (see the severity model above) to secrets,
dependency, and configuration findings.

**Rule — a sink whose callers are outside the review scope.** `[V4
release]` A vulnerable operation often sits in a method that nothing in
the reviewed files calls: a repository, data-access or library method
whose own parameters reach the sink. The "Entry point" and "Controlled
data" links then depend on callers the review cannot see. Resolve it
this way, every time, so the same code never gets different statuses:

```text
The method is callable from outside its own file (public/exported, or
internal to an assembly/package the review does not fully cover), and a
parameter reaches the sink with no sanitization, validation or
parameterization in between
    -> treat that parameter as attacker-controlled: the method's own
       signature is the trust boundary, because nothing in scope
       constrains what a caller passes
    -> if the sink's unsafe behavior is itself shown from the code
       (e.g. the value is concatenated into raw SQL), the result is
       CONFIRMED; state in the finding's evidence that attacker control
       rests on this rule (callers outside the review scope)
    -> assign severity from the severity model as usual; the unseen
       callers may be one reason to lower it, never a reason by
       themselves to use NEEDS_VERIFICATION

An in-scope caller exists
    -> trace the real callers instead; this rule does not apply, and a
       caller that provably constrains the value can still make the
       candidate REJECTED
```

`NEEDS_VERIFICATION` remains the answer when a required fact about the
sink, or about a control inside the reviewed code, cannot be
established — not merely because the callers are out of scope. This rule
is a defined reading of the "Entry point" link above, like the
exposure-type exception; it does not relax the chain for anything else.

## Baseline origin

For a diff-aware or development-time review specifically (see
`plays/code-review.md`'s "Diff-aware review" and
`plays/secure-development-workflow.md`), tag each finding with where it
came from relative to the current change:

```text
INTRODUCED     the vulnerable code is part of the current diff and did
               not exist before it
MODIFIED       code that existed before was changed by the current
               diff, and the change is what makes it vulnerable (or
               changes how it's vulnerable)
PRE_EXISTING   the vulnerable code is unchanged by the current diff —
               found while reviewing surrounding context, not because
               the diff touched it
UNKNOWN        git history isn't available or conclusive enough to tell
```

Do not attribute a `PRE_EXISTING` issue to the current change — that
misdirects both credit and urgency triage. But do not suppress a severe
`PRE_EXISTING` finding either just because it wasn't introduced now;
report it, clearly labeled `PRE_EXISTING`, alongside whatever the
current diff actually introduced. This tag is orthogonal to
CONFIRMED/REJECTED/NEEDS_VERIFICATION and to severity — a finding has
both.

## Vulnerability chaining

Individually moderate findings can combine into something more serious.
Examples:

```text
IDOR + predictable file ID + sensitive file download
    = HIGH data exposure (each alone might be MEDIUM/LOW)

Unrestricted upload + static execution directory
    = remote code execution
```

Look for chains explicitly, but **do not artificially combine unrelated
findings** just to inflate severity — a real chain requires that
exploiting the first finding actually enables reaching the second.

## Rejected findings

Keep rejected candidates available for audit transparency rather than
discarding them silently:

```text
Rejected candidate: SQL injection in UserRepository.cs
Reason: input reaches an EF query through a parameterized LINQ
    expression. No query-structure control demonstrated.
```

Do not clutter the main report with every rejected scanner warning —
store the detailed rejected list separately (see
`templates/security-report.md`'s "Rejected Candidate Findings" section)
and keep the main findings summary focused on what survived validation.

## Feedback Learning — reusing a REJECTED result `[V4 Batch 1]`

**Cached results are never treated as permanently correct.** Before
this play's own procedure re-derives a REJECTED conclusion from
scratch, check whether an existing, still-eligible Feedback record
already covers this exact occurrence — but only skip re-derivation
when that record passes every one of the checks below; otherwise run
this play's procedure in full, same as if no record existed at all.
Full field-level schema, the exact algorithm, and the acceptance test
cases live in `work/v4-planning/context-manifest-schema.md` sections
4/5/5.1/5.2 — this section states the procedure, not a second copy of
that schema.

```text
1. Candidate generated (scanner hit, or this play's own manual
   analysis) -- exactly as it would be with no Feedback store at all.
   A Feedback record NEVER changes which candidates get generated or
   which scanners run (tools/feedback_store/ has no code path that
   could -- see that package's own negative-control tests).
2. Search .security/feedback.json (tools/feedback_store/store.py) for
   a record whose category/sink/reachabilityPath COULD match.
3. Occurrence identity precondition (tools/feedback_store/identity.py):
   same sink (full repository-relative path), same category, and the
   SAME ORDERED reachabilityPath (every {path, qualifiedSymbol} hop,
   comparing qualifiedSymbol as an exact string -- not the sink alone,
   not just the trailing method name, not with any parameter signature
   stripped -- a new caller reaching an old sink through a path the
   original record never saw is a DIFFERENT occurrence, full stop).
   `[ADDED, per the qualifiedSymbol redesign, schema-version 2]`:
   `qualifiedSymbol` must carry enough namespace/type/signature
   identity that two genuinely different callables can never collide
   under it (a bare "GetReport(int)" with no enclosing type does NOT
   suffice -- two different classes could each declare one); a hop
   missing this, or a record built under the older schema version that
   never had it at all (a "legacy" record), NEVER matches for reuse
   regardless of how well everything else lines up -- go straight to
   step 5, the same outcome as any other identity mismatch. Each hop
   MAY also carry an optional `lineRange` -- this is evidence-location
   metadata only, never compared here: a pure line shift at an
   otherwise-unchanged hop (e.g. a comment inserted above it) must
   never by itself change whether identity matches, but reaching this
   step never grants reuse by itself either -- step 4's checks still
   all run. Failing identity means the candidate is never compared
   against this record at all -- go straight to step 5.
4. Reuse eligibility (tools/feedback_store/eligibility.py), ALL FOUR
   required, always evaluated in full even if an earlier one already
   failed:
   (a) `[CORRECTED, per a round-1 independent review Minor: this
       previously said "the reachabilityPath's sink," narrower than
       what it actually requires]` re-inspect the current code ALONG
       THE WHOLE reachabilityPath (not the sink alone -- a record's
       safetyPattern can, and often does, name behavior at an
       intermediate hop, not just the terminal sink) -- does it still
       match the record's safetyPattern, and does the candidate still
       fall within the record's own scope (never assume; when
       genuinely ambiguous, FAIL CLOSED -- treat as not matching);
   (b) no invalidationConditions have become true (an UNKNOWN
       condition state counts as true, not false, for this purpose);
   (c) no file in dependencies changed (the ordinary diff-based
       Selective Invalidation check, extended to Feedback records --
       see plays/security-impact-analysis.md's "Incremental
       invalidation" and its central-component exception, which now
       also sweeps Feedback records for a central/load-bearing
       change);
   (d) re-inspect EVERY intermediate hop in reachabilityPath (not just
       the sink) -- is the specific control each one represents still
       present and unchanged.
   All four passing -> REUSE the record's conclusion; do not
   re-invoke this play's procedure. Call
   `tools/feedback_store/store.py`'s `increment_reuse_count()` for the
   reused record — this is what actually advances the reuseCount
   safety valve toward its threshold; skipping this call means the
   threshold can never be reached however many times the record is
   reused. `[ADDED, per a round-2 independent review Minor:
   increment_reuse_count() only mutates the in-memory store — nothing
   in this step said the result must actually be persisted, so the
   counter reset to whatever was last written every time the store was
   reloaded, and could never reach the threshold across separate
   review runs]` **This step is not complete until the incremented
   count is actually written back** — call `store.write()` with the
   hash `store.load()` returned earlier in this review (skip the write
   only if step 2 already reported the store as degraded, per
   `skills/security-review/SKILL.md` step 2's own note not to write to
   a degraded store). Record which Feedback record ID was reused and
   which checks were re-verified in the review's own audit trail -- a
   reuse is never silent. `[ADDED, V4 Batch 2 preflight]` **Every
   store mutator (`increment_reuse_count`, `mark_stale`,
   `mark_revalidated`, `replace_rejection_record`, `append_*`) writes a
   freshly VALIDATED COPY back into the store** (copy -> mutate ->
   validate -> commit; a failed validation leaves the store untouched).
   A record object you were holding BEFORE the call is therefore a
   stale alias afterwards -- do not keep reading or passing it; re-read
   the record from the store (`store["rejectionRecords"][record_id]`)
   for any subsequent step, including the `decide_reuse` call in step 3
   of a later candidate and the `write()` here.
5. Any check above failing (or the candidate never having matched
   identity in the first place) -> run this play's full procedure,
   unchanged authority, exactly as if no Feedback record existed.
6. After this play's procedure resolves the candidate:
   - REJECTED again, with a HIGH-confidence reachabilityPath trace ->
     `[CORRECTED, per a round-1 independent review Minor: "append a
     NEW record" could leave TWO records with identical occurrence
     identity around at once — one already-eligibility-failed
     (STALE or otherwise) and one freshly appended — with nothing in
     this step saying which one a later reuse check should even
     consult]` if a record for this EXACT occurrence already exists
     (whether marked STALE or not — this is the same record step 3's
     identity check just matched, or step 4 just failed against),
     REFRESH that record in place (`store.mark_revalidated`/
     `replace_rejection_record`) with new evidence/lastValidation --
     never just re-stamp the old text without actually re-deriving it,
     and never leave the old one sitting alongside a new one. The
     replacement record must always be built via
     `schema.new_rejection_record()` fresh (which starts `reuseCount`
     at 0) — `[ADDED, per a round-2 independent review Minor]` **never
     hand-copy the old record's own fields into a new dict**, which
     could carry the old `reuseCount` (or a stale `status`/
     `staleReason`) forward and defeat the reuseCount safety valve
     silently. Only append a genuinely NEW record when no record for
     this occurrence existed at all before this candidate.
   - REJECTED, but the trace could only reach MEDIUM/LOW confidence ->
     do NOT cache it as a reusable record at all; it is re-derived
     every time it recurs, which is this situation's own safe default.
   - CONFIRMED or NEEDS_VERIFICATION where a record for this exact
     occurrence previously said REJECTED -> that record must lose its
     reusable status (marked STALE with the reason "re-validation
     resolved differently"), preserving the history of what it used
     to say rather than erasing it, but never again treated as a
     cached "safe" conclusion.
```

**This mechanism's job is to never wrongly exempt a genuinely
different occurrence from validation, which it achieves by construction
-- it is not responsible for guaranteeing a new path gets discovered
and generates a candidate in the first place; that remains this skill's
own diff-aware workflow, unchanged.**

## Feedback Learning — human-discovered false negatives `[V4 Batch 1]`

When a human finds a vulnerability this system's own review missed (a
false negative), the required response is root-cause attribution
across four layers, not just "add one more fixture":

```text
routing         the classifier/manifest never selected the right
                domain/play for this change at all
attack_surface  the map was missing the entry point, control, or sink
                involved
cross_file_flow the flow existed in the map/domain but the multi-hop
                trace (plays/cross-file-data-flow.md) didn't connect it
reasoning       everything was in scope and traced correctly, but the
                manual semantic analysis step itself missed the
                vulnerability
```

Attribute the layer using `tools/feedback_store/attribution.py`'s
`attribute_layer()` / `record_miss()` -- it walks the four layers in
dependency order (routing first, since nothing downstream matters if
the wrong domain was never even loaded) but REFUSES to attribute
anything when a gate has no supporting evidence, rather than defaulting
to any one layer (including "reasoning," which is not a catch-all
bucket for ambiguous cases). Every layer's own evidence must positively
confirm which one actually failed — never a fixed priority order
picking whichever layer happens to be checked first.

The resulting `feedback_miss` record is stored in the SAME
`.security/feedback.json` file as rejection records, but in a SEPARATE
collection (`missRecords`) — **a missed vulnerability is never stored
as though it were a rejected candidate.** In this batch, a miss record
is auditable intelligence only: it does not automatically change
routing, the attack-surface map, a domain floor, or scanner selection.
Acting on a recurring pattern (e.g. repeated routing misses for one
framework's convention) still requires an ordinary, reviewed code or
Play change — the same discipline as any other correction in this kit.

## Remediation requirements

Remediation guidance attached to a finding (see `templates/finding.md`'s
`### Remediation` field) must be actionable, not generic:

```text
Bad:    Sanitize input.
Good:   Replace string-concatenated SQL with parameterized queries.
Better: provide a minimal safe code example appropriate for the
        framework actually in use (see references/ for the stack).
```

Prefer the smallest safe fix. Do not use a finding's remediation as an
opportunity to rewrite unrelated architecture — that is scope creep, not
remediation.

## Verification requirements

Every remediation must include verification steps the person applying
the fix can actually run (see `templates/finding.md`'s `### Verification`
field). A representative shape:

```text
1. Add a regression test covering the vulnerable path.
2. Submit the malicious/edge-case input the finding describes.
3. Confirm the vulnerable behavior no longer occurs (e.g. query
   structure is unchanged, the path stays inside the base directory,
   the redirect target is rejected).
4. Confirm legitimate requests/inputs still work as before.
```

A finding without verification steps is incomplete — "fixed" is a claim
that needs a way to be checked, not just asserted.

## Safe testing and validation boundaries

Validation and proof-of-concept work for a finding must stay defensive:

```text
Do not:
  delete or modify production data
  modify production systems
  exfiltrate or print real, unredacted secrets (see plays/secrets-security.md)
  brute-force real accounts
  perform uncontrolled network exploitation against systems you do not
      have explicit authorization to test
```

Proof-of-concept testing should use local environments, test
environments, fixtures, mock services, or otherwise safe payloads. Active
testing against a live, in-scope target requires the user to explicitly
provide the authorized environment and request that testing — do not
assume authorization from the fact that a finding exists.

## Failure handling (scanner/tool unavailability)

If a scanner is unavailable, the review continues — it does not stop.
Report the gap explicitly:

```text
Scanner unavailable: Gitleaks
Coverage impact: automated secret detection unavailable for this run.
Fallback: manual secret review performed per plays/secrets-security.md.
```

**Never claim "no secrets found" (or the equivalent for any category)
when the scanner did not run and an equivalent manual review was not
actually performed.** State the gap instead.
