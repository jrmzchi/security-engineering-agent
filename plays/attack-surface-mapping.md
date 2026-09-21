# Play: Attack Surface Mapping

Authoritative procedure for `skills/attack-surface-map`. Builds a
persistent, evidence-backed graph of a **target repository's** security-
relevant entry points, boundaries, privileged operations, and sensitive
sinks — not this kit's own repository.

## Not the same thing as an attack-path chain

`plays/finding-validation.md`'s "Attack path model" is a **linear
chain reconstructed fresh for one candidate finding** (Attacker -> Input
source -> Data transformation -> Validation -> Security controls ->
Sensitive sink -> Security impact) — produced, used to judge that one
finding, and discarded. It is not persisted and does not accumulate
across findings.

This play's output is a **persistent, reusable graph**: many nodes,
many edges, built once and consulted repeatedly. The two work together
but do not replace each other:

```text
Attack surface map    -> "what entry points, controls, and sinks does
                          this project have, and how do they connect?"
                          (built ahead of time, reused across reviews)

Attack-path chain      -> "for THIS candidate finding, does a complete,
                          evidenced path from attacker input to impact
                          actually exist?"
                          (built fresh per finding, still required)
```

Consulting the map can speed up building a chain (it may already know
where the relevant entry point and controls are), but it never
substitutes for independently verifying that specific finding's path —
see `plays/finding-validation.md`'s confidence model, which still
governs whether a finding is CONFIRMED.

## Not the same thing as a threat model, either

`plays/threat-model.md` also names "entry points" and "trust
boundaries" (its Core Concepts table) — but it's a **lightweight,
narrative, per-project-or-per-feature exercise**, scaled down for small
work and skipped entirely for low-risk utilities, whose output is a
filled-in `templates/threat-model.md` document read by humans. This
play's output is a **structured, persistent, machine-readable graph**
with a fixed node/edge vocabulary, built to be queried by automated
steps — `plays/security-impact-analysis.md`'s reverse-dependency
lookups do this today — not primarily to be read as prose. A team can do a full threat-model
exercise and still have no attack surface map, or vice versa — running
one does not satisfy the other, though the same discovery work (asking
"where are the entry points/trust boundaries") obviously informs both,
and there is no reason not to reuse findings from one while building
the other.

## Node types

Use only the types below; don't invent new ones without updating this
table. Each has a stable-ID prefix (see "Stable IDs" below) — use
these prefixes consistently so IDs alone hint at type.

```text
Type                      ID prefix
------------------------- -----------
ENTRY_POINT               AS-ENTRY-
TRUST_BOUNDARY            TB-
AUTHENTICATION_CONTROL    AS-AUTHN-
AUTHORIZATION_CONTROL     AS-AUTHZ-
VALIDATION_CONTROL        AS-VALID-
SERVICE                   AS-SVC-
DATA_STORE                AS-DATA-
FILESYSTEM                AS-FS-
EXTERNAL_SERVICE          AS-EXT-
PROCESS_EXECUTION         AS-PROC-
QUEUE                     AS-QUEUE-
BACKGROUND_JOB            AS-JOB-
SECRET_SOURCE             AS-SECRET-
CLIENT_SIDE_SINK          AS-CLIENT-
ADMIN_SURFACE             (tag, not usually a primary type — see "Dual-typing" below)
SENSITIVE_SINK            (tag, not usually a primary type — see "Dual-typing" below)
```

```text
ENTRY_POINT               where an external actor's request enters the
                          system (a route, a message handler, a CLI arg)
TRUST_BOUNDARY            a point where the trust level changes
AUTHENTICATION_CONTROL     verifies who the caller is
AUTHORIZATION_CONTROL      verifies what the caller may do
VALIDATION_CONTROL         checks/sanitizes/encodes untrusted input
SERVICE                    an internal business-logic component
DATA_STORE                 a database or persistent store
FILESYSTEM                 local or mounted file storage
EXTERNAL_SERVICE           a third-party or other-internal-system dependency
PROCESS_EXECUTION          spawns an OS process or shell command
QUEUE                      a message queue/broker
BACKGROUND_JOB             a scheduled or async worker
SECRET_SOURCE               where a credential/key/token originates
CLIENT_SIDE_SINK             a browser-side DOM write, redirect, or
                          other client-executed sensitive operation
```

### Dual-typing: `tags`

`ADMIN_SURFACE` and `SENSITIVE_SINK` describe a node's exposure or
impact character, not what kind of thing it structurally is. A node
that's "an admin surface" is usually, more fundamentally, an
`ENTRY_POINT`; a node that's "a sensitive sink" is usually a
`DATA_STORE`, `FILESYSTEM`, or similar. Record the structural type as
`type` (with its ID prefix from the table above), and add
`tags: ["ADMIN_SURFACE"]` and/or `tags: ["SENSITIVE_SINK"]` when that
character also applies — see the worked examples below. Use
`type: "ADMIN_SURFACE"` or `type: "SENSITIVE_SINK"` directly only for
the rare node that genuinely fits no more specific structural type.

