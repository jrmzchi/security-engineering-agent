# Play: Configuration Security

Authoritative procedure for deployment/configuration findings.

## Scope

```text
Debug enabled
Verbose errors
Unsafe CORS
Insecure cookies
Missing HTTPS enforcement
Dangerous IIS configuration
Directory browsing
Sensitive static files
Exposed backups
Development configuration in production
```

## Debug enabled in production (CWE-489 / CWE-215)

Frameworks' debug/development modes often expose stack traces, source
snippets, environment variables, or even a code-execution console
(e.g. Flask's Werkzeug debugger, ASP.NET Core's developer exception
page) to anyone who can trigger an unhandled exception. Check the actual
runtime configuration for the production environment, not just the
repository default — a `DEBUG=True` default in source that is always
overridden by a production environment variable is not itself the
finding; confirm what value is actually used where it runs.

## Verbose errors

Stack traces, internal file paths, SQL fragments, or library version
numbers returned in error responses give an attacker a reconnaissance
advantage and sometimes directly leak secrets (a connection string in a
DB-connection-failure stack trace). Production error handling should
return a generic message and log the detail server-side only.

## Unsafe CORS

See `plays/web-security.md`'s CORS section for the specific
misconfiguration patterns; here, check that the CORS policy is actually
sourced from a fixed configuration for the deployed environment rather
than left permissive "temporarily" in a config file that ships to
production.

## Insecure cookies

```text
Missing Secure flag        cookie sent over plaintext HTTP if ever reached
Missing HttpOnly flag       cookie readable by JavaScript (XSS impact
                            amplifier for session/auth cookies)
Missing/incorrect SameSite  see CSRF considerations in
                            plays/web-security.md
No Domain/Path scoping      broader-than-necessary exposure across
                            subdomains/paths
```

For session/auth cookies specifically, see also `plays/authentication.md`'s
"Session hijacking" section — the same flags matter there from the
account-takeover angle rather than the general configuration-hardening
angle.

## Missing HTTPS enforcement

No redirect from HTTP to HTTPS, no HSTS header, or a load balancer/proxy
terminating TLS while the origin accepts plaintext connections directly
from outside the trusted network. Check the actual network topology —
"TLS terminates at the load balancer" is fine only if nothing outside a
trusted boundary can reach the origin over plaintext.

## Dangerous IIS configuration

See `references/iis-security.md` for the full IIS-specific checklist
(anonymous access, application pool identity, request filtering,
security headers). Pay particular attention to the gap between a
Kestrel-based development configuration and the IIS production
deployment — settings that are safe defaults under `dotnet run` locally
are not automatically applied under IIS.

## Directory browsing

Enabled directory listing on any web-accessible path exposes the
existence (and often the content) of every file in that directory,
including ones never linked from the application — check web-server
configuration (IIS `directoryBrowse`, Nginx `autoindex`, static-file
middleware defaults) rather than assuming it is off by default.

## Sensitive static files

Files served statically that should not be public: `.env`, `.git/`
(an entire repository, including history, if the web root is the repo
root), backup files (`*.bak`, `*.old`, `~`-suffixed editor backups),
source maps for production JS that reveal original source, and
configuration files with embedded credentials.

## Exposed backups

Database dumps, archive files, or configuration backups left in a
web-accessible location (even briefly, during a deployment process) are
a direct data-exposure risk — check deployment scripts and CI/CD
pipelines for where backups are written, not just the current file
listing.

## Development configuration in production

Beyond debug mode specifically: development-only authentication bypass
flags, mock/test service endpoints, seeded test accounts with known
credentials, or relaxed rate limits meant only for local testing —
anything gated by an environment flag should be checked for what that
flag actually resolves to in the production deployment.
