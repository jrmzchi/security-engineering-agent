# V3 Attack Chain Test Cases

Validates `plays/attack-chain-analysis.md`. See
`tests/validation/README.md` for how to run a validation pass. Unlike
most tables in this directory, both a positive and a negative case are
required — see `plays/attack-chain-analysis.md`'s "When a chain is
real" and this document's own "Why the negative case matters" below.

## Positive case: predictable ID + missing object authorization

**Component findings** (from `tests/fixtures/cross_file_object_authz_unsafe/`) —
both recorded as findings with their own entry, per
`plays/attack-chain-analysis.md`'s Required fields ("every step must
be an actual finding with its own record, not a non-vulnerable fact
folded into the chain"):

```text
[INFORMATIONAL] Report IDs are sequential, auto-incrementing integers
    (ReportRepository.cs) — recorded as its own CONFIRMED
    INFORMATIONAL finding, not omitted as a mere fact. Being
    INFORMATIONAL rather than its own vulnerability class is what
    plays/authorization.md's "severity amplifier, not the
    vulnerability itself" means — it does not mean this observation
    is excluded from having a finding record
[HIGH] Missing object-level authorization — ReportsController.cs's
    [Authorize] confirms authentication only; no file in the chain
    checks report ownership (CWE-639)
```

**Preconditions**: the missing-authorization finding is what makes
*any* `reportId` value readable by any authenticated caller; the
predictable-ID finding is what makes trying *every* `reportId` value
practical without needing to discover or guess unpredictable
identifiers first. Neither alone demonstrates mass exposure: the
authorization finding alone still requires knowing a valid ID; the
predictable-ID observation alone is not exploitable without the
missing check.

**Ordered steps**: (1) observe that `reportId` increments sequentially
by creating two reports and comparing their IDs; (2) exploit the
missing authorization check to request an arbitrary `reportId` as any
authenticated user; (3) iterate step 2 across the full ID range to
enumerate and read every report in the system, not just one.

**Boundary transitions**: the authorization finding alone already
crosses "authenticated user -> another user's data" on its own — this
chain does not add a *new* trust boundary crossing on top of that one;
what it adds is scale (see "Combined impact" below). Not every real
chain needs an additional boundary crossing beyond what its most
severe component already crosses — see
`plays/attack-surface-mapping.md`'s `TRUST_BOUNDARY` node type for
what would count as one if this target repository has a map.

**Combined impact**: bulk exfiltration of every user's reports via
automated enumeration, not the single-record read the missing-
authorization finding demonstrates in isolation.

**Confidence**: HIGH — both component findings are independently
CONFIRMED with direct evidence (no ownership check in
`ReportService.cs`; sequential IDs directly observed in
`ReportRepository.cs`), and the precondition linking them (the missing
check applies to every ID, and IDs are cheap to enumerate) is directly
observed, not inferred.

**Chain severity**: CRITICAL, escalated from the missing-authorization
finding's own HIGH — per `plays/attack-chain-analysis.md`'s "Chain
severity" factors, blast radius is what changes: a single confirmed
IDOR is HIGH (one user's data), but demonstrating trivial, scalable
enumeration of *every* record changes this from an isolated incident
to a systemic one. This is the same "combined severity exceeds any
component's own severity" shape as that play's own flagship worked
example, applied to a HIGH+LOW pair reaching CRITICAL instead of a
MEDIUM+MEDIUM pair reaching CRITICAL — the arithmetic isn't
mechanical, the reasoning about actual attacker capability is what
matters.

**Adversarial Validation**: this chain is itself the multi-finding-
chain trigger from `plays/adversarial-validation.md`'s trigger list —
applied to the precondition linking steps 2 and 3 (does a way exist to
reach large-scale exposure some other way that skips the missing-
authorization step, e.g. a bulk-export endpoint that bypasses
per-record checks differently?). No such alternate route exists in
this fixture — `CONTROL_HOLDS` per
`plays/adversarial-validation.md`'s chain-carrier table (this reuses
the finding-side name for a different object, per that play's
disclosure — not the finding-side meaning; here it means "no way was
found to reach the later step while skipping the earlier one," not
"a defense was found to hold").

Expected review outcome: the reviewer produces both component findings
individually **and** a chain record substantially matching the above —
a pass that produces only the two component findings, without
recognizing the chain, has not validated this capability.

## Negative case: coexisting but unrelated findings

**Component findings** (existing, unrelated fixtures):

```text
[HIGH] XSS via unescaped DOM write from location.search
    (tests/fixtures/xss_unsafe.js)
[HIGH] CORS misconfiguration — wildcard origin with credentials
    (tests/fixtures/cors_wildcard_credentials_unsafe.js)
```

Both findings could plausibly appear in the same review of the same
application (different files, both HIGH, both client-side-adjacent).
**There is no chain here.** Exploiting the XSS does not require the
CORS misconfiguration, and exploiting the CORS misconfiguration does
not require the XSS — neither finding's exploitation establishes any
fact the other depends on for reachability. Per
`plays/attack-chain-analysis.md`'s "When a chain is real" core
requirement (exploiting the first finding must actually *enable
reaching* the second, not merely coexist with it), these must be
reported as two independent findings, not combined into a chain.

Expected review outcome: the reviewer produces both component findings
and explicitly does **not** produce a chain record for them. A pass
that manufactures a chain here (e.g. "an attacker could combine XSS
with the CORS misconfiguration for a more severe attack") has
committed exactly the speculative-chain-generation error
`plays/attack-chain-analysis.md`'s guardrail exists to prevent — this
failure mode is symmetric with, and as serious as, missing the
positive case above.

## Why the negative case matters

A validation pass that only exercises the positive case cannot
distinguish "the reviewer correctly recognizes chains" from "the
reviewer chains any two HIGH findings it sees in the same review." Run
both cases in the same pass — see `plays/attack-chain-analysis.md`'s
own note that a chain is not automatically more severe than its worst
component, and this kit's general "prefer more reliable findings over
more findings" bias (`AGENTS.md`'s "Non-negotiable rules").
