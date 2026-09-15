# Play: API Security

Authoritative procedure for API-layer review, referencing OWASP API
Security Top 10 concepts, plus SSRF, insecure deserialization, XXE, and
mass assignment (server-side risks that most commonly manifest through
an API surface).

## Scope

```text
Authentication
Object authorization
Function authorization
Rate limits
Resource consumption
Mass assignment
Sensitive fields
Pagination / filtering
External APIs / webhooks
Error handling
Versioning
SSRF
Insecure deserialization
XXE
Request smuggling indicators
```

## Authentication vs. authorization

**The existence of authentication does NOT prove object authorization
exists.** Pay special attention to endpoint shapes like:

```text
GET /api/users/{id}
DELETE /api/files/{id}
GET /api/orders/{orderId}
```

For each: confirm the handler checks that the *authenticated caller* is
allowed to access *this specific* `{id}` — not merely that some valid
token was presented. This is BOLA/IDOR (see `plays/authorization.md` for
the general authorization play).

## Rate limits and resource consumption

Expensive operations (search with unbounded result sets, bulk export,
recursive/nested queries in GraphQL, file processing) without a limit on
frequency, page size, or query depth/complexity are a resource-exhaustion
risk. Check for pagination defaults and maximums, not just their
existence.

## Mass assignment (CWE-915)

If a request body is bound directly onto a persistence/domain model
(auto-binding frameworks, `[FromBody] User model` patterns, ActiveRecord
mass-assign), check whether privileged fields (`isAdmin`, `role`,
`balance`, `verified`) can be set by a request that should not be able to
set them. Safe pattern: an explicit DTO/allowlist of bindable fields per
endpoint.

## Sensitive fields in responses

Check that serialization does not leak more than the caller should see
(password hashes, internal IDs used elsewhere as secrets, other users'
PII in a list endpoint, stack traces in error responses).

## External APIs / webhooks / SSRF (CWE-918)

Any code path where the server fetches a URL and that URL (or its host)
is influenced by attacker-controlled input — a webhook target, an "import
from URL" feature, an image-proxy/link-preview feature — is a candidate
for Server-Side Request Forgery.

Check for:

```text
Is the target host validated against an allowlist?
Is the resolved IP checked against internal/link-local/loopback ranges
    (not just the hostname, to defend against DNS rebinding)?
Are redirects followed without re-validating each hop?
Are non-HTTP(S) schemes (file://, gopher://, etc.) rejected?
```

Framework/library HTTP clients with certificate validation disabled
(`ServerCertificateCustomValidationCallback` returning `true`,
`verify=False` in `requests`, `rejectUnauthorized: false`) compound SSRF
risk and are also a separate configuration finding.

## Insecure deserialization (CWE-502)

Sinks: `pickle.loads` on untrusted data, `yaml.load` (vs. `safe_load`),
.NET `BinaryFormatter`/`NetDataContractSerializer` on untrusted input,
Java native serialization. If the deserialized bytes are attacker
reachable (a request body, a stored blob a lower-privileged actor could
write), mark this a **CRITICAL candidate** and prioritize it for
validation ahead of other candidates in the same batch — deserializers of
this class carry unusually high potential impact (remote code execution),
which justifies queuing it first. This is a prioritization signal, not an
exemption from validation: per `plays/finding-validation.md`, it must
still go through independent validation and have its attack path
confirmed (attacker control of the input, reachability, and that the
target actually deserializes it) before being reported as CONFIRMED
CRITICAL. If validation cannot confirm reachability or attacker control,
downgrade to NEEDS_VERIFICATION like any other candidate.

## XXE (CWE-611)

Any XML parser processing attacker-supplied XML: check whether external
entity resolution and DTD processing are disabled. Modern defaults in
most frameworks disable this, but a parser explicitly configured to
resolve external entities (or an older library/version whose default is
unsafe) is vulnerable.

## Request smuggling indicators

Look for ambiguous request framing that a proxy/gateway pair could
interpret differently from the origin server: mismatched or duplicate
`Content-Length`/`Transfer-Encoding` handling, especially in hand-rolled
HTTP parsing or older library versions. This is more often an
infrastructure/deployment concern than an application-code one — flag it
for review against the actual proxy/gateway configuration rather than
trying to prove it purely from application source.

## Versioning

Deprecated API versions still reachable and lacking security fixes
applied to the current version are a real (often overlooked) exposure —
check whether old versions are actually decommissioned, not just
undocumented.
