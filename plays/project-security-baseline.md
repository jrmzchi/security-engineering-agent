# Play: Project Security Baseline

Authoritative procedure for `skills/project-security-baseline`. Builds
and maintains a persistent, evidence-backed description of a **target
repository's** security-relevant architecture — the repository being
reviewed with this kit, not this kit's own repository.

## Other uses of the word "baseline" in this kit

None of these are this play, and this play does not replace or
duplicate any of them:

- `plays/security-design.md` produces a **per-feature**, throwaway
  requirements document, written before one feature is implemented,
  filed into `templates/security-design.md`. This play produces a
  **persistent, repo-wide** fact base — what the whole project's
  architecture actually is — that outlives any single feature and gets
  consulted (and updated) across many reviews.
  `templates/security-design.md`'s closing line calls the finished
  requirements doc "the baseline `security-review` should check the
  implementation against" — a different, narrower sense of the word.
- `plays/finding-validation.md`'s "Baseline origin" section is a
  **per-finding** tag (`INTRODUCED`/`MODIFIED`/`PRE_EXISTING`/
  `UNKNOWN`) answering "did the current diff introduce this specific
  vulnerability, or did it already exist?" That's about one finding's
  relationship to one diff. This play is about the project's
  architecture as a whole, independent of any single finding or diff.
- Gitleaks itself has a "baseline"/allowlist file (a list of findings
  to suppress as already-known/accepted) — a scanner-tool feature, not
  this project's own vocabulary, but easy to conflate with `.security/`
  since both are persistent files that live in the reviewed repo. Not
  related to this play at all.
- `plays/scanner-selection.md` uses "baseline" once, loosely, to mean
  "this kit's own V1 release" — plain English, not a defined term.

A feature's design requirements are not an architecture fact, a
finding's diff-relative origin tag is not an architecture fact, and a
scanner's suppression list is not an architecture fact either — don't
reuse any of that vocabulary here, and don't reuse this play's
vocabulary there.

## What it answers

```text
Languages? Frameworks? Runtime? Hosting? Deployment OS?
Authentication? Authorization? Database? ORM? Frontend?
External services? File storage? Secret sources? Background jobs?
Admin surfaces? Public surfaces? Security middleware? Sensitive data?
```

## The fact schema

Every material baseline claim has five parts:

```text
Value       the fact itself
Confidence  HIGH / MEDIUM / LOW / UNKNOWN
Source      USER_CONFIRMED / CODE_EVIDENCE / CONFIG_EVIDENCE / INFERRED / NONE
Evidence    file path + what was observed there
Freshness   which evidence file(s) this fact depends on
```

Source is not a side note — see "Fact sources" below for its values and
the one rule that actually depends on it (a `USER_CONFIRMED` fact must
never be silently overwritten by contradicting code evidence).

**This confidence scale is not `plays/finding-validation.md`'s.**
That one grades how certain a candidate *vulnerability* is
(HIGH/MEDIUM/LOW, no UNKNOWN — a finding you can't assess is
`NEEDS_VERIFICATION`, a different vocabulary entirely). This one grades
how certain an *architecture fact* is, and explicitly allows `UNKNOWN`
as a first-class result (see "Unknowns are valid" below) rather than
forcing a guess. Do not borrow one scale for the other's purpose.

### Don't infer beyond the evidence

```text
Bad:
  ASP.NET Core detected -> Hosting = IIS

Good:
  ASP.NET Core detected
  web.config contains an aspNetCore module entry
  Windows deployment scripts present
  -> Hosting = IIS/Windows, Confidence = HIGH
```

A framework's default or common pairing is not evidence of what a
*specific* project actually does. If the deployment target isn't
evidenced, it's `UNKNOWN` — see below.

### Unknowns are valid

`UNKNOWN` is a legitimate value, not a gap to paper over. Do not infer
a deployment fact (hosting, environment, external dependencies) from
framework defaults alone just to avoid writing `UNKNOWN`. When a
review's outcome genuinely depends on the missing fact, mark the
affected finding/decision `NEEDS_VERIFICATION` (per
`plays/finding-validation.md`) or ask the user — but only when the gap
actually changes the decision, not for every unknown.

### Fact sources

Tag where a fact came from, and never silently let one kind override
another:

```text
USER_CONFIRMED   the user told you this directly
CODE_EVIDENCE     observed directly in source
CONFIG_EVIDENCE   observed in a config/manifest/deployment file
INFERRED          derived from other evidence, not directly observed
NONE              no evidence at all (paired with confidence UNKNOWN —
                  see "Unknowns are valid" above; do not label a no-
                  evidence fact INFERRED, which claims a derivation that
                  didn't happen)
```

