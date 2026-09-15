// Fixture: Open redirect via unvalidated returnUrl (VULNERABLE)
//
// Expected review outcome: CONFIRMED MEDIUM/HIGH open redirect
// (CWE-601). See plays/web-security.md's "Open redirect" section.
// Severity is elevated when chained with an OAuth/login flow, as here.
//
// Attack path: `returnUrl` is attacker-controlled (query parameter),
// passed directly to Redirect() with no validation — an attacker sends
// a victim a link like
// /account/login?returnUrl=https://evil.example/phish, the victim logs
// in on the legitimate site (which they trust), and is then redirected
// to the attacker's phishing page, which can now claim to be a
// "next step" the victim already trusts.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[Route("account")]
public class AccountController : Controller
{
    [HttpPost("login")]
    public IActionResult Login(string username, string password, string returnUrl)
    {
        // (authentication happens here)

        // VULNERABLE: returnUrl is redirected to as-is, with no check
        // that it stays on this site.
        return Redirect(returnUrl);
    }
}
