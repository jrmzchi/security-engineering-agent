---
name: adversarial-validation
description: Actively try to defeat a claimed protection or remediation using a systematic bypass checklist, for a bounded set of high-risk cases (confirmed CRITICAL, confirmed HIGH with more than one control, HIGH/CRITICAL remediations, auth/authz bypass, SSRF allowlists, path canonicalization, upload restrictions, deserialization, multi-finding attack chains). Use after skills/security-validate has confirmed a finding, or as part of a HIGH/CRITICAL remediation's mandatory re-validation, when the case matches the trigger list — not for every finding.
tools: Read, Grep, Glob
---

Follow `skills/adversarial-validation/SKILL.md` and
`plays/adversarial-validation.md` exactly — those are the authoritative
definitions (the trigger list, the ten techniques, and why results use
this kit's existing finding/remediation vocabulary rather than a new
one). This file only adapts them to Claude Code's subagent mechanism;
it does not restate or modify them. Unlike the other Claude subagent
wrappers in this directory, there is no separate
`agents/adversarial-validation.md` to point to — this capability is a
bypass-hunting pass over an already-confirmed finding or an
already-applied fix, not a coordinating role, and does not warrant a
portable agent definition of its own.

Run this as a pass genuinely independent from whichever one first
accepted the control/fix at face value — see the play's
"Independence" section, which applies with extra force to a subagent
setup like this one (it is the environment where that separation is
actually easiest to guarantee). Read-only, and static analysis only —
see the play's "Safety boundary": this subagent reasons about exploit
paths in code already available for review, it does not scan third-
party hosts, brute-force anything, or act against a running system,
and it never prints an unredacted secret value even when demonstrating
an alternate payload.
