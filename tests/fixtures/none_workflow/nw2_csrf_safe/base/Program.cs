using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication.Cookies;

var builder = WebApplication.CreateBuilder(args);

builder.Services
    .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.LoginPath = "/login";
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
        options.Cookie.HttpOnly = true;
    });
builder.Services.AddAuthorization();
// The account page sends the request token in this header; browsers cannot set it on a cross-site form post.
builder.Services.AddAntiforgery(options => options.HeaderName = "X-CSRF-TOKEN");
builder.Services.AddSingleton<AccountStore>();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

// Permanetly deletes the signed-in user's account.
app.MapPost("/account/delete", async (HttpContext ctx, AccountStore store, IAntiforgery antiforgery) =>
{
    if (!await antiforgery.IsRequestValidAsync(ctx))
    {
        return Results.BadRequest();
    }
    var userId = ctx.User.FindFirst("sub")!.Value;
    await store.DeleteAsync(userId);
    return Results.Ok();
}).RequireAuthorization();

app.Run();
