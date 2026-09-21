---
name: project-security-baseline
description: Build and maintain a persistent, evidence-backed description of a target repository's security-relevant architecture (languages, frameworks, hosting, authentication, authorization, database, external services, secret sources, admin surfaces). Use when no baseline exists yet and security-sensitive work needs project context, or when explicitly asked to (re)build/refresh the security baseline.
tools: Read, Grep, Glob
---

Follow `skills/project-security-baseline/SKILL.md` and
`plays/project-security-baseline.md` exactly — those are the
authoritative definitions (the fact schema, evidence/confidence/
freshness rules, discovery procedure, storage location). This file
only adapts them to Claude Code's subagent mechanism; it does not
restate or modify them. Unlike the other Claude subagent wrappers in
this directory, there is no separate `agents/project-security-baseline.md`
to point to — this capability is a discovery pass over a target
repository, not a coordinating role, and does not warrant a portable
agent definition of its own.

Read-only for the *code* under review: this subagent inspects manifests,
configuration, and source to derive facts and reports them for the
calling agent to write to `.security/baseline.json`/`.security/README.md`
in the target repository — it does not itself decide whether to commit
that output. Never write a secret value into a reported fact — see
`plays/project-security-baseline.md`'s "Secret sources" section.
