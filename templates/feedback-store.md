# Feedback Store Template

Used with `plays/finding-validation.md`'s "Feedback Learning" sections.
Written to `.security/feedback.json` in the **target repository being
reviewed** — not to this kit's own repository, and never merged into
that same repository's `.security/baseline.json` or
`.security/attack-surface.json`. Full field-level schema, the reuse
eligibility algorithm, and the acceptance test cases are
`work/v4-planning/context-manifest-schema.md` sections 4/5/5.1/5.2's —
this file shows the same shape in its persisted JSON form, produced by
`tools/feedback_store/schema.py`, never hand-assembled to a different
shape.

`[V4 release]` A sibling `.security/feedback.json.quarantine` file means a
record that a fresh validation contradicted could not be durably marked
STALE: while it exists the store loads as degraded and nothing is reused.
It lists the record ids; only `tools/feedback_store/store.py`'s
`recover_quarantine()` removes it, after checking each listed record is
STALE or absent. Do not delete it by hand without that check.

```json
{
  "schemaVersion": 2,
  "updated": "2026-01-01T00:00:00Z",
  "gitCommit": "a1b2c3d-or-null",
  "writerVersion": "1.0.0",
  "rejectionRecords": {
    "case1-report-ownership": {
      "recordId": "case1-report-ownership",
      "recordType": "feedback_rejection",
      "candidateShape": {
        "category": "BOLA/IDOR",
        "suspicionPattern": "object reference taken from a caller-supplied ID with no visible ownership check at the sink itself",
        "safetyPattern": "ReportService.GetReport enforces report.OwnerUserId == currentUserId before returning the result",
        "reachabilityPath": [
          {"path": "src/Controllers/ReportsController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportsController.GetReport(int)", "lineRange": {"start": 40, "end": 44}},
          {"path": "src/Services/ReportService.cs", "qualifiedSymbol": "MyApp.Services.ReportService.GetReport(int, int)", "lineRange": {"start": 18, "end": 27}},
          {"path": "src/Repositories/ReportRepository.cs", "qualifiedSymbol": "MyApp.Repositories.ReportRepository.FindById(int)"}
        ]
      },
      "rejectionReason": "cross-file ownership check present in ReportService.GetReport",
      "evidence": {
        "path": "src/Repositories/ReportRepository.cs",
        "observation": "FindById itself has no ownership check; enforced by its caller"
      },
      "scope": "applies to ReportsController.GetReport -> ReportService.GetReport -> ReportRepository.FindById specifically",
      "dependencies": [
        "src/Controllers/ReportsController.cs",
        "src/Services/ReportService.cs",
        "src/Repositories/ReportRepository.cs"
      ],
      "lastValidation": {
        "timestamp": "2026-01-01T00:00:00Z",
        "commit": "a1b2c3d-or-null",
        "validatedBy": "code_reviewer_subagent"
      },
      "invalidationConditions": [],
      "reuseCount": 0
    }
  },
  "missRecords": {
    "miss-2026-01-15-routing": {
      "recordId": "miss-2026-01-15-routing",
      "recordType": "feedback_miss",
      "layer": "routing",
      "observedMiss": "missing object-ownership check in a newly-added report-export endpoint",
      "expectedFinding": "CONFIRMED HIGH BOLA/IDOR",
      "priorLayersPassed": [],
      "evidence": {
        "path": "src/Controllers/ReportsController.cs",
        "observation": "item 0's own recorded domain set for this diff was {'code-review'} only -- 'authorization' was never selected"
      },
      "remediation": "review plays/security-change-detection.md's MODERATE/HIGH lists for whether this endpoint shape should route to authorization by default",
      "scope": "endpoints reading a caller-supplied object ID with no [Authorize]-change signal",
      "createdAt": "2026-01-15T00:00:00Z",
      "humanConfirmedBy": "jane.reviewer"
    }
  }
}
```

**`status`** (omitted above -- both records are current): a rejection
record only gains a `status` key, with value `"STALE"`, when Selective
Invalidation or a failed reuse-eligibility re-derivation determines it
can no longer be reused as-is — same convention as
`templates/project-security-baseline.md`'s baseline facts, not a new
one invented here. `reachabilityPath`/`dependencies` are always
repository-relative paths, normalized to forward slashes — never an
absolute path, never one containing a `..` segment. They are COMPARED
through one shared rule, `tools/feedback_store/paths.py`'s
`canonical()`, used identically by identity, eligibility and both
invalidation mechanisms: separators normalized, then Unicode NFD
decomposition, then `casefold()`, then NFC recomposition. So a record
whose stored path spells a file name in lower case and a diff that
reports the same file with an upper-case letter are the SAME file, and
so are the NFC and NFD spellings of an accented file name (macOS tools
commonly emit NFD). `casefold()` is full Unicode case folding, not
just upper/lower: `ß` and `ss` compare equal too. The stored spelling
keeps the caller's original case and Unicode form; only the comparison
key is transformed.

