# Play: Enterprise Identity Integration (AD/SSO)

Authoritative procedure for whether an application **correctly uses the
identity result** of an existing enterprise AD/SSO integration. It is
loaded inside the `authentication` domain (no separate domain), only when
the code under review actually integrates with one of the first-version
protocols below — see "When this play applies".

The generic rules stay where they are and are not restated here:
`plays/authentication.md` (bypass, fail-open branches, sessions, credential
exposure) and `plays/authorization.md` (object- and function-level
authorization). This play adds only what is specific to consuming an
enterprise identity provider or directory. Findings still go through
`plays/finding-validation.md` and `plays/security-gate.md` unchanged.

## Scope

```text
Trusted, verified login result
Authorization after login
Directory connection, service account and query safety
Fail-closed on identity failure
Missing, invalid or stale identity configuration
Identity data in logs
```

First-version protocols (decided 2026-09-25, `work/v4-planning/v4-design.md`
section 6):

```text
OIDC / OAuth 2.0     sign-in through Entra ID or ADFS; JWT bearer tokens
                     accepted by APIs
LDAP / LDAPS         the application itself binds to and queries AD
Windows Integrated   Negotiate (Kerberos, NTLM fallback) on IIS, HTTP.sys
Authentication       or Kestrel
```

## What this play does not do

- **It is not an audit of the enterprise AD / Entra environment.** Domain
  controller hardening, GPOs, tenant Conditional Access, AD CS, Kerberoastable
  accounts, trust relationships and the like are out of scope. A request
  framed as "audit our entire AD environment" is answered by stating that
  boundary and, where useful, reviewing only the applications' own use of
  the directory — it does not expand into an environment audit.
- **SAML 2.0 and WS-Federation are not covered in this version.** When the
  code under review uses them, state that coverage gap in the review's
  notes, apply `plays/authentication.md` / `plays/authorization.md` as
  usual, and do not report the integration as reviewed.
- **Environment facts that code cannot show are not findings and not
  passes.** A domain controller's LDAP signing policy, an SPN registration,
  a service account's delegation setting, a tenant's token lifetime
  policy: record each one the conclusion depends on as an environment
  assumption in the review's notes. Never treat it as evidence that the
  integration is safe.
- **No live validation is implied.** This kit's own validation of this play is
  fixtures, manual traces and static checks only
  (`tests/validation/v4-enterprise-identity-test-cases.md`).

## When this play applies

Load it when the change or repository contains an integration signal.
This list is the kit's one copy of these signals —
`plays/security-change-detection.md`'s detection signals point here
instead of repeating them. It gives examples and is not exhaustive:

```text
.NET     AddOpenIdConnect AddMicrosoftIdentityWebApp AddMicrosoftIdentityWebApi
         AddJwtBearer with an Entra ID / ADFS Authority, Microsoft.Identity.Web,
         MSAL, AddNegotiate, NegotiateDefaults, WindowsIdentity,
         IIS windowsAuthentication, System.DirectoryServices(.Protocols,
         .AccountManagement), LdapConnection, DirectoryEntry,
         DirectorySearcher, PrincipalContext
Python   ldap3, python-ldap, msal, authlib / OIDC client libraries
Node     ldapjs, openid-client, passport-azure-ad, @azure/msal-node
Config   Authority / TenantId / ClientId / Instance settings, LDAP server /
         bind DN / search base settings, IIS authentication sections
```

A signal routes material; it is not a finding.

## Trusted, verified login result

The identity the application acts on must come from the identity
provider's verified result, never from something the client can set.

