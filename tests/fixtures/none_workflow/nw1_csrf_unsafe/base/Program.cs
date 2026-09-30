using Microsoft.AspNetCore.Authentication.Cookies;

var builder = WebApplication.CreateBuilder(args);

builder.Services
    .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.LoginPath = "/login";
        // The partner portal embeds the account page, so the cookie must travel cross-site.
        options.Cookie.SameSite = SameSiteMode.None;
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    });
builder.Services.AddAuthorization();
builder.Services.AddSingleton<AccountStore>();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

// Permanetly deletes the signed-in user's account.
app.MapPost("/account/delete", async (HttpContext ctx, AccountStore store) =>
{
    var userId = ctx.User.FindFirst("sub")!.Value;
    await store.DeleteAsync(userId);
    return Results.Ok();
}).RequireAuthorization();

app.Run();
