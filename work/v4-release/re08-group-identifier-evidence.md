# RE-08: a group matched by distinguished name — trust boundary and evidence (2026-09-29)

**Question.** Revision 7's RE-08 review CONFIRMED a LOW finding on
`tests/fixtures/enterprise_identity/group_lookup_fail_closed_safe.cs`: "authorization gate keyed to a mutable AD group
identifier (DN)". Revision 6's review of the same file, with the same routed domains and the same four files read,
reported no finding. This record traces whether an untrusted attacker can make that value, or its meaning, change.
It does not treat "the row is expected safe" as evidence.

**Answer.** No attacker path exists in the case. The only way to repoint the gate is a privileged directory change. The
DN match is therefore **not a security vulnerability**. What remains is an availability/configuration risk and an
environment assumption, both recorded below.

## The code, as the runner sees it

| Element | Code | Who controls it |
|---|---|---|
| Group identifier | `private const string ApproversGroupDn = "CN=Finance Approvers,OU=Groups,DC=corp,DC=example";` | the application's source code. It is a compile-time constant; no request value reaches it |
| Caller identity | `var upn = context.User.Identity?.Name;` | the authenticated principal set by the host's authentication, not a request field. A missing identity returns without success |
| Membership check | `await _groups.IsMemberAsync(upn, ApproversGroupDn, cts.Token)` | the directory, through an `IDirectoryGroups` implementation that is not in the case |
| Grant | `context.Succeed(requirement)` only when that call returns `true` | — |
| Failure | `catch (Exception ex) { _log.LogWarning(...); }`: the requirement stays unmet | fail-closed. That is the property this row tests (`tests/validation/v4-enterprise-identity-test-cases.md` T10) |

## What could change which object the DN names

| Change | Effect on the gate | Who can make it | Classification |
|---|---|---|---|
| The group is renamed or moved to another OU | the DN no longer names the group. The case's own code grants only on `true`, so access is **denied** if the lookup reports no membership. That the out-of-case `IDirectoryGroups` implementation does so for a DN that no longer resolves is an **environment assumption** | a directory writer with rights on that object | availability/configuration risk (fail-closed), recorded, not a security finding |
| The group is deleted and a new group is created at the same DN | the gate now follows the new group's membership | a directory writer with create and delete rights in `OU=Groups` | environment fact (directory permissions). Record it as an assumption: "whoever administers `OU=Groups` controls this gate" |
| A second object with the same DN | impossible: a DN names exactly one object in a directory | — | — |
| The caller supplies or influences the DN | no path: it is a constant | — | — |
| The caller's identity is forged | outside this row: the identity is the host's authenticated principal, and the other rows cover its verification | — | — |

**Consequence.** Every path that changes the gate needs directory write permissions. That is privileged,
environment-level control, which the play puts out of scope ("not an audit of the enterprise AD / Entra
environment"; "environment facts that code cannot show are not findings and not passes").

**No bypass exists in the case.** There is no cross-scope ambiguity: the DN names one domain. There is no wrong
identity-to-group mapping, and no stated policy that requires a SID or object ID.

## Root cause of the finding, and the guidance change

The play's rule said: "Group or role mapped by display name / sAMAccountName string instead of a stable identifier ...
— names can be renamed or duplicated". It did not say how to judge a unique-but-mutable name such as a DN, and one
review stretched "can be renamed" into a finding.

By the user's decision (2026-09-29) the rule now separates three cases, deciding by the case's trust boundary and
attacker privileges, never by the field name alone:
- **A display name** is not a security identity key: an authorization decision keyed on one is a finding.
- **A unique-but-mutable name** (sAMAccountName, a DN) is decided by what the code shows:
  - a rename, move or delete that fails closed is an availability/configuration risk;
  - control over the directory object is an environment assumption;
  - a security finding needs one of these to be shown: an ambiguous match across scopes, a wrong identity mapping, an
    authorization bypass, or a breach of an explicit policy.
- **General authorization rules are unchanged.** That includes "any signed-in user", group-claim overage, and a
  fail-open lookup.

`tools/context_manifest/tests/test_release_rv18_re08.py` checks the rule text and the trust-boundary facts above
against the fixture.
