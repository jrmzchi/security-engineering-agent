# Reference: IIS Security

IIS-specific deployment concerns for ASP.NET Core (or classic ASP.NET)
applications. See `references/aspnet-security.md` for the application
layer and `references/windows-security.md` for general Windows path/
permission semantics.

## Hosting model: check this first

This is the single most important thing to check for an IIS-deployed
ASP.NET Core app, and it changes every check below: **which hosting
model is configured** (`<AspNetCoreHostingModel>` in the `.csproj`, or
the `hostingModel` attribute in `web.config`'s `<aspNetCore>` element —
default is **InProcess** since ASP.NET Core 3.0).

```text
InProcess (default since 3.0)
    The app runs inside the IIS worker process (w3wp.exe) via the
    ASP.NET Core Module v2 (ANCM v2), using IISHttpServer as the actual
    web server. Kestrel is NOT in the request path at all — there is no
    separate Kestrel process to check limits/config on. ANCM's handler
    mapping is typically path="*" verb="*", meaning IIS hands every
    request to the app; the app's own StaticFiles middleware (not IIS
    directly walking the physical directory) decides what gets served
    and from where.

OutOfProcess
    The app runs as a separate process running Kestrel; IIS/ANCM acts
    as a reverse proxy in front of it. This is the model where "settings
    safe under `dotnet run` locally are not automatically applied under
    IIS" is the relevant framing, and where Kestrel's own configuration
    (KestrelServerLimits, etc.) is actually part of the request path
    alongside IIS's.
```

Checking Kestrel-specific settings (`KestrelServerLimits.MaxRequestBodySize`,
Kestrel timeouts) against an InProcess deployment is a false lead — for
InProcess, check `IISServerOptions` (e.g. `MaxRequestBodySize`, default
30MB) and IIS's own `maxAllowedContentLength` in `web.config` instead.

```text
Developer exception pages         gated by ASPNETCORE_ENVIRONMENT, which
                                    must be set correctly in the IIS
                                    application pool / web.config, not
                                    just in a local launchSettings.json
                                    that never reaches the server. This
                                    check applies to both hosting models.
Request size / timeout limits      InProcess: check IISServerOptions and
                                    web.config's maxAllowedContentLength.
                                    OutOfProcess: check Kestrel's own
                                    limits AND IIS's — both are
                                    independently in the request path,
                                    so a generous setting on one side
                                    does not help if the other is
                                    misconfigured.
```

## Anonymous access

Check the site/application's Authentication settings in IIS —
Anonymous Authentication enabled where the application expects Windows
Authentication or another scheme to gate access is a common
misconfiguration that bypasses the application's own auth entirely at
the IIS layer, before requests even reach the app.

## Application pool identity

```text
Running as a highly privileged account (LocalSystem, a domain admin
    account) instead of a dedicated, least-privilege application pool
    identity (ApplicationPoolIdentity or a scoped service account)
Application pool identity granted write access to directories it does
    not need write access to (beyond its own temp/upload directories)
```

## Filesystem permissions

The application pool identity should have read access to the
application's files and write access only to directories it genuinely
needs to write to (uploads, logs, temp). Broad write access to the
application's own code/binary directory would let a successful upload/
write vulnerability escalate to persistent code execution.

## web.config

```text
Contains connection strings or other secrets directly (see
    plays/secrets-security.md) instead of referencing configuration
    providers/environment variables
<httpErrors> / custom error pages configured to avoid leaking stack
    traces (see plays/configuration-security.md's "Verbose errors")
<security><requestFiltering> present and not overly permissive (see
    below)
```

## Request filtering

```text
Verify dangerous file extensions/segments the application does not need
    to serve are not explicitly allowed
Verify hidden segments (.git, appsettings.json, .env if present) are not
    reachable — either through requestFiltering's hiddenSegments/
    fileExtensions or through the application's own StaticFiles
    configuration (see references/aspnet-security.md)
```

## Directory browsing

Confirm `<directoryBrowse enabled="false" />` (the IIS default) has not
been overridden to `true` — see `plays/configuration-security.md`'s
"Directory browsing" section for the general risk.

## TLS / HTTP to HTTPS

```text
An IIS site bound to both HTTP and HTTPS without an HTTP->HTTPS
    redirect rule (URL Rewrite, or the application's own
    UseHttpsRedirection — verified this actually reaches IIS, not just
    the Kestrel layer behind it)
HSTS header present via app.UseHsts() or IIS-level configuration
Outdated TLS protocol versions enabled at the server/OS level (this is
    an OS/Windows-Server configuration concern, not application code —
    flag it for the infrastructure owner, note it as a coverage
    boundary if it cannot be checked from source alone)
```

## Security headers

Check for `X-Frame-Options`/`frame-ancestors`, `X-Content-Type-Options:
nosniff`, and a CSP, configured either in the application (middleware) or
via IIS's `<httpProtocol><customHeaders>` — either location is a valid
place to set them, but they need to be set in at least one.

## Static file exposure

For an **InProcess**-hosted app, ANCM hands every request to the
application — what gets served statically is decided by the
application's own `StaticFiles` middleware configuration (see
`references/aspnet-security.md`'s StaticFiles section), not by IIS
walking the physical directory directly. For a **classic ASP.NET**
application (not ASP.NET Core) or a static/non-ASP.NET site under IIS,
IIS itself does serve files directly from the physical path, and request
filtering (below) is what excludes sensitive ones. Check which of these
applies before concluding a file is (or is not) reachable — see
`plays/configuration-security.md`'s "Sensitive static files" for the
general risk either way.

## Log configuration

Confirm IIS logging is enabled for the site (useful for incident
investigation) and that logs themselves are not stored in a
web-accessible location.
