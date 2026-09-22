# V3 Slim Batch 4 — Results: AGENTS.md's Non-negotiable rules vs. SKILL.md restatements

Scope (per user instruction, 2026-09-22): only `AGENTS.md`'s
"Non-negotiable rules" section and every `SKILL.md` that restates any of
those rules. Follows up directly on Batch 3's candidate 2 (which only
checked `security-review`) by widening to every skill.

## Executive result

**No change made. Both restatements are structurally required, not just
stylistically convenient — confirmed by tracing actual invocation paths,
not by probabilistic judgment.** `skills/secrets-scan/SKILL.md`'s
`Scanner output is candidate evidence` and
`skills/security-review/SKILL.md`'s "Non-negotiable rules" section stay
as-is. Reported honestly; this is not `V3 SLIM GOLDEN BASELINE`.

## 1. Inventory: which skill restates which rule

`AGENTS.md`'s "Non-negotiable rules" (`AGENTS.md:105-121`) has 4 rules.
Searched every `skills/*/SKILL.md` (13 files) for a restatement of each:

| Rule (`AGENTS.md` line) | Restated in |
|---|---|
| Scanner output is candidate evidence, never confirmed on its own (`:108-109`) | `skills/secrets-scan/SKILL.md:30` (1-line minimal form: "Scanner output is candidate evidence. Determine:"), `skills/security-review/SKILL.md:88-90` (full form, bulleted) |
| A dangerous function/API's presence is not itself a vulnerability (`:111-113`) | `skills/security-review/SKILL.md:91-94` only (cites `plays/code-review.md`'s "Dangerous pattern ≠ vulnerability", confirmed present at `plays/code-review.md:75`) |
| Every HIGH/CRITICAL finding needs a concrete attack path or a confidence downgrade (`:115-118`) | `skills/security-review/SKILL.md:95-97` only (cites `plays/finding-validation.md`, confirmed present) |
| Prefer more reliable findings over more findings (`:120`) | **Not restated anywhere** — no candidate to check for this one |

`skills/dependency-audit/SKILL.md` was checked specifically because it
also consumes scanner output (OSV-Scanner/Trivy) — it does **not** restate
rule 1 verbatim; instead it has its own domain-specific translation ("Do
not blindly combine results" + direct/transitive/reachable
deduplication), arguably a better pattern than either of the two
restatements below, but out of this batch's scope to act on (not itself
a candidate for removal — it isn't restating anything).

## 2. Tracing both entry paths (the actual check, not assumed)

**Path A — `AGENTS.md` read first, then the skill.** Trivially fine for
both restatements: the reader has already seen the rule once. This path
is where the restatement is arguably redundant.

**Path B — the skill loaded directly, `AGENTS.md` never read.** This is
not hypothetical in this kit — traced two concrete, real invocation
chains:

```text
security-reviewer subagent:
  integrations/claude/agents/security-reviewer.md
    -> "Follow agents/security-reviewer.md exactly"
      -> agents/security-reviewer.md:24 "Full procedure:
         skills/security-review/SKILL.md"
        -> skills/security-review/SKILL.md IS read in this chain.
           Neither AGENTS.md nor any other file carrying these 3 rules
           is read anywhere in this chain otherwise.

secrets-reviewer subagent:
  integrations/claude/agents/secrets-reviewer.md
    -> "Follow agents/secrets-reviewer.md exactly"
      -> agents/secrets-reviewer.md: "Full procedure in
         plays/secrets-security.md, entry point at skills/secrets-scan"
        -> plays/secrets-security.md IS read in this chain.
           skills/secrets-scan/SKILL.md is named descriptively
           ("entry point at") but is NOT instructed to be read, and
           plays/secrets-security.md itself does NOT contain the
           "candidate evidence" framing (verified: 0 grep matches for
           it in that file). AGENTS.md is not read anywhere in this
           chain either.
```

**Finding beyond what this batch asked, surfaced because the trace
uncovered it:** the `secrets-reviewer` subagent path, as its wrapper
chain is currently written, does not reliably reach the "scanner output
is candidate evidence" framing *at all*, independent of anything in this
batch — `skills/secrets-scan/SKILL.md`'s one-liner is never actually
read in that specific chain, and `plays/secrets-security.md` doesn't
carry it either. This is a **pre-existing gap**, not something removing
the SKILL.md restatement would create, and it is out of this batch's
scope to fix (the batch is about whether to *remove* text, not add
wiring) — recorded under "Unresolved risks" below rather than silently
noted and dropped.

