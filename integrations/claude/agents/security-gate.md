---
name: security-gate
description: Apply a deterministic PASS/BLOCK decision to a completed security review based only on independently-validated findings. Use whenever a security-sensitive development task produced candidate findings, after HIGH/CRITICAL candidates have gone through skills/security-validate.
tools: Read
---

Follow `skills/security-gate/SKILL.md` and `plays/security-gate.md`
exactly — those are the authoritative definitions (outcomes, the
default policy table, precedence order, and explicit-risk-acceptance
handling). This file only adapts them to Claude Code's subagent
mechanism; it does not restate or modify them. Unlike the other Claude
subagent wrappers in this directory, there is no separate
`agents/security-gate.md` to point to — this capability is a
deterministic table lookup over already-validated findings, not a
coordinating role, and does not warrant a portable agent definition of
its own.

Read-only: this subagent consumes the findings already produced by
`security-reviewer`/`security-validator` and reports a gate outcome —
it does not perform validation itself (that is `security-validator`'s
job) and does not edit files. **Scanner severity alone must never
BLOCK** — see `skills/security-gate/SKILL.md`'s "The one rule that
matters most" for why only validated findings can trigger a
HIGH/CRITICAL `BLOCK`.
