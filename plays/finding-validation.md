# Play: Finding Validation

Authoritative procedure for `skills/security-validate`, and the shared
confidence/severity models used across every other play.

## Purpose

The validator does not assume the reviewer (or a scanner) is correct. For
every HIGH/CRITICAL candidate, independently reconstruct the case for and
against it being real.

## Procedure, per candidate finding

```text
Reconstruct the attack path
    -> attacker capability -> entry point -> controlled data
       -> vulnerable operation -> boundary crossed -> impact
Confirm attacker control
    -> is the data at the sink actually traceable back to something an
       attacker supplies, or does it only look similar to attacker input?
Confirm code reachability
    -> is this code path actually reachable given routing, feature
       flags, authentication requirements already in front of it?
Confirm sink behavior
    -> does the sink actually do what the candidate assumes? (e.g. does
       this ORM method actually build raw SQL, or does it parameterize?)
Inspect sanitization
    -> is there an encoder/escaper/sanitizer between source and sink
       that the initial pass missed?
Inspect validation
    -> is there an allowlist/type check/schema validation that would
       reject the attack payload before it reaches the sink?
Inspect authorization
    -> even if the technical vulnerability is real, does an
       authorization check limit who can trigger it, changing the
       actual impact?
Inspect framework protections
    -> see plays/code-review.md's "Framework-provided protections"
Inspect environmental constraints
    -> is the vulnerable code path only reachable in a build/environment
       that never runs against real data (e.g. test-only, feature-flagged
       off in production)?
Determine realistic impact
    -> given all of the above, what can an attacker actually achieve?
```

## Result

Every candidate resolves to exactly one of:

```text
CANDIDATE             not yet validated — the state every finding starts
                      in when security-reviewer (or a scanner) produces
                      it, before this procedure runs
CONFIRMED             the attack path holds up under independent scrutiny
REJECTED              the attack path does not hold; state which link broke
NEEDS_VERIFICATION    plausible but a required fact could not be
                      established from available evidence (e.g. cannot
                      determine at review time whether a middleware runs
                      before this handler)
```

`CANDIDATE` is this procedure's input, not one of its outputs — every
candidate this procedure runs on must exit as one of the other three.
(Note the naming: `NEEDS_VERIFICATION` — with an underscore, matching
the ALL_CAPS convention used across every other machine-readable status
in this project. `plays/security-gate.md`'s `AWAITING_VALIDATION` and
`plays/security-remediation.md`'s `FIX_UNVERIFIED` are deliberately
different names, not typos — see those plays for why a candidate
awaiting its first validation pass, and a fix whose re-validation was
inconclusive, are kept distinct from this status rather than reusing
it.)

Always state the reason. Worked example:

```text
Candidate: SQL injection in UserRepository.cs
Reviewer evidence: user input reaches a database query.
Validator discovers: Entity Framework parameterizes the value through
    a LINQ expression; the code does not use FromSqlRaw/ExecuteSqlRaw.
Result: REJECTED
Reason: attacker-controlled input does not modify query structure.
```

## Confidence model

```text
HIGH      attack path clearly demonstrated end-to-end with concrete
          evidence at every link (file/line for source, transformation,
          sink; no missing step)

MEDIUM    likely exploitable, but some environment/runtime detail is
          missing that would need to be confirmed to call it HIGH (e.g.
          reachability depends on a deployment configuration not visible
          from source)

LOW       a suspicious pattern exists (e.g. a dangerous sink with
          attacker-influenced input somewhere upstream) but exploitability
          cannot currently be demonstrated with the evidence at hand
```

**LOW confidence findings must not normally be presented as confirmed
vulnerabilities.** Use `NEEDS_VERIFICATION` instead, and say what
evidence would resolve it.

## Severity model

```text
CRITICAL
HIGH
MEDIUM
LOW
INFORMATIONAL
```

Severity considers, together, not any single factor in isolation:

```text
Exploitability          how hard is this to actually trigger?
Required privileges      does the attacker need to already have an
                        account, a specific role, or network position?
User interaction         does a victim need to click/open/run something?
Data sensitivity         what kind of data or capability is exposed?
Blast radius             one user's data, all users' data, the whole
                        system?
System privileges        does successful exploitation grant further
                        system access (RCE, admin)?
Internet exposure        is the vulnerable surface reachable from the
                        public internet, or only from an internal
                        network / requires prior internal access?
Business impact          financial, legal/compliance, reputational
```

**Do not assign CRITICAL simply because the vulnerability belongs to a
traditionally dangerous CWE category.** A textbook SQL injection with no
real exploitation path (e.g. gated behind an internal admin-only tool
requiring existing high privilege, on an air-gapped internal network) may
reasonably be MEDIUM. A seemingly minor information-disclosure bug that
leaks a session token to any unauthenticated caller can be CRITICAL.

## Attack path requirement (HIGH/CRITICAL)

Every HIGH or CRITICAL finding must be able to state the full chain:

```text
Attacker capability
  |
Entry point
  |
Controlled data
  |
Vulnerable operation
  |
Security boundary crossed
  |
Impact
```

If any link cannot be shown with evidence, downgrade confidence or mark
`NEEDS_VERIFICATION` — do not report it as confirmed HIGH/CRITICAL on the
strength of the parts that *can* be shown.

