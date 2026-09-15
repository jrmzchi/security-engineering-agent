// Fixture: CSRF via a side-effect GET endpoint, "protected" by
// SameSite=Lax (DECEPTIVE — looks protected, is NOT)
//
// This is a false-negative-avoidance fixture, not a false-positive
// one: the point is that a reviewer relying on "the session cookie has
// SameSite set" as a blanket CSRF control must still flag this,
// because SameSite=Lax does not cover this specific request shape.
// See plays/web-security.md's "CSRF" section (the SameSite=Lax
// carve-out was added specifically because of this class of miss —
// see that play for the reasoning) and plays/finding-validation.md's
// note on the project's own bias toward under-reporting versus
// over-reporting.
//
// Expected review outcome: CONFIRMED CSRF (CWE-352), despite the
// cookie configuration looking like a mitigation at a glance.
//
// Attack path: this endpoint performs a state change (account
// deletion) on GET. The session cookie is configured with
// SameSite=Lax, which DOES still attach on a top-level cross-site GET
// navigation (e.g. an attacker page executing
// `window.location = 'https://victim/account/delete?confirm=true'` —
// note the value must be "true" for ASP.NET Core's bool model binder
// to accept it; "1" fails binding and the request 400s before reaching
// the vulnerable code, which would mask the finding without actually
// fixing anything). SameSite=Lax only withholds the cookie on things
// like cross-site XHR/fetch and sub-resource requests — not top-level
// navigation. No anti-forgery token is present, and the endpoint is
// GET rather than POST/DELETE, so the usual
// `[ValidateAntiForgeryToken]` convention was never applied to it
// either.

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

public class Startup
{
    public void ConfigureServices(IServiceCollection services)
    {
        services.ConfigureApplicationCookie(options =>
        {
            options.Cookie.HttpOnly = true;
            options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
            // Looks like a CSRF mitigation was considered - it was not
            // enough for the endpoint below.
            options.Cookie.SameSite = SameSiteMode.Lax;
        });
    }
}

[ApiController]
[Route("account")]
[Authorize]
public class AccountController : ControllerBase
{
    private readonly IAccountService _accounts;

    public AccountController(IAccountService accounts) => _accounts = accounts;

    // VULNERABLE despite SameSite=Lax: state-changing GET, no
    // anti-forgery token, no re-authentication step.
    [HttpGet("delete")]
    public IActionResult DeleteAccount([FromQuery] bool confirm)
    {
        if (!confirm)
        {
            return BadRequest("confirm=true required");
        }
        var userId = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        _accounts.Delete(userId);
        return Ok("account deleted");
    }
}
