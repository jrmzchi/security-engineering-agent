# V3 Slim Batch 6 — Results: remaining agent wrapper chain inventory

Scope (per user instruction, 2026-09-22): trace every remaining Claude
agent wrapper's actual invocation chain (following the
`v3-agent-wiring-test-cases.md` secrets-reviewer template from Batch 5),
identify any rule genuinely unreachable when the role is invoked
directly, fix only confirmed gaps with minimal changes, and add/update a
validation case for each fix. **Result: no further gap found — this is
an inventory-only submission, no kit file changed.**

13 Claude wrappers total. `security-reviewer` (Batch 4) and
`secrets-reviewer` (Batch 5, fixed) already checked — this batch covers
the remaining 11.

## Group A: wrappers with a separate portable `agents/*.md` role

| Role | Chain | Necessary rule(s) for this role | Reachable? |
|---|---|---|---|
| `security-team-lead` | wrapper -> `agents/security-team-lead.md` -> (dispatches to other agents) + `plays/finding-validation.md` (dedup/chaining note) + `plays/attack-chain-analysis.md` + `templates/security-report.md` | `AGENTS.md`'s non-negotiable rules (this role assembles the final report from others' findings, so it inherits their correctness rather than re-deriving it) | **Yes — explicitly, not implicitly.** Step 1 of `agents/security-team-lead.md`'s own workflow is "Read the repository structure, manifest/project files, and any existing README/`AGENTS.md`/CLAUDE.md" — this role is instructed to read `AGENTS.md` as its own first action, regardless of whether the invoking context already did. No gap. |
| `security-architect` | wrapper -> `agents/security-architect.md` -> `skills/security-design`/`plays/security-design.md` + `skills/threat-model`/`plays/threat-model.md` | N/A for `AGENTS.md`'s 3 review-time rules (scanner-output/dangerous-pattern/attack-path) — this role establishes requirements *before* code exists; it does not evaluate scanner hits, dangerous-function presence, or attack paths in existing code. Checked `plays/security-design.md` and `plays/threat-model.md` for their own critical rules instead — both are self-contained procedures the wrapper points to directly, nothing found unreachable. | **N/A / no gap** — different rule set than the review-time roles, and what this role does need is reachable |
| `security-validator` | wrapper -> `agents/security-validator.md` -> `plays/finding-validation.md` directly | The "dangerous pattern ≠ vulnerability" principle, in the form this role actually needs it | **Yes, via domain translation, not verbatim restatement.** `plays/finding-validation.md`'s Confidence model (`LOW = "a suspicious pattern exists... but exploitability cannot currently be demonstrated"`, line 110-112) plus its explicit "**Do not assign CRITICAL simply because the vulnerability belongs to a traditionally dangerous CWE category**" (line 147-148) together *are* this principle, translated into the validator's own vocabulary — a better fit for this role than importing `AGENTS.md`'s generic wording would be. No gap. |
| `dependency-auditor` | wrapper -> `agents/dependency-auditor.md` -> `plays/dependency-security.md` directly | The "scanner/CVE-match output is candidate evidence" principle | **Yes, via domain translation.** `plays/dependency-security.md`'s "Reachability is a judgment call, not a guess" section (a CVE match must be checked for direct/transitive/runtime/reachability before being prioritized; if reachability can't be determined, confidence drops to MEDIUM rather than asserting either way) is this principle applied to dependencies specifically — matches the pattern Batch 4 already flagged as arguably the *better* approach (`skills/dependency-audit/SKILL.md`'s own translation, same idea one layer up). No gap. |

## Group B: wrappers with no separate portable agent (point directly to skill+play)

All 7 follow the same well-formed pattern: a short paragraph naming the
skill+play as authoritative, explicitly disclosing "there is no separate
`agents/X.md`" (confirmed correct — none exists for these), and then
**naming the one most safety-critical nuance for that specific role
inline, with a citation to where the full rule lives** — rather than
either restating it fully or omitting it. This is the same shape as the
fix applied to `secrets-reviewer` in Batch 5, already present here from
the start.

| Role | Chain | Safety-critical nuance named inline | Reachable? |
|---|---|---|---|
| `security-gate` | wrapper -> `skills/security-gate/SKILL.md` + `plays/security-gate.md` | "why scanner severity alone can't BLOCK, and how a chain record gates independently of its component findings" | **Yes** — both files confirmed (Batch 3/earlier sessions) to actually contain this rule; the wrapper correctly delegates rather than silently omitting |
| `adversarial-validation` | wrapper -> `skills/adversarial-validation/SKILL.md` + `plays/adversarial-validation.md` | "Independence" section, "never prints an unredacted secret value" | **Yes** — stated inline, not just cited |
| `attack-chain-analysis` | wrapper -> `skills/attack-chain-analysis/SKILL.md` + `plays/attack-chain-analysis.md` | "do not construct a chain just because two findings coexist" ("When a chain is real" test) | **Yes** — stated inline |
| `attack-surface-map` | wrapper -> `skills/attack-surface-map/SKILL.md` + `plays/attack-surface-mapping.md` | "do not guess an endpoint into existence... mark it `NEEDS_VERIFICATION` instead" | **Yes** — stated inline |
| `project-security-baseline` | wrapper -> `skills/project-security-baseline/SKILL.md` + `plays/project-security-baseline.md` | "Never write a secret value into a reported fact" | **Yes** — stated inline |
| `security-impact-analysis` | wrapper -> `skills/security-impact-analysis/SKILL.md` + `plays/security-impact-analysis.md` | Scope-bounding only (this role doesn't make a judgment call with an obvious failure mode the way the others do) | **Yes / N/A** — no specific safety-critical nuance identified as missing |
| `security-change-detection` | wrapper -> `skills/security-change-detection/SKILL.md` + `plays/security-change-detection.md` | "default to the higher plausible level when genuinely unsure" | **Yes** — stated inline |

## Conclusion

**No gap found in any of the 11 remaining chains.** The one real gap in
this whole inventory (`secrets-reviewer`) was already found and fixed in
Batch 5. The other 6 "Group A" roles either explicitly read `AGENTS.md`
themselves (`security-team-lead`), don't need the specific rules in
question (`security-architect`), or reach the substance of the rule
through a domain-specific translation already present in their play
(`security-validator`, `dependency-auditor`) — consistent with Batch 4's
observation that translation-over-verbatim-restatement is often the
better pattern in this kit. All 7 "Group B" roles already follow the
exact shape the `secrets-reviewer` fix was brought into line with: name
the one critical nuance inline, cite the full rule's location, don't
restate it in full.

No file changed. No new validation case needed (no fix was made) — the
existing `tests/validation/v3-agent-wiring-test-cases.md` stays at one
case; a header note below points future batches to add a case only when
an actual fix is made, not for confirmed-clean chains, to avoid the file
growing into a duplicate of this inventory.

## Not done here

- No reduction/Slim work attempted, per explicit instruction.
- Not `V3 SLIM GOLDEN BASELINE`.