```text
OIDC / OAuth 2.0 / JWT
  Signature      validated with keys from the provider's metadata;
                 unsigned tokens rejected; algorithm restricted to the
                 provider's (no "none", no HS*/RS* key confusion); no
                 custom SignatureValidator / validation delegate that
                 returns the token unvalidated
  Issuer         validated against the exact expected issuer / tenant; a
                 multi-tenant ("common"/"organizations") app validates the
                 tenant (tid) against an allowlist instead of turning
                 issuer validation off
  Audience       validated against this application's client ID /
                 App ID URI; an API does not accept an ID token, or a
                 token issued for another audience, as an access token
  Lifetime       expiry validated, clock skew bounded (minutes, not hours)
  Flow           authorization code flow; state and nonce validated
                 (the framework handler does this unless disabled); PKCE for
                 public clients; tokens are not taken from URL query strings
  Metadata       fetched over HTTPS (RequireHttpsMetadata not disabled in
                 production) with certificate validation left on

Windows Integrated Authentication
  Identity       taken from the server-side Negotiate result
                 (HttpContext.User / WindowsIdentity), never from a request
                 header, form field or cookie the client controls
  Proxies        a user header set by a front-end proxy (X-Remote-User,
                 REMOTE_USER, X-Forwarded-User) is trusted only if the app
                 is reachable exclusively through that proxy and the proxy
                 strips client-supplied copies — otherwise any client can
                 assert any identity
  Anonymous      anonymous authentication is not enabled on a path that
                 the application itself leaves unprotected
                 (references/iis-security.md, "Anonymous access"). Anonymous
                 plus Windows authentication both enabled on IIS is normal
                 when the app's own [Authorize] / fallback policy issues the
                 challenge
  Protocol       NTLM not forced where Kerberos is expected; Extended
                 Protection for Authentication (channel binding) actually
                 ENABLED (IIS tokenChecking Allow/Require; its default is
                 None) where the host supports it, not merely "not disabled"
  Ambient        the browser sends Negotiate/NTLM automatically (intranet
  credential     zone), like a cookie: a state-changing endpoint needs an
                 anti-forgery token or custom header (plays/web-security.md's
                 CSRF section); SameSite cannot protect this credential

LDAP bind used as the login check
  Password       an empty or missing password, or one containing a NUL
                 character, is rejected BEFORE the bind: a simple bind with a
                 DN and an empty password is an unauthenticated bind that many
                 directories accept (a native LDAP client stops reading at a
                 NUL, so a password that starts with one is empty there), so
                 "bind succeeded" does not prove the password (CWE-287)
  Result         "user found by search" is never treated as "password
                 correct"; the bind is performed as the user, over a
                 protected channel (see "Directory connection...")
```

## Authorization after login

An authenticated enterprise identity is not an authorization decision.
Every endpoint still needs its function- and object-level check per
`plays/authorization.md`. Specific to enterprise identity:

```text
"Any signed-in domain / tenant user" used as the gate for an admin or
    sensitive function
Group or role mapped by display name: a display name is neither unique
    nor a security identity key. An authorization decision keyed on one is
    a finding. Use a stable identifier: group object ID, SID or app role
    value
Group or role mapped by a directory name that is unique but mutable
    (sAMAccountName, a distinguished name): decide from the case's actual
    trust boundary and attacker privileges, never from the field name
    alone.
    -> a rename, move or delete makes the match fail and access is denied
       (fail-closed): an availability / configuration risk, recorded in
       the notes. Not a security finding.
    -> whoever may create, rename, or delete and recreate that directory
       object controls the gate: an environment fact (directory
       permissions), recorded as an assumption per "What this play does
       not do". Not a finding by itself.
    -> a security finding only when the code in scope shows one of these:
       an ambiguous match across scopes (the same name accepted from
       another domain, forest or tenant), a wrong identity-to-group
       mapping, an authorization bypass, or a breach of an explicit policy
       the scope states
Group-claim overage ignored: when a user has too many groups the token
    carries an overage indicator (_claim_names / hasgroups) instead of the
    groups; treating "no group claim" as "no restriction" or as a default
    role is a finding — fetch the groups or deny
Guest / B2B / external accounts receive the same authorization as members
    when the application's design says they should not
An API that accepts any valid token for its audience without checking the
    delegated scope (scp) or the app role (roles): other tenant apps can get
    an app-only token for it via client credentials unless the resource
    requires assignment (an environment fact: record it as an assumption)
Authorization decided in the authentication event handler or a claims
    transformation that is skipped or swallowed on error, instead of in
    an authorization policy that always runs
IsInRole / group-membership checks against a hardcoded string that does
    not match what the provider actually issues (the check silently never
    passes or, worse, a fallback grants access)
```

Keep the two concerns separate in the evidence: the identity provider
establishes who the caller is; the application's own policy decides what
the caller may do.

## Directory connection, service account and query safety

