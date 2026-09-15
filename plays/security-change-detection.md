# Play: Security Change Detection

Authoritative procedure for `skills/security-change-detection`.

## Sensitivity levels

Four levels. These measure how sensitive the *change* is, not how
severe a *vulnerability* is — see that skill's note on not confusing
the two.

### NONE

```text
documentation, comments, spelling, text labels, non-security CSS,
purely visual layout, formatting, internal variable rename with no
behavior change
```

Action: **no security workflow.** Do not run a scanner, do not load a
play, do not produce a security summary for this change.

### LOW

```text
ordinary internal business logic, calculations, data formatting,
non-privileged UI behavior, refactoring with no security-boundary
change
```

Action: **lightweight diff check.** Read the diff for anything that
looks out of place; no full scanner run unless something suspicious
actually appears while reading it.

### MODERATE

```text
new API endpoint without obviously privileged behavior, database-query
changes, file reads/writes not directly controlled by users, new
dependency, configuration changes, HTTP client changes, background
jobs, user-controlled redirects, logging involving potentially
sensitive data
```

Action: **targeted security review** — load only the relevant play(s)
and reference(s) for what changed (see `skills/security-review/SKILL.md`'s
"Where to look next" table and its
`skills/security-review/references/quick-reference.md`), not the full
skill. **If a targeted review turns up a CONFIRMED
finding, the gate still applies** — see `skills/security-gate`'s "When
this runs": gating depends on whether a finding exists, not on this
sensitivity label. **Also check `skills/security-design`'s own
activation list independently of this level**: several MODERATE items
here (APIs, database-query changes, HTTP client changes, background
jobs, user-controlled redirects, file reads/writes) also appear on that
skill's trigger list, which is authoritative for "should design run
before this is implemented" — a MODERATE sensitivity label does not
override it. Run design when either list says to.

### HIGH

```text
authentication, authorization, admin functionality, credential/password
handling, session management, JWT, cookies, cryptography, file upload,
file download, user-controlled filesystem paths, command/process
execution, shell execution, dynamic code execution, CORS, security
middleware, privilege changes, secret storage, external
callbacks/webhooks, SSRF-sensitive network behavior, deserialization,
deployment security configuration, rendering attacker-influenced data
into HTML/DOM/a template (output encoding, XSS-adjacent)
```

Action: **security design required before implementation when the
*pre-code* classification (see "Classify from intent" below) comes out
HIGH** (see `skills/security-design`), **targeted security review
required after implementation**, **security gate required at
completion** whenever a finding exists (see `skills/security-gate`).

### When a change doesn't clearly match any list above

These four lists are examples, not an exhaustive taxonomy — treat them
as illustrative, not a closed set. When a change doesn't obviously fit one,
default to the **higher** of the plausible levels rather than the
lower one. A miss in the NONE/LOW direction means a security-relevant
change goes completely unreviewed; a miss in the HIGH direction costs
an unnecessary targeted review. Those failure modes are not symmetric
— see `plays/finding-validation.md`'s bias toward under-reporting over
false assurance, which applies to workflow selection here the same way
it applies to individual findings there.

## Detection signals

Signals influence which workflow runs. **They are not vulnerability
findings** — do not report a finding simply because one of these
patterns exists; that determination is `skills/security-review`'s job,
using the attack-path model in `plays/finding-validation.md`.

```text
ASP.NET / .NET:
  [Authorize] [AllowAnonymous] Controller MapGet MapPost MapPut
  MapPatch MapDelete UseAuthentication UseAuthorization
  AddAuthentication AddAuthorization AddCors UseCors IFormFile
  PhysicalFile FileStream Path.Combine Path.GetFullPath Process.Start
  HttpClient FromSqlRaw ExecuteSqlRaw Redirect Cookie JWT Claims Roles
  Policy DataProtection Antiforgery

Python:
  subprocess os.system eval exec pickle yaml requests httpx pathlib
  open Flask routes FastAPI routes Django views SQL execution
  filesystem operations

JavaScript / Node:
  child_process eval Function innerHTML outerHTML insertAdjacentHTML
  postMessage Express routes JWT cookies CORS filesystem path SQL
  NoSQL redirects

Configuration:
  web.config appsettings.json appsettings.*.json .env IIS configuration
  authentication configuration authorization configuration CORS
  configuration TLS configuration security headers package manifests
  lock files CI/CD security configuration
```

## Classify from intent, before code exists

Reason about what the requested behavior implies, not just the literal
words of the request.

```text
Request: "Add an endpoint for downloading machine reports by filename."

Reasoning:
  HTTP input + filesystem access + potential object authorization +
  potential path traversal = HIGH

Request: "Change the button color from blue to gray."

Reasoning: no security-relevant behavior = NONE
```

Security design (`skills/security-design`) should run before
implementation when this pre-code classification comes out HIGH — not
after, when the design questions are harder to answer cheaply.

## Re-classify from the actual diff, after code exists

Implementation can introduce security-relevant behavior the original
request never mentioned. Re-run this same classification against what
was actually built (see `plays/secure-development-workflow.md`'s
post-implementation step), using the signals above and the
diff-inspection guidance in `plays/code-review.md`'s "Diff-aware
review" section — including surrounding code the diff calls into, not
just changed lines.

## No security theater

For a NONE classification, do not produce a security summary, do not
mention that "no issues were found" (nothing was checked), and do not
pad the response with unnecessary security framing — see
`plays/secure-development-workflow.md`'s completion-summary guidance.
