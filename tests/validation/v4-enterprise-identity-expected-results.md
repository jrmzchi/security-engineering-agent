# V4 Enterprise Identity (AD/SSO): Expected Results

One row per fixture in `tests/fixtures/enterprise_identity/` (V4 Batch 4,
`plays/enterprise-identity-security.md`). This set is reported as **its own
Recall figure**. It is
**not** part of `tests/validation/expected-results.md` (the V3 corpus), its
"Summary counts", or a V3 corpus pass. Run a pass the way
`tests/validation/README.md` describes, stripping each fixture's header
comment first. Traces and the exclusion, routing and degraded-mode cases are in
`tests/validation/v4-enterprise-identity-test-cases.md`.

| Fixture (under `tests/fixtures/enterprise_identity/`) | Expected outcome | Category / CWE | Trap being tested |
|---|---|---|---|
| `token_validation_unsafe.cs` | CONFIRMED, CRITICAL | Authentication bypass: token signature/issuer/audience not validated / CWE-347, CWE-287 | — |
| `token_validation_safe.cs` | No confirmed finding | — | reviewer flags any custom `TokenValidationParameters` block or a non-default `ClockSkew`, missing that every switch here tightens the defaults |
| `group_authorization_unsafe.cs` | CONFIRMED, HIGH | Missing function-level authorization after SSO / CWE-862, CWE-285 | — |
| `group_authorization_safe.cs` | No confirmed finding | — | reviewer flags the group object ID as a hardcoded secret, or the overage denial as broken access, missing that the ID is non-secret configuration and denying on overage is the fail-closed choice |
| `ldap_connection_unsafe.cs` | CONFIRMED, 3 findings (cleartext Basic bind on 389; hardcoded service-account password; LDAP filter injection) | CWE-319; CWE-798; CWE-90 | — |
| `ldap_connection_safe.cs` | No confirmed finding | — | reviewer flags any `LdapConnection` search built from request data, or `AuthType.Basic` alone, missing LDAPS with default certificate validation, the injected credential and the RFC 4515 escaping |
| `group_lookup_fail_open_unsafe.cs` | CONFIRMED, HIGH | Fail-open authorization on directory failure / CWE-636, CWE-285 | — |
| `group_lookup_fail_closed_safe.cs` | No confirmed finding | — | reviewer flags the broad `catch (Exception)` itself, missing that the catch leaves the requirement unmet (deny) |
| `windows_auth_header_trust_unsafe.cs` | CONFIRMED, CRITICAL | Authentication bypass by a client-supplied identity header / CWE-290, CWE-287 | — |
| `windows_auth_negotiate_safe.cs` | No confirmed finding | — | reviewer treats `User.Identity.Name` from Negotiate as client-controlled, flags the group SID as a secret, or reports CSRF on the admin POST, missing its custom-header requirement |
| `ldap_bind_empty_password_deceptive.cs` | CONFIRMED, CRITICAL | Authentication bypass: unauthenticated (empty-password) simple bind accepted as login / CWE-287 | LDAPS with certificate validation and RFC 4514 DN escaping, presented as if they made the bind trustworthy; neither rejects an empty password |
| `identity_config_missing_unsafe.cs` | CONFIRMED, HIGH | Authentication silently disabled when identity configuration is missing / CWE-1188, CWE-306 | — |
| `identity_config_missing_safe.cs` | No confirmed finding | — | reviewer flags the startup `throw` as an availability defect, missing that refusing to start is the required fail-closed behaviour (the endpoint is group-gated, and multi-tenant tenant aliases are rejected) |

```text
Batch 4 set -- must produce a CONFIRMED finding:     7  (6 *_unsafe + 1 *_deceptive)
Batch 4 set -- must NOT produce a CONFIRMED finding: 6  (6 *_safe)
```
