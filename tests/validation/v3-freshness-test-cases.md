# V3 Freshness and Incremental Invalidation Test Cases

Validates `plays/project-security-baseline.md`'s freshness rules,
`plays/attack-surface-mapping.md`'s equivalent, and
`plays/security-impact-analysis.md`'s "Incremental invalidation"
mechanism that drives both. See `tests/validation/README.md` for how
to run a validation pass — these cases are judgment calls against a
target repository's `.security/baseline.json` and
`.security/attack-surface.json`, not this kit's own fixtures, so
"running" a case means reasoning through the scenario against the
plays' stated rules rather than reviewing code in `tests/fixtures/`.

The underlying mechanism (see `plays/security-impact-analysis.md`'s
"Incremental invalidation") is an exact file-path lookup: for each
fact/node/edge, if any path in its own `freshnessOf` array is in the
changed-files set, re-evaluate it — nothing more, nothing content-
aware. `templates/project-security-baseline.md`'s own worked example
shows a single file (`Program.cs`) named in more than one fact's
`freshnessOf` (both a `framework` fact and an `authentication` fact) —
so "which facts go stale" depends entirely on a given target
repository's actual `freshnessOf` data, not on which topic a changed
file's *name* suggests. The cases below test the mechanism itself and
its two explicit exceptions, not a claim about which specific facts a
specific file backs in general.

## Baseline freshness cases

| # | Scenario | Expected outcome | Reason |
|---|---|---|---|
| 1 | A file changed that appears in no fact's `freshnessOf` (e.g. a CSS color value) | No fact goes stale | The lookup is a direct match against each fact's own `freshnessOf` list — see "Incremental invalidation" above; this is also consistent with `plays/project-security-baseline.md`'s "When to build or refresh one": a CSS-color change should never trigger a baseline build, and by the same logic never invalidates one |
| 2 | A file changed that IS named in a fact's `freshnessOf` (any fact — the mechanism does not care what the fact is *about*) | That fact, and only facts whose `freshnessOf` names this file, go stale | Direct lookup, not a rebuild — see "Incremental invalidation"'s explicit statement that a change to one file touches only the facts whose `freshnessOf` names it |
| 3 | An `UNKNOWN`/`NONE`-source fact exists, and the changed-files set includes a new file of a type that could plausibly supply evidence for it (e.g. a new `Dockerfile` appearing, and a hosting fact is currently `UNKNOWN`) | That `UNKNOWN` fact is re-evaluated, even though the direct-lookup mechanism alone would not surface it (an empty `freshnessOf` cannot match anything) | See "Incremental invalidation"'s explicit carve-out for this case — the direct-lookup mechanism has a documented blind spot for facts with no evidence yet, and this is the one case it names for catching it manually |
| 4 | `Program.cs`'s authentication setup changes (e.g. the `AddAuthentication(...)` call site is edited) | The broader-invalidation exception applies: re-evaluate the `AUTHENTICATION_CONTROL` node/fact this file backs, **plus** every edge connected to that node in both directions — not the entire baseline/map, and not an unbounded number of hops beyond those directly-connected edges | This is `plays/security-impact-analysis.md`'s own named example for the "broader invalidation is justified" exception — central authentication bootstrap is explicitly called out as a case where many other facts/edges implicitly assume something this file backs is still true, even though they don't name this file in their own `freshnessOf` |

## Incremental attack-surface cases

| # | Scenario | Expected outcome | Reason |
|---|---|---|---|
| 5 | One controller's action method changed, and no attack-surface node/edge outside that endpoint names this file in its `freshnessOf` | Only that endpoint's node(s)/edge(s) are marked for re-evaluation | This is what "incremental" means — see `plays/attack-surface-mapping.md`'s "Building and refreshing" and `plays/security-impact-analysis.md`'s ownership of the invalidation mechanism |
| 6 | A shared authorization handler/filter changes (e.g. a custom `IAuthorizationHandler` used by multiple controllers) | The broader-invalidation exception applies here too — this is "authentication/authorization bootstrap," one of the categories that exception explicitly names; re-evaluate every edge connected to the control node(s) it backs | Same exception as baseline case 4, applied to the attack-surface graph |
| 7 | A shared path-resolution helper changes (the shape of this batch's `PathHelper.cs` fixtures) — but it is an ordinary shared dependency, not routing/auth bootstrap/config | This does **not** trigger the broader-invalidation exception — it is handled by the ordinary mechanism: every node/edge whose own `freshnessOf` names this file is re-evaluated (which may still be several, if several endpoints depend on it), and nothing beyond that | `plays/security-impact-analysis.md`'s own worked example uses exactly this shape (`PathResolver.cs`) to illustrate the OTHER mechanism — forward-impact classification, where every caller is `TRANSITIVE`, not a trigger for the broader-invalidation exception, which that play reserves for "central routing, authentication/authorization bootstrap, or other configuration" specifically |
| 8 | An unrelated CSS change | Attack surface unchanged — nothing marked for re-evaluation | No attack-surface node/edge has evidence pointing at a CSS file |

## What these cases validate

The point of cases 1 and 8 is proving V3 does **not** rebuild or
re-review everything on every change — see
`plays/project-security-baseline.md`'s "Do not rebuild the entire
baseline after every change" and `plays/security-impact-analysis.md`'s
framing of this as an optimization/intelligence layer, not something
that regresses ordinary `skills/security-review` scope discipline (see
that skill's "Where to look next" progressive-disclosure table). The
point of cases 4 and 6 is the opposite failure mode: under-invalidating
by treating the broader-invalidation exception as if it never applies.
A validation pass that over-invalidates (treats every case above as
"re-evaluate everything," including cases 1, 7, and 8) has technically
avoided false negatives but reintroduced the cost V3 exists to reduce.
A pass that under-invalidates (misses that cases 4 and 6 are the
documented exception, not the ordinary rule) reintroduces exactly the
stale-assumption risk that exception exists to catch. Case 7 exists
specifically to test that the two are not conflated — a shared
dependency that is NOT itself security bootstrap/config does not
automatically earn the broader treatment just because it is widely
used.
