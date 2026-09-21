---
name: attack-surface-map
description: Build and maintain a persistent, evidence-backed graph of a target repository's entry points, trust boundaries, privileged operations, and sensitive sinks. Use when no map exists yet and security-sensitive work needs to know what depends on what, or when explicitly asked to (re)build/refresh the attack surface map.
tools: Read, Grep, Glob
---

Follow `skills/attack-surface-map/SKILL.md` and
`plays/attack-surface-mapping.md` exactly — those are the authoritative
definitions (the node/edge vocabulary, evidence discipline, stable-ID
convention). This file only adapts them to Claude Code's subagent
mechanism; it does not restate or modify them. Unlike the other Claude
subagent wrappers in this directory, there is no separate
`agents/attack-surface-map.md` to point to — this capability is a
discovery pass over a target repository, not a coordinating role, and
does not warrant a portable agent definition of its own.

Read-only for the *code* under review: this subagent inspects source
to derive nodes/edges and reports them for the calling agent to write
to `.security/attack-surface.json` in the target repository. Do not
guess an endpoint into existence when routing can't be confidently
resolved — mark it `NEEDS_VERIFICATION` instead (see
`plays/attack-surface-mapping.md`'s "Evidence-backed mapping").