`skills/security-review/SKILL.md` states this same chain with a
seven-node breakdown (`Attacker -> Input source -> Data transformation ->
Validation -> Security controls -> Sensitive sink -> Security impact`) for
use while tracing a candidate during initial review. The two are the same
model at different granularity, not competing versions — the SKILL.md
version splits "Vulnerable operation" into the transformation/validation/
controls/sink steps that matter most for a data-flow vulnerability. Use
whichever granularity fits the finding; do not treat a mismatch in node
count between the two documents as a discrepancy.

**Exception — exposure-type findings.** Some finding categories are not
data-flow vulnerabilities and do not have a "Controlled data" or
"Vulnerable operation" node to fill in: a confirmed leaked credential, a
known-CVE dependency reachable at runtime, or a production deployment
with debug/verbose-error mode enabled. For these, the exposure itself —
plus its reachability and blast radius — is the evidence; do not
downgrade a confirmed active credential leak, a reachable known-CVE
dependency, or a confirmed production misconfiguration to LOW confidence
or NEEDS_VERIFICATION merely because it has no "Vulnerable operation"
step to cite.
Apply the full attack-path chain to data-flow vulnerabilities (injection,
XSS, SSRF, IDOR, deserialization, and similar); apply severity based on
exposure and blast radius (see the severity model above) to secrets,
dependency, and configuration findings.

## Baseline origin

For a diff-aware or development-time review specifically (see
`plays/code-review.md`'s "Diff-aware review" and
`plays/secure-development-workflow.md`), tag each finding with where it
came from relative to the current change:

```text
INTRODUCED     the vulnerable code is part of the current diff and did
               not exist before it
MODIFIED       code that existed before was changed by the current
               diff, and the change is what makes it vulnerable (or
               changes how it's vulnerable)
PRE_EXISTING   the vulnerable code is unchanged by the current diff —
               found while reviewing surrounding context, not because
               the diff touched it
UNKNOWN        git history isn't available or conclusive enough to tell
```

Do not attribute a `PRE_EXISTING` issue to the current change — that
misdirects both credit and urgency triage. But do not suppress a severe
`PRE_EXISTING` finding either just because it wasn't introduced now;
report it, clearly labeled `PRE_EXISTING`, alongside whatever the
current diff actually introduced. This tag is orthogonal to
CONFIRMED/REJECTED/NEEDS_VERIFICATION and to severity — a finding has
both.

## Vulnerability chaining

Individually moderate findings can combine into something more serious.
Examples:

```text
IDOR + predictable file ID + sensitive file download
    = HIGH data exposure (each alone might be MEDIUM/LOW)

Unrestricted upload + static execution directory
    = remote code execution
```

Look for chains explicitly, but **do not artificially combine unrelated
findings** just to inflate severity — a real chain requires that
exploiting the first finding actually enables reaching the second.

## Rejected findings

Keep rejected candidates available for audit transparency rather than
discarding them silently:

```text
Rejected candidate: SQL injection in UserRepository.cs
Reason: input reaches an EF query through a parameterized LINQ
    expression. No query-structure control demonstrated.
```

Do not clutter the main report with every rejected scanner warning —
store the detailed rejected list separately (see
`templates/security-report.md`'s "Rejected Candidate Findings" section)
and keep the main findings summary focused on what survived validation.

## Remediation requirements

Remediation guidance attached to a finding (see `templates/finding.md`'s
`### Remediation` field) must be actionable, not generic:

```text
Bad:    Sanitize input.
Good:   Replace string-concatenated SQL with parameterized queries.
Better: provide a minimal safe code example appropriate for the
        framework actually in use (see references/ for the stack).
```

Prefer the smallest safe fix. Do not use a finding's remediation as an
opportunity to rewrite unrelated architecture — that is scope creep, not
remediation.

## Verification requirements

Every remediation must include verification steps the person applying
the fix can actually run (see `templates/finding.md`'s `### Verification`
field). A representative shape:

```text
1. Add a regression test covering the vulnerable path.
2. Submit the malicious/edge-case input the finding describes.
3. Confirm the vulnerable behavior no longer occurs (e.g. query
   structure is unchanged, the path stays inside the base directory,
   the redirect target is rejected).
4. Confirm legitimate requests/inputs still work as before.
```

A finding without verification steps is incomplete — "fixed" is a claim
that needs a way to be checked, not just asserted.

## Safe testing and validation boundaries

Validation and proof-of-concept work for a finding must stay defensive:

```text
Do not:
  delete or modify production data
  modify production systems
  exfiltrate or print real, unredacted secrets (see plays/secrets-security.md)
  brute-force real accounts
  perform uncontrolled network exploitation against systems you do not
      have explicit authorization to test
```

Proof-of-concept testing should use local environments, test
environments, fixtures, mock services, or otherwise safe payloads. Active
testing against a live, in-scope target requires the user to explicitly
provide the authorized environment and request that testing — do not
assume authorization from the fact that a finding exists.

## Failure handling (scanner/tool unavailability)

If a scanner is unavailable, the review continues — it does not stop.
Report the gap explicitly:

```text
Scanner unavailable: Gitleaks
Coverage impact: automated secret detection unavailable for this run.
Fallback: manual secret review performed per plays/secrets-security.md.
```

**Never claim "no secrets found" (or the equivalent for any category)
when the scanner did not run and an equivalent manual review was not
actually performed.** State the gap instead.
