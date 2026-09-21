# Play: Security Impact Analysis

Authoritative procedure for `skills/security-impact-analysis`. Answers
a question `skills/security-change-detection` does not: not just "what
changed," but **"what else depends on what changed."** Also delivers
the Git-driven incremental-invalidation mechanics that
`plays/project-security-baseline.md` and `plays/attack-surface-mapping.md`
each deferred to this play when they were built.

## Not a replacement for security-change-detection

`skills/security-change-detection` classifies the diff itself
(NONE/LOW/MODERATE/HIGH) — a self-contained judgment about the changed
code. This play starts from that classification and asks what *else*,
beyond the diff, is affected by it — expanding review scope when
warranted, never narrowing what `security-change-detection` already
requires. A HIGH classification's required workflow
(`plays/security-change-detection.md`'s HIGH section) still applies in
full regardless of what this play finds.

## Two directions

```text
Forward flow      newly added/changed code calls existing code
                  -> is the thing it calls doing anything unsafe with
                     what this change now feeds it?
                  (already noted once, as a single example, in
                  plays/secure-development-workflow.md — this play
                  turns that example into a repeatable procedure)

Reverse impact    existing code that depends on what changed
                  -> a changed shared helper/service/component — who
                     calls it, and does the change affect their
                     security posture?
```

Use both. A changed authorization helper needs reverse impact (who
calls it, are they still protected the same way); a newly-added
controller calling an existing filesystem helper needs forward flow
(does that helper's existing behavior become dangerous now that this
new caller feeds it attacker-controlled input). Don't perform
exhaustive call-graph construction for its own sake — stop at
security-sensitive paths, per `plays/attack-surface-mapping.md`'s
"Don't over-model" principle, which applies here too.

## Consulting the Attack Surface Map for reverse impact

When `.security/attack-surface.json` exists (see
`plays/attack-surface-mapping.md`), reverse impact is a lookup: find
the node for the changed component, follow its incoming edges to see
what calls/reads/writes/depends on it. Without a map, fall back to a
direct code search for callers/references — slower, but still required;
a missing map is not an excuse to skip reverse impact.

## Impact classification

```text
DIRECT        the file/component itself was changed
TRANSITIVE    depends on something changed, and that dependency is
              security-relevant (the changed thing is on a path this
              component's security posture actually relies on)
POTENTIAL     a dependency plausibly exists but can't be confirmed
              (dynamic dispatch, reflection, configuration-driven
              wiring — same conditions that produce a LOW-confidence
              chain in plays/cross-file-data-flow.md)
UNAFFECTED    no dependency relationship found
```

**Not the same "direct/transitive" as `plays/dependency-security.md`'s
— and the direction is reversed, not just the object.** That one
classifies *third-party package* dependencies (does the manifest list
it explicitly, or does another package pull it in) for CVE
prioritization purposes: there, "direct" means "explicitly declared by
this project." Here, `DIRECT` means "this file *is* the change," and a
component that merely *calls* the changed file is `TRANSITIVE`, not
`DIRECT` — the opposite of how "direct" reads in the package sense
(where directly depending on something is the more prominent
relationship, not the less specific one). Don't transplant either
scale's intuition onto the other.

`POTENTIAL` is not license to skip it — treat it the way
`plays/finding-validation.md` treats an unconfirmable link:
`NEEDS_VERIFICATION`, state what would resolve it, don't silently drop
it to `UNAFFECTED` for convenience.

### Worked example

```text
PathResolver.cs changed (canonicalization logic tightened)
    -> PathResolver.cs itself: DIRECT (this is the changed file)

FilesController.Download    -> calls PathResolver directly, but is
                                NOT itself changed -> TRANSITIVE:
                                re-verify the download flow's path
                                handling still behaves as expected
ArchiveService.CreateZip     -> also calls PathResolver, not changed
                                -> TRANSITIVE
BackgroundExportJob           -> calls PathResolver via a factory
                                resolved by DI configuration, not
                                changed -> POTENTIAL (confirm which
                                implementation the factory returns
                                before ruling it in or out)
LoginController               -> no dependency on PathResolver
                                -> UNAFFECTED
```

Only `PathResolver.cs` itself is `DIRECT` here — everything that merely
*calls* it is, at most, `TRANSITIVE`. This is the reversal noted above:
being the thing that changed is `DIRECT`; depending on the thing that
changed is `TRANSITIVE`, no matter how directly that dependency is
expressed in code (a straight method call is still `TRANSITIVE` here,
unlike in `plays/dependency-security.md`'s sense of "direct").

## Incremental invalidation — the mechanics `baseline` and `attack-surface` deferred here

Both `.security/baseline.json` and `.security/attack-surface.json`
record a `freshnessOf` array on every fact/node/edge — the evidence
file(s) it depends on (see
`templates/project-security-baseline.md`/`templates/attack-surface-map.md`).
Given a set of changed files (from `git diff`/`git status`, including
untracked files — see `plays/secure-development-workflow.md`'s
"Post-implementation inspection", not `plays/code-review.md`'s
"Diff-aware review" section, which only covers `git diff` and does not
mention untracked files):

```text
For each fact in baseline.json:
    if any path in fact.freshnessOf is in the changed-files set:
        re-evaluate this fact (current evidence wins — see
        plays/project-security-baseline.md's "Freshness and
        invalidation"; mark STALE if evidence now contradicts it)

For each node/edge in attack-surface.json:
    if any path in its freshnessOf is in the changed-files set:
        re-evaluate this node/edge the same way (mark STALE, not
        NEEDS_VERIFICATION — see plays/attack-surface-mapping.md's
        "Evidence-backed mapping" for why those are different statuses)
```

This is a direct lookup, not a rebuild — a change to one file touches
only the facts/nodes/edges whose `freshnessOf` names that file. Do not
re-walk the whole baseline or the whole map for an unrelated change.

**This lookup cannot trigger on a fact with an empty `freshnessOf`** —
which is exactly what `templates/project-security-baseline.md` gives an
`UNKNOWN`/`NONE`-source fact (no evidence to depend on). An `UNKNOWN`
fact is often the one most likely to be resolvable by a new change (a
new `Dockerfile` appearing is exactly the kind of change that could
resolve a previously-`UNKNOWN` hosting fact). When the changed-files set
includes a file of a type that could plausibly supply evidence for an
existing `UNKNOWN`/`NONE` fact (a new deployment file, a new config
file), re-evaluate that fact too, even though the lookup above won't
surface it automatically.

**Exception — broader invalidation is justified** when the change
touches central routing, authentication/authorization bootstrap, or
other configuration that many other facts/nodes implicitly assume is
still true even though it isn't in their own `freshnessOf` list (e.g.
`Program.cs`'s authentication setup changing affects the
`AUTHENTICATION_CONTROL` node it backs, but also calls into question
every `AUTHENTICATES` edge pointing at that node). When a changed file
is this kind of load-bearing configuration, re-evaluate everything
`freshnessOf`-linked to it, **plus** every edge connected to the
node(s) it backs (both directions) — not the entire map, and not every
node "structurally reachable" from it by an arbitrary number of hops;
this exception widens the *edges* checked around a directly-hit node,
it does not license an unbounded graph walk. Recognizing which files
are this central is itself a security-relevant judgment —
`plays/review-budget.md`'s "Changed attack-surface centrality" section
now formalizes scoring it, both from a map and qualitatively without
one; this play only establishes the invalidation-scope exception
itself, why, and this bound on it.

## Output

This play doesn't introduce its own finding format or a new artifact —
its output is: an expanded (or confirmed-sufficient) review scope
(feeding `skills/security-review`), and the specific baseline
facts/attack-surface nodes marked for re-evaluation (feeding
`skills/project-security-baseline` and `skills/attack-surface-map`).
None of these three skills' own SKILL.md files reference this play
directly — but `AGENTS.md`'s "Before implementing a meaningful
software change" step 4 now routes an in-scope change through
`skills/security-impact-analysis` when it touches a changed shared
component, and `skills/security-review/SKILL.md`'s steps 2/3 "and is
fresh" checks are what actually consult the facts/nodes this play
flags. Whether the three skills should also reference this play
directly, instead of relying on that higher-level routing, is left to
a later integration batch.
