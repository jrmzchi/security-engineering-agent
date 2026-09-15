# Play: Security Design

Authoritative procedure for `skills/security-design`. Produces security
requirements **before** implementation.

## Procedure

For the feature under design, answer each question below. Skip a question
only when it is genuinely not applicable, and say so — do not silently
omit it.

### 1. What are the assets?

What is worth protecting here: user data, credentials, payment
information, internal system access, availability, integrity of records?
Name them concretely — "user PII (email, address)" not "data".

### 2. Who are the actors?

Every party that interacts with the feature: anonymous users,
authenticated users, specific roles, admins, background services, other
internal systems, external third parties (webhooks, partner APIs).

### 3. What are the trust boundaries?

Where does the trust level change? Client -> server is always one.
Service -> service inside a private network may or may not be, depending
on the network model. Third-party webhook -> your handler is always a
boundary — that payload is attacker-reachable even if the third party is
"trusted".

### 4. What input is attacker-controlled?

Anything originating on the other side of a trust boundary: request
bodies, query params, headers (including `Referer`, `User-Agent`,
`X-Forwarded-*`), cookies, file contents/names, webhook payloads, and
anything read back out of storage that a lower-privileged actor could
have written earlier (stored injection).

### 5. What operations are privileged?

Anything that reads/writes another user's data, changes permissions,
spends money, sends communications, executes on the server (commands,
deserialization), or touches the filesystem outside a sandboxed
directory.

### 6. What security controls are required?

For each privileged operation and each attacker-controlled input, name
the control: authentication requirement, authorization check (object AND
function level), input validation, output encoding, rate limiting,
parameterization, allowlisting.

### 7. What must never be trusted?

Be explicit about the inverse of (4): client-side validation alone,
hidden form fields, a role claim in a JWT without server-side
verification against current state, an ID in a URL implying ownership.

### 8. What should be logged?

Authentication events (success and failure), authorization denials,
privileged actions (who did what to what), and enough context to
investigate an incident later — without logging secrets or full
sensitive payloads.

### 9. What failure behavior is safe?

When a check fails, an external call times out, or an exception is
thrown, does the system fail closed (deny/reject) or fail open
(allow/continue)? For anything security-relevant, it must fail closed.

## Scale to the feature

A public, read-only, non-sensitive listing endpoint might answer all nine
questions in a few lines. An admin credential-reset flow needs a full,
careful pass. Do not pad a low-risk feature's design doc to look thorough — an
oversized document for a trivial feature adds review burden without
adding safety.

## Output

Fill in `templates/security-design.md`. This becomes the requirements
that `security-review` later checks the implementation against.
