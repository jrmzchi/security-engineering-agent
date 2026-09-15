# Play: Authorization

Authoritative procedure for authorization findings — IDOR/BOLA, broken
access control, privilege escalation.

## Scope

```text
IDOR (Insecure Direct Object Reference)
BOLA (Broken Object Level Authorization)
Broken access control (general)
Horizontal privilege escalation
Vertical privilege escalation
Missing object authorization
Missing function authorization
```

## IDOR / BOLA (CWE-639)

For every endpoint that takes an identifier and returns or acts on a
specific object (`{id}` in a path, a hidden form field, a body field),
trace:

```text
Is the caller's identity established (authentication)?
Is it checked that THIS caller owns/can access THIS object, not just
    that they are logged in?
Is the check done server-side, on every access path to the object
    (not only the "main" UI flow — also exports, bulk endpoints,
    websocket/GraphQL resolvers, admin-adjacent tools)?
```

Object identifiers being sequential/guessable is a severity amplifier,
not the vulnerability itself — the vulnerability is the missing
authorization check. A sequential ID with a correct ownership check is
not IDOR; a UUID without an ownership check still is.

## Missing function authorization

Distinct from object authorization: does the caller have permission to
invoke this *operation* at all, regardless of which object it targets?
Common gap: admin-only actions checked only by hiding the button/menu
item in the UI, with the underlying endpoint reachable by any
authenticated user who guesses or observes the URL/request shape.

## Horizontal privilege escalation

A user acting on another user's data/account at the *same* privilege
level (user A modifying user B's profile/order/settings). Root cause is
almost always a missing or incorrect object-ownership check — see IDOR
above.

## Vertical privilege escalation

A lower-privileged actor reaching functionality meant for a higher
privilege level. Check for:

```text
Role/permission stored on the client and trusted without server
    re-verification (a JWT claim read but not validated against current
    account state, a role passed as a hidden form field)
An API accepting a role/permission field in the request body that then
    gets applied without a server-side authorization check on who may
    set it
A privilege check present on one entry point (e.g. the main UI action)
    but absent on an equivalent one (a bulk/import endpoint, an older
    API version, an internal/admin-adjacent route)
```

## Broken access control (general)

Anything not neatly IDOR or missing-function-check but still resulting
in access beyond what the actor should have: directory listing exposing
files belonging to other tenants in a multi-tenant system, a shared
cache/queue that does not partition by tenant, a default-allow
authorization policy where a new endpoint is reachable unless explicitly
locked down (prefer default-deny).

## Multi-tenant considerations

For multi-tenant systems, every authorization check above must also
verify the object belongs to the caller's tenant, not just the caller
directly — a same-tenant, wrong-user IDOR and a cross-tenant IDOR are
both this class of finding, but cross-tenant is typically higher
severity (broader blast radius).