```text
Transport      LDAPS (636) or StartTLS before any bind carrying a password;
               simple bind over plain LDAP (389) exposes the password on
               the network
Certificates   server certificate validation not disabled
               (VerifyServerCertificate / ServerCertificateValidationCallback
               returning true, LDAPTLS_REQCERT=never, OPT_X_TLS_NEVER,
               rejectUnauthorized:false)
Signing        Negotiate/Kerberos bind without TLS: signing and sealing
               confirmed on (LdapConnection: SessionOptions.Signing/Sealing
               set, default off; PrincipalContext: on by default unless
               ContextOptions drops them); over LDAPS, channel binding kept
Service        bind credentials not hardcoded or committed
account        (plays/secrets-security.md); stored in a secret store, a
               managed identity or a gMSA; replaceable without a rebuild
               (rotation); the account is read-only, scoped to the needed
               OU, and not a privileged / Domain Admin account
Queries        LDAP filter values escaped per RFC 4515 and DN components
               per RFC 4514 — the injection rule itself is
               plays/code-review.md's "LDAP injection" (CWE-90); search base
               and scope limited to what the feature needs; size/time
               limits set
Kerberos /     impersonation (WindowsIdentity.RunImpersonated, ASP.NET
delegation     impersonation) reaches only resources the user may reach;
               a double-hop to a back end requires constrained delegation
               (an environment assumption, record it); code does not
               rely on unconstrained delegation
OIDC client    client secret not committed; prefer a certificate or managed
credential     identity; rotation possible without a code change
```

## Fail-closed on identity failure

When the identity provider or directory cannot be reached, returns an
error, or its answer cannot be verified, access that depends on it is
denied. Fail-open shapes:

```text
catch around token validation, bind or group lookup that returns
    "allowed", a default role, or continues as if membership were known
An authentication-failed event handler that calls Success(), sets a
    principal, or suppresses the failure (OnAuthenticationFailed /
    OnRemoteFailure / OnTokenValidated swallowing the exception)
Group lookup timeout treated as "not in the deny group" rather than
    "membership unknown"
A failover path that is weaker than the primary: a secondary directory
    over plain LDAP, a local-account fallback without its own controls,
    certificate validation relaxed "only when the primary is down"
Cached identity or group data used after its expiry because refresh
    failed
```

A deliberate break-glass path is not a finding by itself; it is one when it
has no authorization, audit or scope of its own.

## Missing, invalid or stale identity configuration

```text
Missing   authentication silently not registered, or skipped, when
          Authority / ClientId / LDAP server settings are absent (for
          example "if not configured, skip auth"); the safe behaviour
          is refusing to start or refusing requests
Invalid   an http:// authority or metadata address, a wildcard / empty
          audience, an issuer list containing a placeholder, a test
          tenant in a production configuration
Stale     a signing key copied from the provider's JWKS into
          configuration and never refreshed (breaks or, if a validation
          switch is flipped to "fix" it, fails open); metadata refresh
          disabled; group or role mappings pointing at identifiers that no
          longer exist
```

## Identity data in logs

```text
Tokens, Authorization headers, bind passwords, client secrets and
    Kerberos tickets never logged (plays/authentication.md's
    "Credential exposure" applies)
IdentityModelEventSource.ShowPII (or the equivalent "log PII" switch)
    not enabled in production
Directory exceptions logged without the bind DN's password or the full
    connection string
```

Failed-login and authorization-denied events are still logged, without
the secret material.

## Evidence and severity

Use `plays/finding-validation.md`'s attack-path model and confidence levels
unchanged. Typical shapes: signature, issuer or audience validation
disabled on a reachable endpoint, an empty-password LDAP bind accepted as a login,
and a client-controlled identity header trusted directly are
authentication bypasses (usually CRITICAL/HIGH). Plain-LDAP simple bind and
disabled certificate validation need a network position (usually HIGH/MEDIUM,
per the deployment). A fail-open group lookup inherits the severity of
what the group protects.

Check 5 of the first version (safe/unsafe fixtures and controlled tests
distinguish the cases above) is this play's own validation obligation:
`tests/validation/v4-enterprise-identity-test-cases.md` and the
`tests/fixtures/enterprise_identity/` fixtures. Their results are reported as
their own Recall figure, separate from the V3 fixture corpus.
