# Attack Chain Template

Used with `plays/attack-chain-analysis.md`. One record per chain that
passes that play's "When a chain is real" test — including a
`NEEDS_VERIFICATION` chain (see that play's "Confidence" section; a
chain still gets a record even when its confidence is too low to
present as confirmed). Added as an additional section after the normal
findings list — see that play's "Deduplication" section for why
component findings are referenced here, not restated.

```markdown
## Attack Chain AC-NNN: <short descriptive title>

### Component findings (referenced, not restated)

- [SEVERITY] <finding title> — file: path/to/file.ext
- [SEVERITY] <finding title> — file: path/to/file.ext

### Preconditions

For each consecutive pair of steps, the specific fact the earlier step
establishes that the later step's *reachability* actually depends on
(not merely something the later step benefits from). Not "these seem
related" — the concrete condition (e.g. "step 1 is what puts
attacker-controlled content on disk at all; step 2's execution
behavior is what turns that stored file into running code, and step 2
has nothing to execute without step 1").

### Ordered steps

1. <first finding> — what exploiting it establishes
2. <second finding> — how it builds on step 1
...

### Boundary transitions

Which trust boundaries the combined path crosses that no single step
crosses alone (see `plays/attack-surface-mapping.md`'s `TRUST_BOUNDARY`
node type, when a map exists for this target repository).

### Combined impact

What the full chain achieves that no individual step's own Impact
section states.

### Confidence

HIGH | MEDIUM | LOW | NEEDS_VERIFICATION — see
`plays/attack-chain-analysis.md`'s "Confidence" section (this reuses
`plays/finding-validation.md`'s scale, bounded by the lower of each
component finding's own confidence and how directly evidenced the
linking preconditions are).

### Chain severity

CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL, with the reasoning —
**not** simply the highest severity among the component findings; see
`plays/attack-chain-analysis.md`'s "Chain severity" section for the
factors to weigh against the combined path.

### Adversarial Validation

A multi-finding chain is on `plays/adversarial-validation.md`'s
trigger list by default (once that trigger applies) — applied to the
preconditions/controls *between* steps, not to the chain's
already-established combined impact. Once considered, record:

Adversarial Validation: CONTROL_HOLDS | BYPASS_FOUND |
    CONTROL_INCONCLUSIVE
    (see plays/adversarial-validation.md's "Structured result
    metadata" for this chain-specific definition of each value — not
    the finding-side one; an evidence tag this play's own "When a
    chain is real" test and Confidence section weigh, never a
    replacement for either)
Techniques tried: which precondition(s)/step(s) were challenged and
    what was found
```

### Worked example

```markdown
## Attack Chain AC-001: Upload-to-RCE via an execution-enabled directory

### Component findings (referenced, not restated)

- [MEDIUM] Unrestricted file upload (no type/content validation) — file: Controllers/UploadController.cs
- [MEDIUM] Uploaded files served from an execution-enabled directory — file: appsettings.json / web server config

### Preconditions

Step 1 is what puts attacker-controlled content on disk at all; step
2's execution behavior is what turns that stored file into running
code. Neither step alone demonstrates arbitrary code execution: step 1
without step 2 only shows an arbitrary file can be stored somewhere
inert; step 2 without step 1 is a configuration exposure with no
attacker-supplied content to point at.

### Ordered steps

1. Unrestricted file upload — establishes that an attacker can store a
   file of their choosing, with an extension/content of their choosing,
   at a location under the application's control.
2. Uploaded files served from an execution-enabled directory — the
   directory step 1 writes into is configured to execute, not just
   serve, files placed there.

### Boundary transitions

External attacker input -> server-side code execution. Neither step
crosses this boundary alone: step 1 alone only crosses
external-input -> stored-file; step 2 alone has no attacker input to
act on at all without step 1 having supplied it first.

### Combined impact

Remote code execution — an attacker-chosen file, executed by the
server with the server process's own privileges.

### Confidence

HIGH — both component findings are independently CONFIRMED with direct
evidence (no validation on the upload endpoint; the serving directory's
execution behavior confirmed in the web-server configuration), and the
precondition linking them (the upload target directory is the same
directory configured to execute) is directly observed, not inferred.

### Chain severity

CRITICAL, with reasoning: remote code execution is CRITICAL under
`plays/finding-validation.md`'s severity model (system privileges,
potentially full compromise) regardless of what severity either
component finding reached alone — here, neither component reached
CRITICAL, or even HIGH, by itself.

### Adversarial Validation

CONTROL_HOLDS — challenged whether the upload directory's execution
behavior could be reached through any route other than the upload
endpoint (technique 7, alternate entry points); no sibling upload path
or static-file route bypassing the same directory was found.
```
