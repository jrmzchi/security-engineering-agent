# Claude Code Integration

Optional accelerators only. Nothing in `skills/` or `plays/` depends on
anything in this directory — a single Claude Code session reading the
plain Markdown directly (no subagents, no plugins, no hooks) gets the
full, correct workflow. What this directory adds is the ability to run
the specialist roles (`agents/*.md`) as separate, parallel Claude
subagents where that is available and worth the cost.

## What's here

```text
integrations/claude/agents/security-team-lead.md
integrations/claude/agents/security-architect.md
integrations/claude/agents/security-reviewer.md
integrations/claude/agents/security-validator.md
integrations/claude/agents/dependency-auditor.md
integrations/claude/agents/secrets-reviewer.md
integrations/claude/agents/security-change-detection.md
integrations/claude/agents/security-gate.md
```

Each is a thin Claude subagent definition (YAML frontmatter + a short
body) that points at the corresponding authoritative source and does
not duplicate any procedure — see `README.md`'s single-source-of-truth
principle. If a play changes, these files do not need to change. The
first six point at a portable role in `agents/`; the last two
(`security-change-detection`, `security-gate`) point directly at their
`skills/`+`plays/` pair instead — they are lightweight classifiers, not
coordinating roles, so there is no corresponding `agents/*.md` for them
to wrap.

## Installing them as project subagents

Copy (or symlink) the files under `integrations/claude/agents/` into
this project's `.claude/agents/` directory (create it if it does not
exist):

```bash
mkdir -p .claude/agents
cp integrations/claude/agents/*.md .claude/agents/
```

Claude Code will then offer them as invocable subagents. This is a
one-time setup step per clone/checkout — it is not automatic, since not
every user of this kit is running Claude Code, and this repository's own
portable core must not assume it.

## Independent review still matters here

`agents/security-validator.md`'s independence requirement (see that
file, and `plays/finding-validation.md`) is easiest to satisfy exactly
when subagents are available: dispatch validation to a fresh
`security-validator` subagent rather than having the same context that
found a candidate also confirm it. This is the main practical benefit of
installing these subagents, beyond raw parallelism.

## Sequential fallback must still work

Do not build a workflow that only functions when these subagents are
installed. If they are not present (a fresh clone, or a user working in
plain Claude Code without setting them up, or any other agent
entirely), the same review can and should proceed sequentially by
reading `skills/security-review/SKILL.md` and the plays it points to
directly. Test any change to this integration by confirming the
sequential path still produces the same result.

## Experimental Claude features

Do not make this kit's core correctness depend on experimental or
Claude-only features (agent teams, plugins, hooks). They may be used
where genuinely available and helpful, but the portable procedures in
`skills/`/`plays/`/`references/` must remain the source of truth and
must work without them.
