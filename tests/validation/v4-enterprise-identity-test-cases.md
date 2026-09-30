# V4 Enterprise Identity (AD/SSO) Test Cases

Validates `plays/enterprise-identity-security.md` (V4 Batch 4) and its
routing. First-version protocols: OIDC/OAuth 2.0 + JWT, direct LDAP/LDAPS,
Windows Integrated Authentication. SAML 2.0 / WS-Federation are out of this
version (`work/v4-planning/v4-design.md` section 6).

These are manual/LLM-traced cases against cited authoritative text, run the
way `tests/validation/README.md` describes (strip each fixture's header
comment first). Structural facts — every fixture exists, every fixture has an
expected result, every Scope item has a section, and every routing row points
at the play — are also checked automatically by
`tools/context_manifest/tests/test_batch4_enterprise_identity.py`. That test
does not judge findings. **Nothing here was validated against a live AD,
Entra ID, ADFS or Kerberos environment**; none was connected.

Results for this set are a **separate Recall figure**, never blended into the
V3 corpus figures. Expected
outcomes are in `tests/validation/v4-enterprise-identity-expected-results.md`.

## A. Fixture pairs, one per first-version check

All paths are under `tests/fixtures/enterprise_identity/`.

| # | Check (position paper) | Protocol | Unsafe fixture → expected | Safe fixture → expected |
|---|---|---|---|---|
| 1 | Trusted, correctly verified login result/token | OIDC/JWT | `token_validation_unsafe.cs` → CONFIRMED CRITICAL | `token_validation_safe.cs` → no finding |
| 1w | same | Windows Integrated Auth | `windows_auth_header_trust_unsafe.cs` → CONFIRMED CRITICAL | `windows_auth_negotiate_safe.cs` → no finding |
| 2 | Role/group/function/object authorization after login | OIDC | `group_authorization_unsafe.cs` → CONFIRMED HIGH | `group_authorization_safe.cs` → no finding |
| 3 | Safe AD/LDAP connection, service account, credentials, queries | LDAP/LDAPS | `ldap_connection_unsafe.cs` → CONFIRMED, 3 findings | `ldap_connection_safe.cs` → no finding |
| 4 | Fail-closed on connection/verification/group-query failure | LDAP (group lookup) | `group_lookup_fail_open_unsafe.cs` → CONFIRMED HIGH | `group_lookup_fail_closed_safe.cs` → no finding |
| 4c | Fail-closed on missing/invalid configuration | OIDC | `identity_config_missing_unsafe.cs` → CONFIRMED HIGH | `identity_config_missing_safe.cs` → no finding |
| 5 | Fixtures distinguish the cases | LDAP bind | `ldap_bind_empty_password_deceptive.cs` → CONFIRMED CRITICAL (looks safe) | — (pairs 1–4c above are the distinguishing pairs) |

Check 5 is met in two ways. First, each pair above differs in the property (or, for the
LDAP pair, the three properties) that its row's check names; the halves are otherwise the
same code. A reviewer that reports the same outcome for both halves of a pair has failed. Second, the deceptive fixture carries real but irrelevant controls.

### Traces (author's hand trace against the play text at the Batch 4 commit)

Anchors are `plays/enterprise-identity-security.md` line numbers.

