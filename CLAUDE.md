# CLAUDE.md (project)

This is the project-level guide for Claude Code working in this repository.
It supplements, and does not replace, any user-level `~/.claude/CLAUDE.md`
instructions you are operating under.

This repository is a portable security engineering kit — see `AGENTS.md`
for the full map of `skills/` / `plays/` / `references/` / `agents/`. That
file is agent-agnostic and is the primary entry point; read it first.

## Claude-specific notes

Optional Claude-native subagent definitions live under
`integrations/claude/agents/`: six mirror the portable agents in
`agents/` (security-team-lead, security-architect, security-reviewer,
security-validator, dependency-auditor, secrets-reviewer), and the rest
(security-change-detection, security-gate, and the five
project-security-intelligence capabilities — project-security-baseline,
attack-surface-map, security-impact-analysis, attack-chain-analysis,
adversarial-validation) point directly at their `skills/`+`plays/` pair
instead, since they are classifiers/analysis passes rather than
coordinating roles. See `integrations/claude/README.md` for the full
list and why `plays/cross-file-data-flow.md` and
`plays/review-budget.md` have no wrapper of their own. They are
accelerators only — none of
the security procedures in this repo depend on Claude subagents,
skills, plugins, or hooks. A sequential, single-agent fallback must
always work by reading the plain Markdown in `skills/` and `plays/`
directly.

Do not invoke experimental Claude-only features (agent teams, plugins,
hooks) as a requirement for performing a security review — they may be used
where available, but core correctness cannot depend on them.

## Proactive workflow

An ordinary development request ("add an endpoint", "fix this bug") is
not exempt from security consideration just because it wasn't phrased
as a review request — see `AGENTS.md`'s "Before implementing a
meaningful software change" for the routing summary and
`plays/secure-development-workflow.md` for the full procedure. This is
proportional (a NONE/LOW-sensitivity change gets none of it, per
`skills/security-change-detection`) — it is not a mandate to run a full
audit on every change.

## Practical entry points

```text
Review this repository using STANDARD security review.
Perform a DEEP security assessment and generate a security report.
Review the current Git diff for security regressions.
Threat-model the proposed file upload API before implementing it.
```

See `README.md` for the full command/usage reference.
