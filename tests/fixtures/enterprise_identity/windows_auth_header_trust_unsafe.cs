// Fixture: Windows Integrated Authentication bypassed by a trusted identity header (VULNERABLE)
//
// Expected review outcome: CONFIRMED, CRITICAL authentication bypass
// (CWE-290 authentication bypass by spoofing; CWE-287).
// See plays/enterprise-identity-security.md, "Trusted, verified login result"
// (Windows Integrated Authentication, Proxies).
//
// Attack path: Kestrel listens directly on the network (no front-end proxy
// strips the header). A request carrying "X-Remote-User: CORP\it-admin"
// runs before Negotiate authentication and becomes that user's identity,
// so every caller can be anyone.

using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.Negotiate;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://0.0.0.0:8080");

builder.Services.AddAuthentication(NegotiateDefaults.AuthenticationScheme).AddNegotiate();
builder.Services.AddAuthorization(o => o.FallbackPolicy = o.DefaultPolicy);

var app = builder.Build();

// "Reverse-proxy SSO support": take the user from the header when present.
app.Use(async (ctx, next) =>
{
    var forwarded = ctx.Request.Headers["X-Remote-User"].ToString();
    if (!string.IsNullOrEmpty(forwarded))
    {
        // VULNERABLE: client-supplied header becomes the authenticated identity
        ctx.User = new ClaimsPrincipal(new ClaimsIdentity(
            new[] { new Claim(ClaimTypes.Name, forwarded) }, authenticationType: "Forwarded"));
    }
    await next();
});

app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/whoami", (HttpContext ctx) => Results.Ok(ctx.User.Identity?.Name));
app.MapPost("/admin/reset-kiosk/{id}", (int id, HttpContext ctx) =>
        ctx.User.Identity?.Name == @"CORP\it-admin" ? Results.Ok(id) : Results.Forbid())
   .AddEndpointFilter(RequireAdminRequestHeader);

app.Run();

// Negotiate credentials are sent by the browser automatically, like a cookie, so state-changing
// endpoints require a custom header that a cross-site form cannot set (no CORS policy is configured).
static ValueTask<object?> RequireAdminRequestHeader(EndpointFilterInvocationContext ctx, EndpointFilterDelegate next) =>
    ctx.HttpContext.Request.Headers.ContainsKey("X-Kiosk-Admin-Request")
        ? next(ctx)
        : ValueTask.FromResult<object?>(Results.BadRequest());