| # | Fixture | Evidence in the fixture | Rule applied | Result |
|---|---|---|---|---|
| T1 | `token_validation_unsafe.cs` | `ValidateIssuer = false`, `ValidateAudience = false`, `SignatureValidator = (token, parameters) => new JsonWebToken(token)` | "Signature ... no custom SignatureValidator ... that returns the token unvalidated" (:89–93); "Issuer validated" (:94); "Audience validated" (:98) | attacker-minted token accepted → CONFIRMED CRITICAL bypass — matches |
| T2 | `token_validation_safe.cs` | tenant-specific `Authority`/`ValidIssuer`, `ValidAudience` from config, `RequireSignedTokens`, `ValidateIssuerSigningKey`, `ClockSkew` 2 min, `RequireHttpsMetadata = true`; missing config throws; the endpoint returns only the caller's own `oid`, so the app-only-token rule (:162–165) has nothing to protect here | same rows; "Lifetime ... clock skew bounded (minutes, not hours)" (:101); "Metadata fetched over HTTPS" (:105) | every switch tightens → no finding — matches; trap: the custom block alone is not a defect |
| T3 | `windows_auth_header_trust_unsafe.cs` | middleware before `UseAuthentication` builds `ctx.User` from `X-Remote-User`; Kestrel bound to `0.0.0.0` with no proxy; Negotiate yields NoResult without an `Authorization` header, so the forged principal survives and satisfies the fallback policy; the admin POST carries the same custom-header CSRF filter as the safe half, which an attacker sending requests directly simply sets | "Identity taken from the server-side Negotiate result ... never from a request header" (:109); "Proxies ... trusted only if the app is reachable exclusively through that proxy" (:112) | any caller asserts `CORP\it-admin` → CONFIRMED CRITICAL — matches |
| T4 | `windows_auth_negotiate_safe.cs` | only `AddNegotiate`; no header read; fallback policy; admin policy checks `WindowsIdentity.Groups` for a configured SID; the state-changing POST requires `X-Kiosk-Admin-Request`, which a cross-site form cannot set, and no CORS policy exists | :109; "Group or role mapped by display name ... instead of a stable identifier (... SID ...)" (:153); "Ambient credential ... a state-changing endpoint needs an anti-forgery token or custom header (plays/web-security.md's CSRF section)" (:127–130) — the custom header is present | no finding — matches; trap: `Identity.Name` from Negotiate is server-verified |
| T5 | `group_authorization_unsafe.cs` | `[Authorize]` with no policy on `admin/payroll/export`; comment relies on SSO | "'Any signed-in domain / tenant user' used as the gate for an admin or sensitive function" (:151); `plays/authorization.md` "Missing function authorization" | every tenant/guest account exports payroll → CONFIRMED HIGH — matches |
| T6 | `group_authorization_safe.cs` | policy requires `groups` claim equal to a configured object ID; `_claim_names`/`hasgroups` → false | :153 (stable identifier); "Group-claim overage ... fetch the groups or deny" (:156–159) | no finding — matches; trap: the object ID is configuration, not a secret (`plays/secrets-security.md` flags secrets, not identifiers) |
| T7 | `ldap_connection_unsafe.cs` | port 389 + `AuthType.Basic` + `Bind` with a password; `BindPassword` const; filter `"...(displayName=" + name + "))"` | "Transport ... simple bind over plain LDAP (389) exposes the password" (:181); "Service account ... not hardcoded" (:192); "Queries ... escaped per RFC 4515 ... plays/code-review.md's 'LDAP injection'" (:197) | three separate findings → CONFIRMED ×3 — matches |
| T8 | `ldap_connection_safe.cs` | port 636 + `SecureSocketLayer = true`, no `VerifyServerCertificate` callback; credential from `IOptions<DirectoryOptions>`, and missing options throw before any bind; `LdapFilter.Escape` covers `\ * ( ) NUL`; `OneLevel`, `SizeLimit = 25` | :181, "Certificates ... not disabled" (:184), :192, :197; "Missing" (:238) | no finding — matches; trap: `AuthType.Basic` is safe inside TLS |
| T9 | `group_lookup_fail_open_unsafe.cs` | `catch (Exception) { ... context.Succeed(requirement); }` | "catch around token validation, bind or group lookup that returns 'allowed'" (:218) | directory failure grants approval → CONFIRMED HIGH — matches |
| T10 | `group_lookup_fail_closed_safe.cs` | the same `catch` only logs; the requirement stays unmet | :211 section head ("access that depends on it is denied") | no finding — matches; trap: a broad catch is not itself the defect |
| T11 | `identity_config_missing_unsafe.cs` | authentication and the group-gated fallback policy are registered only `if (identityConfigured)`, with no else; `/hr/cases` is mapped unconditionally | "Missing ... authentication silently not registered, or skipped, when Authority / ClientId ... are absent" (:238) | anonymous access to HR cases on a misconfigured deployment → CONFIRMED HIGH — matches |
| T12 | `identity_config_missing_safe.cs` | throws when `Instance`/`TenantId`/`ClientId`/the group ID are missing, when `Instance` is not https, or when `TenantId` is `common`/`organizations`/`consumers`; `/hr/cases` requires the HR group, the same as in the unsafe half | :238 ("the safe behaviour is refusing to start"), "Invalid an http:// authority" (:242); "Issuer ... multi-tenant ... validates the tenant" (:94); "'Any signed-in domain / tenant user'" (:151) does not apply because of the group policy | no finding — matches; trap: refusing to start is the required behaviour |
| T13 | `ldap_bind_empty_password_deceptive.cs` | LDAPS 636, default cert validation, RFC 4514 escaping — but no empty-password check before `Bind` (`Password` is `string?`, so an empty form value reaches `Bind` as `""` under .NET 8 nullable defaults); a successful `Bind` becomes a sign-in | "Password an empty or missing password, or one containing a NUL character, is rejected BEFORE the bind ... 'bind succeeded' does not prove the password" (:133–138) | existing username + empty password signs in → CONFIRMED CRITICAL — matches; the transport and escaping controls are real but irrelevant to this path |

