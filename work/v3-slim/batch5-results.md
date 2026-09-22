# V3 Slim Batch 5 — Results: secrets-reviewer chain gap fix

Scope (per user instruction, 2026-09-22): verify and, if warranted, fix
the specific gap Batch 4 surfaced but did not act on — the
`secrets-reviewer` subagent chain not reaching the "scanner output is
candidate evidence" principle. Not a reduction batch; this one adds a
small amount of content to close a real gap. Not `V3 SLIM GOLDEN BASELINE`.

## 1. Confirming the rule isn't already fully expressed elsewhere in the chain

Read all three files in the chain in full before changing anything:

- `integrations/claude/agents/secrets-reviewer.md` — by design, carries no
  substantive rule text of its own ("does not restate or modify the
  procedure"); not a candidate location.
- `agents/secrets-reviewer.md` — before this fix, its "## Non-negotiable
  rule" section covered only redaction, nothing about candidate-evidence
  status.
- `plays/secrets-security.md` — its "Before reporting a hit, determine"
  section (real vs. placeholder, active vs. inactive, tracked vs.
  untracked, exposure history) is the **practical instantiation** of the
  candidate-evidence principle — a hit is never auto-reported, it must
  clear these checks first. But the *general principle itself*, and its
  citation back to `AGENTS.md`, was never stated anywhere in this chain.

**Conclusion: not fully expressed.** The practice was always correct
(nothing in this chain would cause an actual false-confirmation bug), but
a reader of only this chain had no explicit statement of *why* the
checklist exists or that it traces to `AGENTS.md`'s non-negotiable rules
— exactly the gap the user described.

## 2. Minimal fix chosen

Single-file edit, in the one place both the Claude wrapper and any other
agent framework already point to for "the authoritative role definition":
`agents/secrets-reviewer.md`. Renamed "## Non-negotiable rule" (singular)
to "## Non-negotiable rules" (plural, confirmed nothing else cites this
section name by its old heading text) and added one paragraph before the
existing redaction rule:

```diff
-## Non-negotiable rule
+## Non-negotiable rules
+
+A Gitleaks (or manual-fallback) hit is candidate evidence, never a
+confirmed secret on its own — see `AGENTS.md`'s own "Non-negotiable
+rules" for this principle generally, and apply
+`plays/secrets-security.md`'s "Before reporting a hit, determine" checks
+before treating any hit as a finding.

 Never print full secrets in any report, log, or output. Always redact
 (`sk-proj-abc...xyz`). This applies even when the secret itself is the
```

`AGENTS.md` stays the authoritative source (cited, not restated — the
new text states the principle in one sentence and points to `AGENTS.md`
for it "generally," rather than reproducing `AGENTS.md`'s own wording).
`plays/secrets-security.md`'s existing checklist is cited, not
duplicated — no change made to that file. No other skill's restatement
was touched, per the user's explicit instruction.

## 3. Chain before/after

| Step | Before | After |
|---|---|---|
| `integrations/claude/agents/secrets-reviewer.md` | unchanged | unchanged |
| `agents/secrets-reviewer.md` | no candidate-evidence statement, no `AGENTS.md` citation | states the principle, cites `AGENTS.md` and the play's checklist |
| `plays/secrets-security.md` | checklist present, principle unnamed | unchanged — checklist now explicitly named as the application of the principle stated one file up the chain |

Full case trace: `tests/validation/v3-agent-wiring-test-cases.md` (new
file), case 1.

## 4. Verification

- **Chain reachability**: re-read the full updated `agents/secrets-reviewer.md`
  after the edit — the chain (wrapper -> this file -> play) now states the
  principle and cites `AGENTS.md` as its source, without the wrapper or
  the play needing any change. Documented as a formal case in
  `tests/validation/v3-agent-wiring-test-cases.md` rather than only
  checked ad hoc, so a future change to this chain can be re-verified the
  same way.
- **No restatement duplicated**: the new text is one sentence naming the
  principle plus two citations — it does not reproduce `AGENTS.md`'s
  wording or `plays/secrets-security.md`'s checklist items.
- **Consistency scan**: ran `scripts/macos/consistency-check.sh` before
  and after — 21 hits both times, byte-identical content, no new hit
  introduced by this change.
- **No other skill touched**: `git diff --stat` for this batch shows only
  `agents/secrets-reviewer.md` (content) and
  `tests/validation/v3-agent-wiring-test-cases.md` (new) —
  `skills/security-review/SKILL.md`, `skills/secrets-scan/SKILL.md`, and
  every other restatement from Batch 4's inventory are untouched.

## Git

Committed to `v3-slim` (hash below, filled in after commit).

## Not done here

- `skills/secrets-scan/SKILL.md`'s own one-line restatement was **not**
  touched or removed — the user explicitly said not to remove other
  skills' restatements in this batch, and Batch 4 already established
  that restatement is needed for the direct-`Skill`-load entry path
  regardless of this chain fix.
- The `security-reviewer` chain was not re-examined here — Batch 4 already
  confirmed it has no equivalent gap.
- Still not `V3 SLIM GOLDEN BASELINE` — this batch closes a wiring gap,
  it is not a measured reduction pass.
