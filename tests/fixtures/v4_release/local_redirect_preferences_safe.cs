// Fixture: redirect restricted to a local path (SAFE), V4 release corpus row RV-20
//
// Expected review outcome: NO confirmed finding. False-positive-avoidance
// counterpart to redirect_unvalidated_unsafe.cs -- a reviewer must not flag
// this just because a request parameter reaches a redirect call.
//
// Why it's safe: a non-local or empty returnUrl never reaches the redirect
// (Url.IsLocalUrl), and LocalRedirect() itself refuses any target that is
// not a local path. The action only stores a display-language preference
// chosen from a fixed allowlist, grants nothing, and is protected by an
// antiforgery token.
//
// Replaces tests/fixtures/redirect_local_safe.cs for the V4 release corpus
// only: that fixture's Login action accepts a username and password and,
// once its "(authentication happens here)" placeholder comment is stripped
// for review, verifies nothing. See tests/validation/v4-release-corpus.md.

using Microsoft.AspNetCore.Localization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[Route("preferences")]
public class PreferencesController : Controller
{
    private static readonly HashSet<string> SupportedCultures = new(StringComparer.Ordinal)
    {
        "en-US", "fr-FR", "de-DE",
    };

    [HttpPost("language")]
    [ValidateAntiForgeryToken]
    public IActionResult SetLanguage(string culture, string returnUrl)
    {
        if (string.IsNullOrEmpty(culture) || !SupportedCultures.Contains(culture))
        {
            return BadRequest();
        }
        Response.Cookies.Append(
            CookieRequestCultureProvider.DefaultCookieName,
            CookieRequestCultureProvider.MakeCookieValue(new RequestCulture(culture)),
            new CookieOptions { Secure = true, SameSite = SameSiteMode.Lax, MaxAge = TimeSpan.FromDays(365) });

        if (string.IsNullOrEmpty(returnUrl) || !Url.IsLocalUrl(returnUrl))
        {
            return RedirectToAction("Index", "Home");
        }
        return LocalRedirect(returnUrl);
    }
}