If current code evidence contradicts a `USER_CONFIRMED` fact, flag the
contradiction explicitly rather than overwriting it — the user's
statement might be describing an intended future state, or the code
might be wrong. Let them resolve it.

## Discovery: progressive disclosure, not a blind full-repo read

Look at what's actually likely to carry the answer, not the whole
repository indiscriminately:

```text
project manifests               (package.json, *.csproj, requirements.txt, ...)
framework configuration         (Program.cs / Startup.cs, settings.py, ...)
routing                          (controllers, route files, urls.py, ...)
middleware
authentication configuration
authorization configuration
dependency manifests / lockfiles
deployment files                 (web.config, Dockerfile, *.yml pipelines, ...)
environment/config templates     (.env.example, appsettings*.json, ...)
database access                  (ORM config, connection setup)
filesystem usage
external HTTP usage
background workers
admin surfaces
frontend entry points
```

Read the manifest/config files first — they're small and usually name
the framework, database, and major dependencies directly — before
opening arbitrary source files to confirm a specific claim.

## Storage

```text
.security/baseline.json     machine-readable facts (this play's output)
.security/README.md         human-readable summary of the same
```

These live in the **target repository being reviewed**, not in this
kit's own repository. Whether the target project commits `.security/`
or ignores it is that project's call, not this kit's — recommend:
stable architecture facts are usually worth committing (they're
project documentation as much as they are review input); anything
transient (a single run's scratch state) should not be. Never write a
secret value into either file — see "Secret sources" below.

### Unrecognized schema version

`baseline.json`'s `schemaVersion` may be newer than this play knows
about (a different kit version wrote it) or simply malformed. Don't
partially parse a version you don't recognize — treat the whole file as
untrustworthy, report that the baseline needs rebuilding, and fall back
to building the relevant subset fresh (per "When to build or refresh
one" below), the same way a missing baseline is handled.

### Secret sources: name the source, not the value

```text
Good: "Secret source: environment variable DB_PASSWORD"
Bad:  "DB_PASSWORD=actual-secret-value"
```

Same rule as `plays/secrets-security.md` — a baseline fact about
*where* a secret comes from is structural information; the secret
itself never belongs in a stored artifact.

## Freshness and invalidation

A fact is only as good as the evidence it's tied to. When a fact's
evidence file changes, that fact — and only that fact — needs
re-evaluation:

```text
Program.cs changed
        |
authentication baseline may be stale
        |
re-evaluate authentication facts only
```

Do not rebuild the entire baseline after every change; invalidate the
affected facts and re-derive just those. The Git-driven mechanics of
*detecting* which facts a given change affects — reading each fact's
`freshnessOf` against the changed-files set — are in
`plays/security-impact-analysis.md`'s "Incremental invalidation"
section; this play owns the fact schema and the invalidation
*principle*, that one owns the mechanism. `AGENTS.md`'s "Before
implementing a meaningful software change" step 4 now routes an
in-scope change through `skills/security-impact-analysis` for exactly
this; `skills/security-review/SKILL.md` step 2's "and is fresh" check
is what actually consults the result.

If current source evidence contradicts a stored fact, current evidence
wins — set that fact's `status` field (see
`templates/project-security-baseline.md`'s schema) to `STALE` rather
than trusting it, and re-evaluate. Never force what the code actually
does to fit a previously-recorded assumption.

## Keep the baseline out of every prompt

Do not inject the full baseline into ordinary tasks. Keep a compact
summary (stack, auth, storage, files — a few lines) for routing
decisions, and load the detailed evidence for a specific fact only when
that fact is actually relevant to the current change. See
`templates/project-security-baseline.md`'s "Summary" section for the
compact form.

## When to build or refresh one

```text
No baseline exists, trivial task
        -> do not force a full build

No baseline exists, security-sensitive work needs project context
        -> build the relevant subset only

Explicit request ("rebuild security baseline")
        -> full rebuild
```

A CSS-color-change request should never trigger a baseline build. An
authenticated-file-download feature request, with no baseline yet,
justifies building the authentication/authorization/file-storage subset
— not the whole schema.

## Output

Use `templates/project-security-baseline.md` for both the compact
summary and the full per-fact record. `skills/security-review/SKILL.md`
step 2 now consults `.security/baseline.json` when it exists and is
fresh, instead of rediscovering architecture from scratch. Facts
refining — never replacing — `skills/security-change-detection`'s
NONE/LOW/MODERATE/HIGH classification is a separate, still-unwired
question: `AGENTS.md`'s step 1 names this play as one of the inputs
that refines that classification, but no concrete rule yet exists for
how a specific baseline fact should shift it — see
`skills/project-security-baseline/SKILL.md`'s "Relationship to
security-change-detection".
