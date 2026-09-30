// Fixture: Entra ID JWT bearer API with explicit, correct validation (SAFE)
//
// Expected review outcome: no confirmed finding.
// See plays/enterprise-identity-security.md, "Trusted, verified login result".
//
// Why it is safe: signing keys come from the tenant's metadata (Authority,
// HTTPS); issuer is the single expected tenant; audience is this API's own
// App ID URI; lifetime is validated with a short clock skew. The custom
// TokenValidationParameters block TIGHTENS the defaults rather than
// relaxing them.

using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
var tenantId = builder.Configuration["AzureAd:TenantId"]
    ?? throw new InvalidOperationException("AzureAd:TenantId is not configured");
var audience = builder.Configuration["AzureAd:Audience"]
    ?? throw new InvalidOperationException("AzureAd:Audience is not configured");

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = $"https://login.microsoftonline.com/{tenantId}/v2.0";
        options.RequireHttpsMetadata = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = $"https://login.microsoftonline.com/{tenantId}/v2.0",
            ValidateAudience = true,
            ValidAudience = audience,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            RequireSignedTokens = true,
            ClockSkew = TimeSpan.FromMinutes(2),
        };
    });
builder.Services.AddAuthorization();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/api/timesheets/mine", (HttpContext ctx) =>
        Results.Ok(new { employee = ctx.User.FindFirst("oid")?.Value }))
   .RequireAuthorization();

app.Run();
