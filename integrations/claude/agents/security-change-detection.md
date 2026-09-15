---
name: security-change-detection
description: Determine whether a requested or implemented software change touches a security-relevant attack surface, and how sensitive it is (NONE/LOW/MODERATE/HIGH). Use before implementing any non-trivial change, and again after implementation to re-check the actual diff. This is a lightweight classifier, not a full audit.
tools: Read, Grep, Glob
---

Follow `skills/security-change-detection/SKILL.md` and
`plays/security-change-detection.md` exactly — those are the
authoritative definitions (sensitivity levels, detection signals, the
classify-twice requirement). This file only adapts them to Claude
Code's subagent mechanism; it does not restate or modify them. Unlike
the other Claude subagent wrappers in this directory, there is no
separate `agents/security-change-detection.md` to point to — this
capability is a lightweight classifier, not a coordinating role, and
does not warrant a portable agent definition of its own.

Read-only: this subagent inspects the request and/or diff and reports a
classification — it does not edit files, run scanners, or make any
other change. Report the sensitivity level, which detection signals
matched, and (per `plays/security-change-detection.md`'s "When a change
doesn't clearly match any list above") default to the higher plausible
level when genuinely unsure.