## B. Exclusion cases (criterion 2)

| # | Request | Expected | Rule |
|---|---|---|---|
| X1 | "Audit our entire AD environment" | Recognized as out of scope: state the boundary (not an environment audit — DC hardening, GPOs, Conditional Access, AD CS, Kerberoastable accounts are excluded); offer only a review of the applications' own use of the directory; do **not** produce an environment audit | play :40–45 ("It is not an audit of the enterprise AD / Entra environment") |
| X2 | "Review our Entra tenant's Conditional Access policies" | Same as X1 — tenant configuration, not application code | play :40–45 |
| X3 | Code under review uses SAML 2.0 via ADFS | Coverage gap stated in the review notes; `plays/authentication.md`/`plays/authorization.md` applied; the integration is **not** reported as reviewed | play :46–49 |
| X4 | Conclusion depends on the DC's LDAP signing policy or an SPN / delegation setting | Recorded as an environment assumption in the notes; neither a finding nor evidence of safety | play :50–55 |

## C. Routing cases (criterion 3), traced like `design-routing-test-cases.md`

| # | Input | Expected route | Traced through |
|---|---|---|---|
| R1 | Pre-code request "Add Entra ID sign-in to the intranet portal" | `skills/security-design` runs; requirements from `plays/enterprise-identity-security.md` | `skills/security-design/SKILL.md` activation list line "enterprise identity integration (SSO/OIDC, AD/LDAP, Windows Integrated Authentication)" (:17) and the pointer at :53–56; `plays/security-change-detection.md` HIGH list now names "enterprise identity integration" (:69–71) → HIGH → design required before implementation |
| R2 | Pre-code request "Look up a user's manager from AD by LDAP" | as R1 | same activation line; HIGH list "AD/LDAP directory access" |
| R3 | Diff adds `services.AddAuthentication().AddNegotiate()` | TARGETED review, domain `authentication`, play loaded | detection signal `AddNegotiate` in the play's "When this play applies" (:60–78), which `plays/security-change-detection.md` (:124–126) points at; `skills/security-review/SKILL.md` "Where to look next" row "Enterprise identity integration" (:336) → the play plus `plays/authentication.md`/`plays/authorization.md` |
| R4 | Diff adds an `LdapConnection` search | as R3 | signal `LdapConnection`; `skills/security-review/references/quick-reference.md` row for `LdapConnection`/`DirectoryEntry`/`PrincipalContext` |
| R5 | Diff changes a password-reset email template only | `plays/authentication.md` only; the enterprise play is **not** loaded | no integration signal present → the table row's "loaded only when ... signals are present" condition is false; the play stays out of ordinary auth reviews (the context-cost reason for D2) |
| R6 | Manifest producer for R3 (either producer) | `domains` contains `authentication`; no new domain value | D2: the play is inside the existing domain (`tools/context_manifest/domains.py` `ALL_DOMAINS` unchanged) — automated in the test file |

## D. Degraded modes

| # | Condition | Expected | Kind |
|---|---|---|---|
| D1 | No Jev token | given a classification that includes `authentication` (that classification step is a reasoning step, traced in R3/R4, not automated): built-in manifest keeps the domain; the play is reached through the domain table | [AUTO] test file |
| D2 | Jev answers without the `authentication` domain for an identity change (same premise as D1) | the domain floor restores it (validator `below_floor`) → built-in manifest; the play is still reached | [AUTO] test file |
| D3 | No Python interpreter | the kit's plain-Markdown fallback: classification and routing by hand from `plays/security-change-detection.md` and the domain table; nothing in this capability needs code | [TRACE] (`skills/security-review/SKILL.md` step 1 fallback note) |
| D4 | Identity provider / directory unreachable at runtime (application behaviour) | covered as a review rule, not a kit mode: fail-closed fixtures (pairs 4 and 4c) | [TRACE] section A |

## What this document validates and does not

Validates: the play's rules against six fixture pairs and one deceptive
fixture, covering the three first-version protocols; the out-of-scope boundary;
routing from both the design activation list and the review domain table; and
the no-token / Jev-degraded paths, which reach the play through the unchanged
`authentication` domain.

Does not validate: any live identity provider or directory; SAML/WS-Federation;
Python/Node implementations (the signals list them, but the fixtures are
ASP.NET Core only); a model's recall on this set (that is a measurement, to be
reported as its own figure, and no run is recorded here).
