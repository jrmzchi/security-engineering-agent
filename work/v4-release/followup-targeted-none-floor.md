# Follow-up: the CSRF signal floor on the TARGETED/NONE path (2026-09-30)

**Status: implemented on the local branch `v4-release-hardening`, not published** — see `hardening-none-gate.md`.
The text below is the record as written before that work, unchanged. It covers two Minors from the revision-9 fix-only
re-review (report §18). The published product (kit export `812115b5…`) does not contain the fix.

**Scope:** only the TARGETED-mode path where item 0 classifies a change NONE. QUICK/STANDARD/DEEP are unaffected, and
so is a TARGETED change classified LOW or above. The validation corpus exercises neither item.

## 1. Making the floor actually run before the NONE stop

**What holds today.**
- In code, `orchestrator.produce_manifest(scope_texts=...)` applies `signal_floor.required_domains()` at step 0a,
  before the NONE shortcut (1a). A NONE change with both signals gets web-security.
- In the workflow, `plays/secure-development-workflow.md` ("NONE -> stop here") and
  `plays/security-change-detection.md` (the NONE action) carry one exception "when the scope shows both an ambient
  browser credential and a state-changing endpoint".

**The gap.** Whether the exception fires is left to the agent noticing the pair. At NONE the workflow stops before
SKILL step 1, which is the only place `produce_manifest()` — and so the floor — runs. An agent that classifies NONE
and misses the pair never runs the deterministic check. That is the same failure shape RV-18 showed at item 0.

**Proposed change (to be authorized):**
1. At the NONE decision, the NONE row and the NONE action should require one mechanical step before stopping: run
   `tools/context_manifest/signal_floor.required_domains(scope_texts)` on the changed files' texts. If it returns a
   domain, take the exception; if it returns nothing, stop as before. This is cheap, with no model call and no
   network, and it keeps NONE's proportionality for every other change.
2. The agent's own reading of "the scope shows both signals" stays as an additional trigger, never a replacement.
3. **Tests:** a workflow-level test asserting the step text in both documents; and a test that the helper's result
   alone decides the exception (both halves → web-security, either half missing → nothing).
4. **Open to decide:** whether the scope is the changed files' whole texts, as today — which can fire for a
   comment-only change to a file that already holds the pair — or the diff. Whole files is the conservative
   direction and matches the floor's current definition.

## 2. What "no scanner / no summary" means on the exception path

**What holds today.**
- The NONE row reads "No design, no review, no scanner, no summary", followed by the exception: "build the manifest as
  TARGETED and review web-security only (read its play), at the MINIMAL budget. No design step."
- The manifest built for that exception selects `semgrep` for web-security. The validator requires each domain's
  scanners to be accounted for.
- `plays/security-change-detection.md` "No security theater" says, for NONE, "do not produce a security summary, do
  not mention that 'no issues were found' (nothing was checked)".

**The gap.** The exception does not say:
- whether the manifest's selected scanner runs;
- whether a result is reported;
- what happens to a finding.
Taken literally, "No security theater" would forbid reporting even a CONFIRMED CSRF from the exception review, and
its reason ("nothing was checked") is untrue on that path.

**Proposed behaviour (to be authorized):**

| Question | Proposed rule on the exception path |
|---|---|
| Design step | none (unchanged) |
| Domains | the floor's domain only (web-security); no other play |
| Budget | MINIMAL (unchanged) |
| Scanners | as the manifest selects for that one domain (semgrep). Where a selected scanner is unavailable, record it in `coverageGaps`, as for any review. No other scanner runs |
| No finding | a one-line note that the exception ran and found nothing for web-security; no full security summary, and no "no issues found" claim for anything else |
| A finding | reported and routed like any finding: `plays/finding-validation.md`, then `skills/security-gate` |
| "No security theater" | add "except the signal-pair exception, which reports what it checked" |

**Tests to add with it:**
- the text of the NONE row, the NONE action and "No security theater" asserts the same rule in all three places;
- a manifest-level test that the exception's manifest carries only web-security and the scanners that domain maps
  to.

## Not in scope here

- Widening the floor's patterns (the known misses are listed in `signal_floor.py`).
- Any other signal pair.
- A stability measurement.
