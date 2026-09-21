---
name: security-impact-analysis
description: Determine what else depends on a changed component, beyond the diff itself — reverse dependencies of a changed shared helper/service, forward reachability of newly-added code, and which persisted baseline facts / attack-surface nodes need re-evaluation. Use after skills/security-change-detection classifies a change, to decide whether review scope should expand beyond the diff and which cached project intelligence has gone stale.
---

# Security Impact Analysis

What else depends on what changed. Full procedure in
`plays/security-impact-analysis.md`.

## When to use

- After `skills/security-change-detection` classifies a change, to
  check whether review scope needs to expand beyond the diff (a changed
  shared component may affect callers that never appear in the diff)
- A prior `.security/baseline.json` or `.security/attack-surface.json`
  exists and the current change may have made some of it stale
- Not needed for a NONE/LOW-sensitivity change with no shared/central
  component involved

## Not a replacement for security-change-detection

That skill classifies the diff itself. This one asks what *else*,
beyond the diff, the change affects — it can expand scope, never
narrow what `security-change-detection` already requires.

## Two directions

Forward flow (new/changed code calling existing code — is what it now
calls doing something unsafe with what it's newly given) and reverse
impact (existing code depending on what changed — who calls the
changed thing, and are they still protected the same way). Use both;
see the play for the worked reverse-impact example.

## Impact classification

```text
DIRECT        the file/component itself was changed
TRANSITIVE    depends on something changed, and that dependency is
              security-relevant
POTENTIAL     a dependency plausibly exists but can't be confirmed
              (dynamic dispatch, reflection, DI-resolved wiring) —
              treat as NEEDS_VERIFICATION, not as UNAFFECTED
UNAFFECTED    no dependency relationship found
```

Not the same "direct/transitive" as `plays/dependency-security.md`'s,
and the direction is reversed, not just the object: there, directly
depending on a package is "direct." Here, `DIRECT` means "this file is
the change" — a component that merely calls the changed file is
`TRANSITIVE`, no matter how directly it calls it. See the play for the
full disambiguation and worked example.

## Incremental invalidation

Given the changed-files set, look up which baseline facts' and
attack-surface nodes/edges' `freshnessOf` arrays name one of them —
re-evaluate only those, not the whole store. This can't catch a fact
with an empty `freshnessOf` (an `UNKNOWN`/`NONE`-source baseline fact,
which by definition has no evidence file to look up) — re-evaluate
those too when the change plausibly supplies the missing evidence. A
change to central routing/authentication/bootstrap configuration
justifies broader invalidation than its direct `freshnessOf` hits alone
would suggest, bounded to the edges around what it backs — see the
play's "Incremental invalidation" section for the exact scope.

## Output

No new artifact of its own: an expanded or confirmed review scope for
`skills/security-review`, and a list of baseline facts / attack-surface
nodes flagged for re-evaluation by `skills/project-security-baseline` /
`skills/attack-surface-map`.
