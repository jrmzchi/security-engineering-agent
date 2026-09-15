# Reference: ASP.NET Core Security

ASP.NET Core's web layer specifically. See `references/dotnet-security.md`
for general .NET platform concerns and `references/iis-security.md` for
IIS deployment concerns.

## Authentication

```text
Cookie authentication      check cookie flags (Secure/HttpOnly/SameSite)
                            via CookieAuthenticationOptions, not just
                            that authentication is configured at all
JWT bearer authentication   check the token validation parameters:
                            ValidateIssuer, ValidateAudience,
                            ValidateLifetime, ValidateIssuerSigningKey
                            should all be true unless there is a
                            specific, documented reason otherwise;
                            check the signing key is not hardcoded
                            (see plays/secrets-security.md)
```

## Authorization

```text
[Authorize]                 presence alone does not prove correctness —
                            check WHICH policy/role/claim it requires,
                            and whether that matches the endpoint's
                            actual sensitivity
Policies / roles / claims   a policy checking a claim's presence but not
                            its value (e.g. "has a Role claim" instead
                            of "Role claim equals Admin") is a common,
                            easy-to-miss authorization gap
[AllowAnonymous]            on a controller/action that should require
                            auth — check it wasn't left over from
                            scaffolding/testing
Minimal API endpoints        (.MapGet/.MapPost, etc.) — authorization is
                            normally opt-in per-endpoint via
                            .RequireAuthorization() or a group-level
                            .MapGroup(...).RequireAuthorization(). Before
                            treating a missing per-endpoint call as a
                            gap, check whether AddAuthorization() sets a
                            global AuthorizationOptions.FallbackPolicy —
                            when set, it applies to every endpoint with
                            no authorization metadata of its own
                            (Minimal API included), and a missing
                            per-endpoint call is then intentional, not a
                            gap
```

## Antiforgery

```text
[ValidateAntiForgeryToken] / [AutoValidateAntiforgeryToken]  check it is
    actually present on state-changing MVC actions, not just configured
    globally without being wired to the relevant endpoints
Minimal APIs / SPA-consumed APIs relying on custom-header or
    SameSite=Strict cookie patterns instead of the MVC antiforgery
    token — verify whichever pattern is used is actually applied, per
    plays/web-security.md's CSRF section
```

## Model binding

```text
Binding the request body directly onto a persistence/domain entity
    (mass assignment — see plays/api-security.md) instead of a
    dedicated DTO with only the fields the endpoint should accept
[Bind] attribute allowlist used inconsistently — some actions have it,
    others (added later, or via scaffolding) don't
```

## Entity Framework / raw SQL

```csharp
// Safe: parameterized via LINQ or FromSqlInterpolated
var user = context.Users.FirstOrDefault(u => u.Name == name);
var rows = context.Users.FromSqlInterpolated($"SELECT * FROM Users WHERE Name = {name}");

// Unsafe: FromSqlRaw / ExecuteSqlRaw with string concatenation
var rows = context.Users.FromSqlRaw("SELECT * FROM Users WHERE Name = '" + name + "'");
context.Database.ExecuteSqlRaw("UPDATE Users SET Role = '" + role + "' WHERE Id = " + id);
```

`FromSqlRaw`/`ExecuteSqlRaw` are not unsafe by definition — they are
unsafe when the SQL string itself is built by concatenation.
`FromSqlRaw` called with parameter placeholders and a separate parameters
array is safe; the SQL string containing the literal value is not. See
`references/sql-security.md` for the general SQL parameterization pattern
this exemplifies.

## File handling

```text
IFormFile              see plays/file-security.md for upload validation;
                        additionally check IFormFile.FileName is never
                        used directly to build a save path
StaticFiles middleware  check which physical directory it serves and
                        whether that directory can receive
                        user-uploaded content (see plays/file-security.md's
                        "Uploads" section)
```

For `Path.Combine`/`Path.GetFullPath` containment-check patterns and raw
`SqlCommand` parameterization, see `references/dotnet-security.md`'s
"File and SQL APIs" section — these are general .NET APIs, not
ASP.NET-specific ones.

## Redirects

```csharp
// Unsafe: redirecting to a raw user-supplied URL
return Redirect(returnUrl);

// Safer: ASP.NET Core's built-in local-redirect check
return LocalRedirect(returnUrl); // throws if returnUrl is not local
// or explicitly validate against an allowlist for cross-site redirect targets
```

## CORS

```csharp
// Unsafe: wildcard origin combined with credentials
services.AddCors(o => o.AddPolicy("p", b => b
    .AllowAnyOrigin()
    .AllowCredentials())); // this combination is actually rejected at
                            // runtime by the framework, but a policy
                            // reflecting the request Origin header
                            // instead of an explicit allowlist achieves
                            // the same unsafe effect and IS accepted

// Safer: explicit allowlist
services.AddCors(o => o.AddPolicy("p", b => b
    .WithOrigins("https://trusted.example.com")
    .AllowCredentials()));
```

## Configuration and exception handling

```text
app.UseDeveloperExceptionPage() reachable in a production environment
    (check the actual `IsDevelopment()`/environment-name gate, not just
    that the code exists)
Exception middleware order — an exception handler registered after
    routes it should protect will not catch their exceptions
```

See `references/dotnet-security.md` for `appsettings.json`/secrets
handling and `plays/configuration-security.md` for the general
development-configuration-in-production principle.
