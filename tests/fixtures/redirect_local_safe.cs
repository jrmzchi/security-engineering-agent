// Fixture: Redirect restricted to a local path (SAFE)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to redirect_unvalidated_unsafe.cs — a reviewer
// must not flag this just because a query parameter reaches a
// redirect call.
//
// Why it's safe: LocalRedirect() throws if returnUrl is not a local
// path (not an absolute URL to another host), so an attacker-supplied
// external URL is rejected rather than redirected to. See
// references/aspnet-security.md's Redirects section.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[Route("account")]
public class AccountController : Controller
{
    [HttpPost("login")]
    public IActionResult Login(string username, string password, string returnUrl)
    {
        // (authentication happens here)

        // SAFE: LocalRedirect rejects any target that isn't a local path.
        if (string.IsNullOrEmpty(returnUrl) || !Url.IsLocalUrl(returnUrl))
        {
            return RedirectToAction("Index", "Home");
        }
        return LocalRedirect(returnUrl);
    }
}