**What Path B means for the removal question this batch actually asks:**
a Claude Code `Skill` invocation, or any portable (non-Claude) agent
following `AGENTS.md`'s own documented convention ("Read the relevant
skill, which points to the relevant play...") *without* AGENTS.md having
been read in that specific context, loads `skills/security-review/SKILL.md`'s
or `skills/secrets-scan/SKILL.md`'s content directly. Nothing in this
kit's architecture guarantees `AGENTS.md` was read before a `SKILL.md` is
loaded by name — there is no enforcement mechanism, only the documented
convention that it usually is. For that entry path, the restatement is
the only copy of the rule the reader ever sees.

## 3. Would removal cause an entry point to lose a required rule?

**Yes, for Path B, for both restatements.** Concretely:

- Removing `skills/security-review/SKILL.md:86-97` would mean the
  `security-reviewer` subagent chain (which demonstrably reads this file
  and nothing else carrying these 3 rules) loses all three rules if
  invoked without `AGENTS.md` having been read first in that context.
- Removing `skills/secrets-scan/SKILL.md:30`'s one-liner would mean a
  direct `Skill` invocation of `secrets-scan` (not the broken subagent
  chain above, which already doesn't reach it) loses rule 1 entirely,
  since `plays/secrets-security.md` doesn't carry it as a fallback.

This directly fails the user's own stated bar for making the change
("兩種入口的必要行為都能保留") — Path B's necessary behavior would not
be preserved.

## 4. Potential context savings (measured, not achieved)

| Restatement | Lines | Realizable? |
|---|---|---|
| `skills/security-review/SKILL.md:86-97` (full "Non-negotiable rules" section) | 10 content lines (88–97, plus the `## ` header) | Not realized — Path B depends on it |
| `skills/secrets-scan/SKILL.md:30` (one-line lead-in) | ~1 line, and even that line doubles as the lead-in to the following "Determine:" checklist, so the true removable fraction is closer to half a line | Not realized — Path B depends on it |

Total unrealized "savings" if it were safe: ~10–11 lines. Not claimed,
since it is not safe.

## 5. Authoritative source per rule

All four rules' authoritative source is `AGENTS.md:105-121` — this was
already true before this batch and does not change. Neither restatement
currently cites `AGENTS.md` back as that source (`security-review/SKILL.md`'s
rules 2 and 3 cite their elaborating plays; rule 1 and `secrets-scan`'s
version cite nothing). This is a traceability gap, not a duplication
problem, and adding a citation would not reduce any content — out of
this batch's scope (which is about safe removal, not adding citations),
noted under "Unresolved risks" for a future batch to decide on.

## Regression check

No file changed; nothing to re-run. If a future batch decides to pursue
the citation-gap fix above (additive, not a reduction) instead, it would
not need new test cases — no case in `tests/validation/*.md` asserts
citation content for these rules.

## Unresolved risks / notes for future batches

- **The `secrets-reviewer` subagent wrapper chain has a real, pre-existing
  gap**: it never reaches the "scanner output is candidate evidence"
  framing in either `skills/secrets-scan/SKILL.md` or
  `plays/secrets-security.md`. This is independent of this batch's
  question and was not fixed here (out of scope: this batch checks
  removability, not wiring gaps) — flagged for a dedicated batch, the
  same way the `review-budget` wiring gap was handled as its own batch
  earlier in this session.
- Neither restatement cites `AGENTS.md` as its authoritative source
  (traceability gap, not a duplication problem) — a candidate for a
  small, additive, non-reducing fix in a future batch if wanted.
- `skills/dependency-audit/SKILL.md`'s domain-specific translation of
  rule 1, rather than a verbatim restatement, is arguably the better
  pattern of the three approaches now in this kit (`security-review`'s
  full restatement, `secrets-scan`'s minimal one-liner,
  `dependency-audit`'s domain-specific translation) — not acted on here
  since it isn't a removal candidate, but worth naming if a future batch
  looks at consistency across how skills handle this rule.
