// Fixture: Windows Integrated Authentication with a SID-based admin check (SAFE)
//
// Expected review outcome: no confirmed finding.
// See plays/enterprise-identity-security.md, "Trusted, verified login result"
// and "Authorization after login".
//
// Why it is safe: the identity comes only from the server-side Negotiate
// handshake (HttpContext.User). No request header is consulted. Every
// endpoint requires an authenticated user through the fallback policy. The
// admin action checks membership of a group by its SID, not by a
// display-name string. Because the browser sends Negotiate credentials
// automatically, the state-changing admin action also requires a custom request
// header that a cross-site form cannot set (CSRF). The group SID is
// configuration, not a secret.

using System.Security.Principal;
using Microsoft.AspNetCore.Authentication.Negotiate;

var builder = WebApplication.CreateBuilder(args);
var kioskAdminsSid = builder.Configuration["Identity:KioskAdminsGroupSid"]
    ?? throw new InvalidOperationException("Identity:KioskAdminsGroupSid is not configured");

builder.Services.AddAuthentication(NegotiateDefaults.AuthenticationScheme).AddNegotiate();
builder.Services.AddAuthorization(o =>
{
    o.FallbackPolicy = o.DefaultPolicy; // every endpoint requires an authenticated user
    o.AddPolicy("KioskAdmins", p => p.RequireAssertion(ctx =>
        ctx.User.Identity is WindowsIdentity wi
        && wi.Groups is not null
        && wi.Groups.Contains(new SecurityIdentifier(kioskAdminsSid))));
});

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/whoami", (HttpContext ctx) => Results.Ok(ctx.User.Identity?.Name));
app.MapPost("/admin/reset-kiosk/{id}", (int id) => Results.Ok(id))
   .RequireAuthorization("KioskAdmins")
   .AddEndpointFilter(RequireAdminRequestHeader);

app.Run();

// Negotiate credentials are sent by the browser automatically, like a cookie, so state-changing
// endpoints require a custom header that a cross-site form cannot set (no CORS policy is configured).
static ValueTask<object?> RequireAdminRequestHeader(EndpointFilterInvocationContext ctx, EndpointFilterDelegate next) =>
    ctx.HttpContext.Request.Headers.ContainsKey("X-Kiosk-Admin-Request")
        ? next(ctx)
        : ValueTask.FromResult<object?>(Results.BadRequest());
