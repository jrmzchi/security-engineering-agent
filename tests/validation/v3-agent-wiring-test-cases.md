# V3 Agent Wiring Test Cases

Validates that a Claude subagent's actual invocation chain (its
`integrations/claude/agents/*.md` wrapper -> the portable `agents/*.md`
role it says to follow -> whatever play(s) that role points to) reaches
every rule that chain is required to carry, without assuming `AGENTS.md`
was read first in that context. See `tests/validation/README.md` for how
to run a validation pass — the same "trace it, don't just read the
answer off this table" principle applies here: actually open each file
in the chain and confirm the text is there, rather than trusting a
citation.

This file exists because a real gap of this shape was found and fixed
during V3 Slim (see case 1 below) — add a case here whenever a similar
chain-reachability question comes up for a different subagent.

## Case 1: secrets-reviewer reaches "scanner output is candidate evidence"

Traces whether a direct invocation of the `secrets-reviewer` Claude
subagent — with no assumption that `AGENTS.md` was read first in that
session — still reaches the rule that a Gitleaks (or manual-fallback)
hit is candidate evidence, not a confirmed secret, before it can be
reported as a finding.

| Step | File actually read in this chain | Before this fix | After this fix |
|---|---|---|---|
| 1 | `integrations/claude/agents/secrets-reviewer.md` | Says "Follow `agents/secrets-reviewer.md` exactly" — no rule text of its own (by design, per its own "does not restate or modify the procedure") | Unchanged |
| 2 | `agents/secrets-reviewer.md` | "## Non-negotiable rule" section only covered redaction — no mention of candidate-evidence status, no citation to `AGENTS.md` | "## Non-negotiable rules" (now plural) leads with: "A Gitleaks (or manual-fallback) hit is candidate evidence, never a confirmed secret on its own — see `AGENTS.md`'s own 'Non-negotiable rules' for this principle generally, and apply `plays/secrets-security.md`'s 'Before reporting a hit, determine' checks before treating any hit as a finding." |
| 3 | `plays/secrets-security.md` | "Before reporting a hit, determine" checklist already existed (real vs. placeholder, active vs. inactive, tracked vs. untracked, exposure history) — the *practice* was always present, just never named as an instance of the general "candidate evidence" principle, and never traced back to `AGENTS.md` | Unchanged — this fix points to the existing checklist rather than duplicating it |

**Result: before the fix, a subagent following this chain exactly as
written would apply the "Before reporting a hit, determine" checklist
correctly (the practice was never actually broken) but had no explicit
statement that this is because a hit is candidate evidence, and no link
back to `AGENTS.md` as the authoritative source for that principle — so
a reader of just this chain could not confirm *why* the checklist exists
or that it traces to the kit's top-level non-negotiable rule. After the
fix, step 2 explicitly states the principle and cites both `AGENTS.md`
(authoritative source) and the play's existing checklist (the
application) — the chain is self-contained without relying on `AGENTS.md`
having been read in this specific session.**

## What this does not test

This does not re-test whether the `security-reviewer` chain has the same
kind of gap — that chain was traced during V3 Slim batch 4 and confirmed
to already reach `skills/security-review/SKILL.md`'s full restatement of
all relevant rules; no fix was needed there. Nor does it test every
possible subagent chain in this kit — only the one gap actually found so
far.
