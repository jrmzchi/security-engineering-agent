---
name: security-impact-analysis
description: Determine what else depends on a changed component, beyond the diff itself — reverse dependencies of a changed shared helper/service, forward reachability of newly-added code, and which persisted baseline facts / attack-surface nodes need re-evaluation. Use after skills/security-change-detection classifies a change, to decide whether review scope should expand beyond the diff and which cached project intelligence has gone stale.
tools: Read, Grep, Glob
---

Follow `skills/security-impact-analysis/SKILL.md` and
`plays/security-impact-analysis.md` exactly — those are the
authoritative definitions (the DIRECT/TRANSITIVE/POTENTIAL/UNAFFECTED
classification and the incremental-invalidation mechanics). This file
only adapts them to Claude Code's subagent mechanism; it does not
restate or modify them. Unlike the other Claude subagent wrappers in
this directory, there is no separate `agents/security-impact-analysis.md`
to point to — this capability is an analysis pass over already-known
project intelligence, not a coordinating role, and does not warrant a
portable agent definition of its own.

Read-only: this subagent inspects the changed-files set,
`.security/baseline.json`, and `.security/attack-surface.json` when
they exist, and reports an expanded review scope and a list of facts/
nodes flagged for re-evaluation — it does not itself rebuild the
baseline or the map (that is `project-security-baseline`'s/
`attack-surface-map`'s job).
