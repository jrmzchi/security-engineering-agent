using Microsoft.AspNetCore.Authentication.JwtBearer;

var builder = WebApplication.CreateBuilder(args);

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = builder.Configuration["Auth:Authority"];
        options.Audience = "orders-api";
    });
builder.Services.AddAuthorization();
builder.Services.AddSingleton<OrderStore>();

var app = builder.Build();

app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();

app.MapPost("/orders", async (HttpContext ctx, OrderStore store, OrderRequest request) =>
{
    var id = await store.CreateAsync(ctx.User.FindFirst("sub")!.Value, request.Sku, request.Quantity);
    return Results.Created($"/orders/{id}", new { id });
}).RequireAuthorization();

app.Run();

public sealed record OrderRequest(string Sku, int Quantity);
