// Fixture: OIDC sign-in silently skipped when its configuration is missing (VULNERABLE)
//
// Expected review outcome: CONFIRMED, HIGH authentication bypass through
// missing configuration (CWE-1188 insecure default; CWE-306 missing
// authentication for a critical function).
// See plays/enterprise-identity-security.md, "Missing, invalid or stale
// identity configuration".
//
// Attack path: if a deployment omits the AzureAd section (a new environment,
// a renamed key, a failed secret-store mount), the app starts without any
// authentication or authorization. It then serves the HR case files to
// anonymous callers instead of refusing to start. When the configuration is
// present, access is limited to the HR case-worker group.

using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.Identity.Web;

var builder = WebApplication.CreateBuilder(args);
var azureAd = builder.Configuration.GetSection("AzureAd");
var identityConfigured = !string.IsNullOrEmpty(azureAd["ClientId"]);

if (identityConfigured)
{
    var hrCaseWorkersGroupId = builder.Configuration["Identity:HrCaseWorkersGroupId"];
    builder.Services
        .AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
        .AddMicrosoftIdentityWebApp(azureAd);
    builder.Services.AddAuthorization(o => o.FallbackPolicy = new Microsoft.AspNetCore.Authorization.AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .RequireClaim("groups", hrCaseWorkersGroupId!)
        .Build());
}
// VULNERABLE: no else -- "local dev convenience" leaves every endpoint anonymous

var app = builder.Build();
if (identityConfigured)
{
    app.UseAuthentication();
    app.UseAuthorization();
}

app.MapGet("/hr/cases", () => Results.Ok(new[] { "case-1041", "case-1042" }));

app.Run();
