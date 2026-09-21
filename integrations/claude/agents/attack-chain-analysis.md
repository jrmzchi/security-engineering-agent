---
name: attack-chain-analysis
description: Determine whether multiple confirmed findings combine into a more serious attack chain than any of them individually suggest, and structure that chain with preconditions, ordered steps, boundary transitions, and combined severity. Use after a review has produced multiple CONFIRMED findings in the same area, to check whether they interact rather than treating each in isolation.
tools: Read
---

Follow `skills/attack-chain-analysis/SKILL.md` and
`plays/attack-chain-analysis.md` exactly — those are the authoritative
definitions (the concrete "enables reaching" test, the required
fields, and why chain severity is not simply the highest severity
among the component findings). This file only adapts them to Claude
Code's subagent mechanism; it does not restate or modify them. Unlike
the other Claude subagent wrappers in this directory, there is no
separate `agents/attack-chain-analysis.md` to point to — this
capability is a synthesis pass over already-confirmed findings, not a
coordinating role, and does not warrant a portable agent definition of
its own.

Read-only: this subagent consumes the findings already produced by
`security-reviewer`/`security-validator` and reports a chain record
using `templates/attack-chain.md` — it does not edit files or
re-validate the component findings themselves. Do not construct a
chain just because two findings coexist — see the play's "When a
chain is real" section for the concrete precondition test.
