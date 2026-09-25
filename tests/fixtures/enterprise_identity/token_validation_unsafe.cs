// Fixture: Entra ID JWT bearer API with token validation switched off (VULNERABLE)
//
// Expected review outcome: CONFIRMED, CRITICAL authentication bypass
// (CWE-347 improper verification of cryptographic signature; CWE-287).
// See plays/enterprise-identity-security.md, "Trusted, verified login result".
//
// Attack path: any caller can mint a token with an arbitrary "oid"/"roles"
// payload and no valid signature. SignatureValidator hands the raw token back
// without checking it, and issuer and audience checks are off, so the API
// accepts it as a signed-in employee.

using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = builder.Configuration["AzureAd:Authority"];
        options.TokenValidationParameters = new TokenValidationParameters
        {
            // VULNERABLE: "tokens from other tenants kept failing" -- turned off
            ValidateIssuer = false,
            ValidateAudience = false,
            ValidateLifetime = true,
            // VULNERABLE: returns the token without verifying its signature
            SignatureValidator = (token, parameters) => new JsonWebToken(token),
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