## Edge types

```text
CALLS             one component invokes another
READS             reads data from a node
WRITES            writes data to a node
AUTHENTICATES     an AUTHENTICATION_CONTROL verifies identity for the
                  flow reaching it — see "Control edge direction" below
AUTHORIZES        an AUTHORIZATION_CONTROL verifies permission for the
                  flow reaching it — see "Control edge direction" below
VALIDATES         a VALIDATION_CONTROL processes data crossing to it —
                  see "Control edge direction" below
REDIRECTS_TO      an HTTP redirect
FETCHES           an outbound HTTP/network call
EXECUTES          spawns a process or runs dynamic code
UPLOADS_TO        writes an externally-supplied file
DOWNLOADS_FROM    serves a file to an external actor
DESERIALIZES      deserializes external/untrusted data
PUBLISHES         sends a message to a queue/topic
CONSUMES          receives a message from a queue/topic
```

### Control edge direction

For `AUTHENTICATES`/`AUTHORIZES`/`VALIDATES`, `from` is the **control**
node performing the check and `to` is the node/flow it protects — read
it the same subject-verb-object way as `CALLS`/`READS`/`WRITES` ("the
authentication control authenticates the entry point," not "the entry
point authenticates the control"). This is the same convention as every
other edge type (the acting node is always `from`), not a special case.

## Fields

Every node has:

```text
id            stable identifier (see "Stable IDs")
type          one of the node types above
label         a short human-readable name
evidence      { path, symbol, observation }
confidence    HIGH / MEDIUM / LOW
tags          optional: "ADMIN_SURFACE" and/or "SENSITIVE_SINK" — see "Dual-typing"
status        optional: "NEEDS_VERIFICATION" or "STALE" — see "Evidence-backed mapping" below
freshnessOf   evidence file(s) this node depends on (same meaning as
              plays/project-security-baseline.md's field of the same
              name) — used by plays/security-impact-analysis.md to
              decide what needs re-evaluation after a change
```

Every edge has the same fields as a node except `label`/`tags`
(from/to already identify it): `from`, `to`, `type`, `evidence`,
`confidence`, `status`, `freshnessOf`.

## Evidence-backed mapping — do not hallucinate

Every node and edge needs a file/symbol observation, exactly like a
baseline fact (see `plays/project-security-baseline.md`'s fact schema —
same discipline, applied to graph elements instead of architecture
facts).

When routing is dynamically generated (reflection, a framework
convention that can't be statically resolved with confidence), do not
guess an endpoint into existence — give it `confidence: "LOW"` and
`status: "NEEDS_VERIFICATION"` instead (see the third worked example
below). An endpoint you cannot confidently resolve is either absent
from the map or marked `NEEDS_VERIFICATION` — never asserted as if
resolved.

(This reuses `plays/finding-validation.md`'s exact status name for a
different kind of object — a graph node/edge, not a finding. That's a
safe reuse, not the same collision `plays/security-gate.md` and
`plays/security-remediation.md` had to invent new names to avoid: those
two needed different names because a HIGH/CRITICAL *finding* could be
in one of *their* not-yet-resolved states at the same time it might
also be `NEEDS_VERIFICATION` in `finding-validation.md`'s sense — two
statuses on the same object, in play at once, would have been
ambiguous. A map node and a finding are never the same object, so no
such ambiguity exists here.)

`NEEDS_VERIFICATION` and `STALE` mean different things and are not
interchangeable: `NEEDS_VERIFICATION` is for a node/edge that was
**never confidently resolved in the first place** (the case above).
`STALE` (same meaning as `plays/project-security-baseline.md`'s fact
status of the same name) is for a node/edge that **was** confidently
resolved, but current source evidence now contradicts it — see
`plays/security-impact-analysis.md`'s incremental-invalidation
procedure, which is what actually sets this status after a change.

### Secrets: name the source, not the value

A `SECRET_SOURCE` node's `evidence.observation` must follow
`plays/secrets-security.md`'s rule — record *where* the secret comes
from (an environment variable name, a config key, a secret-manager
reference), never the value itself:

```text
Good: observation: "reads from environment variable DB_PASSWORD"
Bad:  observation: "_apiKey = \"sk-live-abc123...\""
```

This applies even though `plays/project-security-baseline.md`'s
equivalent rule was written for `.security/baseline.json` specifically
— `.security/attack-surface.json` is recommended for commit right
alongside it (see "Output" below), so the same never-store-a-live-value
discipline applies here too.

## Don't over-model

Only create nodes and edges that are actually useful for security
reasoning: no privileged operation, no trust-boundary crossing, **and**
no sensitive data means a function isn't a node. The map should be
legible, not exhaustive — a hundred-node graph of every function call
in the codebase defeats the purpose (nobody will read it, and it costs
context for no benefit).

## Stable IDs

Prefer a stable, semantic key over a bare sequence number where one
exists naturally (a route path, a symbol name), and use the type
prefixes from the node table above consistently. Don't renumber
existing IDs just because the map grew; that turns every update into a
huge diff for no reason (see `plays/project-security-baseline.md`'s
freshness principle — the same "only touch what actually changed"
discipline applies here). Within one map, an ID must be unique; if two
independently-built subgraphs are merged, resolve collisions by
re-checking evidence, not by silently picking one.

## Worked examples

The two examples below are deliberately identical, field-for-field, to
`templates/attack-surface-map.md`'s JSON — read that file for exactly
what the persisted form looks like.

### Example 1: authenticated file download

```text
                                         TB-001 (TRUST_BOUNDARY)
                                         "Internet -> authenticated app"
                                         (no edges of its own here - see note)

AS-AUTHN-001 (AUTHENTICATION_CONTROL)
  |  AUTHENTICATES
  v
AS-ENTRY-001 (ENTRY_POINT)              "GET /files/{id}/download"
  |  CALLS
  v
AS-SVC-001 (SERVICE)                    "FilesController.Download"
  ^  AUTHORIZES
  |
AS-AUTHZ-001 (AUTHORIZATION_CONTROL)    "Object-level file ownership check"
  |
AS-SVC-001
  |  CALLS
  v
AS-SVC-002 (SERVICE)                    "FileService.Resolve"
  |  READS
  v
AS-FS-001 (FILESYSTEM, tags: SENSITIVE_SINK)   "Uploaded-files store"
```

A `TRUST_BOUNDARY` node doesn't necessarily need edges of its own — it
can simply annotate that trust changes at a location already implied by
an `ENTRY_POINT`/`AUTHENTICATION_CONTROL` pair, as here. Give it actual
edges only when the boundary sits somewhere not already obvious from
those two node types (e.g. a lower-trust producer publishing onto a
queue a higher-trust worker consumes from).

### Example 2: admin action

```text
AS-AUTHZ-002 (AUTHORIZATION_CONTROL)    "Admin-role policy check"
  |  AUTHORIZES
  v
AS-ENTRY-002 (ENTRY_POINT, tags: ADMIN_SURFACE)   "POST /api/admin/users/{id}/disable"
  |  CALLS
  v
AS-SVC-003 (SERVICE)                    "AdminController.DisableUser"
  |  CALLS
  v
AS-SVC-004 (SERVICE)                    "UserService.Disable"
  |  WRITES
  v
AS-DATA-001 (DATA_STORE, tags: SENSITIVE_SINK)   "Application database"
```

### Example 3: unresolvable routing (`NEEDS_VERIFICATION`)

```text
AS-ENTRY-003 (ENTRY_POINT)
  label: "possible admin route (unresolved)"
  evidence: { path: "AdminModule.cs", symbol: "(none)",
              observation: "routes registered via a custom
              IRouteConvention that composes paths from controller
              names at startup - not statically resolvable by reading
              source alone" }
  confidence: LOW
  status: NEEDS_VERIFICATION
```

## Building and refreshing

Same proportionality rule as the baseline (see
`plays/project-security-baseline.md`'s "When to build or refresh one"):
don't build a map for a trivial change, build only the relevant subset
for an ordinary security-sensitive task, and reserve a full-repo map
for an explicit request or a DEEP review. The Git-driven mechanics of
*which* nodes/edges a given change actually affects — so an update
touches only the relevant subgraph instead of rebuilding the whole
map — are in `plays/security-impact-analysis.md`'s "Incremental
invalidation" section; this play owns the node/edge vocabulary and the
evidence discipline, that one owns the mechanism. `AGENTS.md`'s
"Before implementing a meaningful software change" step 4 now routes
an in-scope change through `skills/security-impact-analysis` for
exactly this; `skills/security-review/SKILL.md` step 3's "and is
fresh" check is what actually consults the result.

### Unrecognized schema version

Same handling as `plays/project-security-baseline.md`'s "Unrecognized
schema version": don't partially parse an `attack-surface.json` whose
`schemaVersion` this play doesn't recognize — treat it as absent and
rebuild the relevant subset.

## Output

Use `templates/attack-surface-map.md` for the `.security/
attack-surface.json` schema. Keep it in the target repository being
reviewed, alongside `.security/baseline.json` — not in this kit's own
repository. `plays/security-impact-analysis.md` consults this map for
reverse-dependency queries and incremental invalidation, and
`plays/attack-chain-analysis.md`'s "Boundary transitions" field
references this map's `TRUST_BOUNDARY` node type when one exists.
`AGENTS.md`'s routing (step 4 for impact analysis; step 7, and
`skills/security-review/SKILL.md`'s workflow, for chain analysis) now
invokes both consumers as part of an ordinary review.
