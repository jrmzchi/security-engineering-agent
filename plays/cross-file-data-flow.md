# Play: Cross-File Security Data Flow

Extends `plays/finding-validation.md`'s attack-path model
(`attacker capability -> entry point -> controlled data -> vulnerable
operation -> boundary crossed -> impact`) and
`plays/code-review.md`'s "Diff-aware review" principle ("do not limit
the review strictly to changed lines when the surrounding security
context is necessary to judge the change safely") with an explicit
procedure for tracing that path **across file and layer boundaries**.
Neither of those sections is replaced — this play is what "surrounding
context" and "boundary crossed" mean in practice when the source and
the sink are in different files.

## The named hops

A typical multi-file flow:

```text
Attacker-controlled input
        |
Controller / route
        |
DTO / model binding
        |
Service
        |
Helper
        |
Repository / filesystem / network / process
        |
Impact
```

Not every flow has all of these — a small app might go straight from
controller to repository. The point isn't to force every flow through
every named hop; it's to **not stop tracing just because the sink lives
in a different file from the source**. A candidate finding whose source
and sink are in different files is not, by itself, weaker evidence or
requiring different treatment — it needs the same rigor as a
single-file finding, applied across more files.

## Every hop needs its own evidence

Same discipline as `plays/project-security-baseline.md`'s facts and
`plays/attack-surface-mapping.md`'s nodes/edges: each hop in the chain
needs a file/symbol/observation, not a plausible-sounding assumption
about what the intervening code "probably" does. If a helper three
layers down from the entry point actually validates or parameterizes
the value, the finding is REJECTED or downgraded regardless of how
attacker-controlled the original input looked at the entry point — see
`plays/finding-validation.md`'s "Inspect sanitization"/"Inspect
validation" steps, which apply at *every* hop, not just the first one
the reviewer happens to look at.

## Confidence: this reuses `finding-validation.md`'s scale, not a new one

Cross-file tracing does not introduce a fourth confidence level or a
different vocabulary. It refines how to apply
`plays/finding-validation.md`'s existing HIGH/MEDIUM/LOW to a chain that
spans multiple hops — the illustrations below are examples of what
commonly drives each level for a *multi-hop* chain specifically, not an
exhaustive redefinition; `plays/finding-validation.md`'s own definitions
(HIGH/MEDIUM/LOW, and the option to fall back to `NEEDS_VERIFICATION`)
remain authoritative for any case not neatly covered by these examples
(a third-party binary dependency with no available source, say):

```text
HIGH     every hop has direct evidence — source, each intermediate
         transformation/call, and the sink are all traced to specific
         file/line observations, with no gap in the chain

MEDIUM   most hops are evidenced, but one link is inferred rather than
         directly observed (e.g. a helper's behavior is inferred from
         its name and a partial read, not a full trace of its body) —
         e.g. `plays/finding-validation.md`'s own "some environment/
         runtime detail is missing" case, when that detail is a
         specific hop in the chain rather than a deployment fact

LOW      dynamic dispatch, reflection, other framework indirection, or
         any other reason a hop's actual behavior can't currently be
         demonstrated with the evidence at hand — e.g. one hop between
         two files can't be reliably confirmed
```

This is `plays/finding-validation.md`'s confidence model
(`plays/finding-validation.md`'s "Confidence model" section) applied
hop-by-hop — not a competing scale. A `LOW`-confidence multi-file chain
follows the same rule as a `LOW`-confidence single-file one: it must
not be silently promoted to a confirmed severe finding. Use
`NEEDS_VERIFICATION` and say which hop couldn't be confirmed, exactly
as `plays/finding-validation.md`'s own worked example does for a
single-file case.

## Consult the Attack Surface Map, when one exists, to move faster — not to skip verification

If `.security/attack-surface.json` (see
`plays/attack-surface-mapping.md`) already has nodes and edges covering
part of this flow, use it to locate the relevant files and known
controls faster than starting from nothing. It never substitutes for
verifying *this specific candidate's* chain — a map edge marked
`confidence: "HIGH"` when the map was built does not mean today's
candidate finding automatically inherits that confidence; re-verify the
specific hop against current source, the same way
`plays/finding-validation.md` already requires independent verification
regardless of what the original reviewer claimed.

## Worked example

```text
Candidate: path traversal via report export

Controller:  ReportsController.Export()
  -> reportName comes from a query string value (attacker-controlled) —
     NOT a route parameter: see the note below on why that distinction
     is itself part of the evidence, not a stylistic detail
DTO:         none — reportName passed straight through
Service:     ReportService.GetReportPath(reportName)
  -> file: Services/ReportService.cs, symbol: GetReportPath
  -> observation: `return Path.Combine(_reportsRoot, reportName);` —
     no canonicalization, no containment check after combining
Repository:  none — ReportService reads the file directly
Sink:        File.ReadAllBytes(path) in ReportService.GetReportPath

Confidence: HIGH — every hop evidenced (query-string binding, service
method body, direct file read), no inferred link.
Result: CONFIRMED — reportName = "../../appsettings.json" resolves
outside _reportsRoot with no check preventing it.
```

**Why query string, not a route parameter, and why that's not
incidental:** ASP.NET Core's routing normalizes and single-segment-
constrains route parameters — a route like `/reports/{reportName}`
would not actually let `../` survive to reach `Path.Combine`, making
that version of this exact scenario NOT exploitable despite looking
identical at the controller signature. See
`tests/fixtures/path_traversal_unsafe.cs`'s own header comment, which
documents exactly this: an earlier version of that fixture used a route
parameter, the claimed attack path didn't actually work, and it was
corrected to a query-string value for that reason. This is
`plays/finding-validation.md`'s "Inspect framework protections" step
(see that play, and `plays/code-review.md`'s "Framework-provided
protections") applied to a specific input-binding mechanism — checking
*how* attacker-controlled data enters, not just *that* it does, is
itself one of the hops that needs evidence.

Compare to a hop that couldn't be resolved:

```text
Candidate: same shape, different codebase

Controller:  ReportsController.Export(reportName from query string)
Service:     ReportService.GetReportPath(reportName)
  -> calls IPathSanitizer.Sanitize(reportName) — an interface;
     the concrete implementation is registered via a DI container
     configuration this reviewer could not resolve statically
     (multiple implementations exist, selection is configuration-driven)

Confidence: LOW — the hop that would determine whether this is
exploitable (what Sanitize() actually does) could not be confirmed.
Result: NEEDS_VERIFICATION — state that resolving which
IPathSanitizer implementation is active, and reading its
Sanitize() method, would resolve this.
```

## Output

Findings produced this way still use `templates/finding.md` and still
go through `plays/finding-validation.md`'s independent validation for
any HIGH/CRITICAL result — this play changes how the chain is
constructed and how confidence is assigned to a multi-file chain
specifically, not the finding format or the validation requirement.

Referenced from `skills/security-review/SKILL.md`'s workflow (step 5)
and from `AGENTS.md`'s routing summary (step 6): when a candidate's
source and sink are in different files, this play's explicit multi-hop
procedure is what `security-review` points to, rather than stopping at
the file boundary.
