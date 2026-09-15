# Security Design Routing Test Cases

Validates that `skills/security-design`'s activation list (see that
skill's "When to use") triggers correctly for a pre-code
request — before any diff exists to classify. Distinct from
`classification-test-cases.md`, which is about
`skills/security-change-detection`'s sensitivity levels; this is
specifically about whether `skills/security-design` runs *before*
implementation and what it should ask about.

| # | Request | Should security-design run? | Expected focus (per `plays/security-design.md`'s nine questions) |
|---|---|---|---|
| 1 | "Add a file download API" | Yes | file security, authorization (object-level — which file can this caller access), path handling (client-supplied filename must not become a trusted physical path) |
| 2 | "Add password reset" | Yes | authentication, token handling (single-use, time-limited reset tokens), sensitive data (does not leak whether an email is registered beyond what's acceptable) |
| 3 | "Add a CSS animation" | No | — (NONE per `skills/security-change-detection`; no attacker-controlled input or privileged operation) |
| 4 | "Add outbound URL fetch from user input" | Yes | SSRF/network security — see `ssrf_user_url_unsafe.py`/`ssrf_allowlist_safe.py` for what the resulting requirements should catch |
| 5 | "Add an admin-only delete endpoint" | Yes | authentication, authorization (both object- and function-level — see `authorization_removed_unsafe.cs`) |
| 6 | "Add a new database query for an existing, already-authorized report" | Yes (lightweight) — see note | database operations is on the activation list, so design runs; but this is also `classification-test-cases.md`'s MODERATE example, so run a lightweight pass (the nine questions answered briefly) rather than a full design write-up |
| 7 | "Rename a private helper method" | No | No security-relevant behavior change |

Case 6 illustrates that `skills/security-design`'s activation list and
`skills/security-change-detection`'s sensitivity level are two
independent signals that can disagree in *degree* without disagreeing
in *kind* — see `plays/security-change-detection.md`'s MODERATE section
("also check `skills/security-design`'s own activation list
independently of this level"). The activation list says "this touches
a database operation, so ask the nine questions"; the sensitivity
level says "but this one is low-stakes enough that the answers should
be quick, not a full write-up." Both can be true at once.