**Each `reachabilityPath` hop is `{path, qualifiedSymbol, lineRange?}`.**
`qualifiedSymbol` is REQUIRED and must carry whatever lexical/type/
signature identity the source language can reliably provide — enough
that two genuinely different callables can never produce the same
string. A bare method name (`"GetReport"`), or a name plus only an
arity/type suffix with no enclosing namespace/type (`"GetReport(int)"`),
is refused at construction time (`tools/feedback_store/schema.py`'s
`_looks_unqualified` check) — it cannot distinguish, for example, a
`ReportController.GetReport(int)` from an unrelated `ExportController.
GetReport(int)`, or two different Python classes that each declare a
same-named method. If a reliably unique `qualifiedSymbol` cannot
actually be built for a given hop, no reusable record may be created
for that trace at all — it must always re-derive through the full
independent Validator instead of ever being cached.

`[DISCLOSED, per a Round 3 independent review Minor]` this check is a
SYNTACTIC FLOOR, not a semantic guarantee: it can reject an obviously
bare name, but it cannot verify that a well-formed-looking
`qualifiedSymbol` actually IS unique for the language in question — a
caller that writes `MyApp.Controllers.ReportController.GetReport` for
BOTH of two real C# overloads (correctly qualified by namespace and
type, but omitting the parameter signature that would have told them
apart) passes this check while still colliding. Getting the actual
uniqueness right is the caller's own responsibility when building
`reachabilityPath` — the same way `paths.py` validates a path's SHAPE
but not whether it names the file the caller actually meant. The
worked example above always includes a full namespace AND (where the
language has overloads) a signature specifically to model the level of
precision this responsibility actually requires — a shorter form like
bare `ReportsController.GetReport` would still be ACCEPTED by this
check, but is not a safe pattern to copy for a language where
overloads or repeated class names across namespaces are possible.

`lineRange` (`{start, end}`, both positive ints) is OPTIONAL and is
evidence-location/diagnostic metadata ONLY — it is never read or
compared when deciding whether a candidate is the same occurrence as a
stored record (`tools/feedback_store/paths.py`'s `same_reachability_path`
never touches it). A pure line shift at an unchanged hop — e.g. a
comment inserted above `ReportService.GetReport`, moving it from lines
18-27 to 23-32 with nothing else different — must never by itself
change whether identity matches. It does NOT follow that a line-shifted
candidate is automatically reusable: identity matching is only the
precondition; every one of checks (a)-(d) in section 5.1 still runs
independently on it, exactly as it would on a byte-for-byte identical
candidate.

**Identity comparison** (`tools/feedback_store/identity.py`) is:
`candidateShape.category` + the ordered `reachabilityPath`, where each
hop compares BOTH the normalized `path` AND the exact `qualifiedSymbol`
string (never a substring, never just the trailing name after the last
qualifier, never with the parameter signature stripped). Any hop
missing `qualifiedSymbol`, any length/order/signature difference, or a
candidate trace below `HIGH` confidence fails the precondition
immediately — the candidate is a DIFFERENT occurrence and checks
(a)-(d) never even run against this record.

**Schema version and legacy records.** `schemaVersion` is currently
`2` — bumped from `1` specifically because the identity rules above are
a semantics change, not a cosmetic one. A store tagged `1` (or any
record within a store — even one currently tagged `2` — whose hops are
still the old bare-`symbol` shape, with no `qualifiedSymbol` key at
all) loads successfully but is treated as **audit-only**: it displays
for human review, but `identity.py`'s own per-record guard refuses to
match it against anything, regardless of how well everything else
appears to line up. Nothing in this package ever silently "upgrades" a
legacy record by guessing at a `qualifiedSymbol` for it — the only way
a legacy occurrence becomes reusable again is a genuine fresh
re-derivation through the full independent Validator, producing an
entirely new record. Writing the store back down (e.g. after adding an
unrelated fresh record) always stamps the top-level `schemaVersion`
with whatever this package's CURRENT version is — that is a true
statement about the file format the writer produces, not a claim that
every record inside has been re-validated — so a store can legitimately
be tagged `2` at the top level while still holding one or more
individual legacy-shaped records inside it. This mixed state is
expected and safe: each record is judged by its own shape, never by the
store's single top-level tag.

**`lastValidation.commit` is `non-empty string | null`.** `null` is the
documented value for a repository with no git history or no commit yet
(the same convention as the store's own top-level `gitCommit`); it
records provenance for a human and participates in no identity, reuse,
invalidation or status decision. An empty string or a non-string is
still malformed. `lastValidation.timestamp` must be a non-empty
string. (`commit` is not the only nullable value on a record: a hop's
optional `lineRange` may also be `null`, meaning "not recorded"; every
other field that participates in any decision is required and
non-null.)

**`rejectionRecords` and `missRecords` share one ID namespace** — a
missed vulnerability is never stored as though it were a rejected
candidate. Precisely what is enforced where: `append_rejection_record`
and `append_miss_record` REFUSE an id already present in either
collection (`DuplicateRecordIdError`); `load()` and `write()` validate
every record's own content but do NOT currently cross-check the two
collections for a shared id, so a hand-edited file carrying the same id
in both will load. Consumers must therefore treat the two collections
as separate by `recordType`, never by id alone.

An **unrecognized `schemaVersion`** (neither the current version nor
the recognized legacy version `1`), invalid JSON, or a single
non-legacy-shaped record that fails schema validation degrades the
WHOLE file to "no intelligence to reuse this run" — never a partial
read of whatever still parses. A legacy-shaped record does NOT trigger
this degradation by itself; it loads as audit-only instead (see above).
A **missing file** is simply "no intelligence recorded yet," not an
error.
