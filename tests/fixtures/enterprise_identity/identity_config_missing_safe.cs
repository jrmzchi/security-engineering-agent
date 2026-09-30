// Fixture: OIDC sign-in whose missing or invalid configuration stops the app (SAFE)
//
// Expected review outcome: no confirmed finding.
// See plays/enterprise-identity-security.md, "Missing, invalid or stale
// identity configuration".
//
// Why it is safe: startup refuses to continue when the identity settings are
// absent, when the instance is not an https:// authority, or when the tenant
// is a multi-tenant alias (common / organizations / consumers) that would admit
// users of any tenant. A misconfigured deployment therefore fails closed.
// Access is limited to the HR case-worker group (a group object ID from
// configuration, not a secret). Keys are always taken from the provider's
// metadata; no signing key is copied into configuration.

using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Identity.Web;

var builder = WebApplication.CreateBuilder(args);
var azureAd = builder.Configuration.GetSection("AzureAd");

foreach (var key in new[] { "Instance", "TenantId", "ClientId" })
{
    if (string.IsNullOrWhiteSpace(azureAd[key]))
    {
        throw new InvalidOperationException($"AzureAd:{key} is not configured; refusing to start");
    }
}
if (!Uri.TryCreate(azureAd["Instance"], UriKind.Absolute, out var instance) || instance.Scheme != Uri.UriSchemeHttps)
{
    throw new InvalidOperationException("AzureAd:Instance must be an https:// authority; refusing to start");
}
if (new[] { "common", "organizations", "consumers" }.Contains(azureAd["TenantId"], StringComparer.OrdinalIgnoreCase))
{
    throw new InvalidOperationException("AzureAd:TenantId must be this organization's tenant; refusing to start");
}
var hrCaseWorkersGroupId = builder.Configuration["Identity:HrCaseWorkersGroupId"]
    ?? throw new InvalidOperationException("Identity:HrCaseWorkersGroupId is not configured; refusing to start");

builder.Services
    .AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApp(azureAd);
builder.Services.AddAuthorization(o => o.FallbackPolicy = new AuthorizationPolicyBuilder()
    .RequireAuthenticatedUser()
    .RequireClaim("groups", hrCaseWorkersGroupId)
    .Build());

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/hr/cases", () => Results.Ok(new[] { "case-1041", "case-1042" }));

app.Run();
