// Fixture: LDAPS login bind that accepts an empty password (DECEPTIVE -- VULNERABLE)
//
// Expected review outcome: CONFIRMED, CRITICAL authentication bypass
// (CWE-287; unauthenticated simple bind treated as a successful login).
// See plays/enterprise-identity-security.md, "Trusted, verified login result"
// (LDAP bind used as the login check).
//
// Why it is deceptive: the transport is LDAPS with certificate validation left
// on, and the username is escaped before it is used in the DN. Those are real
// controls, but they do not address the attack. A simple bind with a valid DN
// and an EMPTY password is an unauthenticated bind that AD accepts by default.
// Bind() returns without throwing, and the code reads that as "password
// correct". Submitting any existing username with an empty password signs in
// as that user.

using System.DirectoryServices.Protocols;
using System.Net;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace FixtureApp.Identity;

public sealed record LoginForm(string Username, string? Password);

[ApiController]
[Route("account")]
public class DirectoryLoginController : ControllerBase
{
    private const string DirectoryHost = "dc01.corp.example";

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromForm] LoginForm form)
    {
        var userDn = $"CN={Rfc4514.EscapeRdnValue(form.Username)},OU=Staff,DC=corp,DC=example";
        try
        {
            using var conn = new LdapConnection(new LdapDirectoryIdentifier(DirectoryHost, 636));
            conn.SessionOptions.SecureSocketLayer = true; // certificate validation left at its default
            conn.AuthType = AuthType.Basic;
            conn.Bind(new NetworkCredential(userDn, form.Password ?? "")); // succeeds for an empty password
        }
        catch (LdapException)
        {
            return Unauthorized();
        }

        var identity = new ClaimsIdentity(new[] { new Claim(ClaimTypes.Name, form.Username) },
            CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignInAsync(new ClaimsPrincipal(identity));
        return Ok();
    }
}

public static class Rfc4514
{
    public static string EscapeRdnValue(string value)
    {
        var escaped = value.Replace("\\", "\\\\").Replace(",", "\\,").Replace("+", "\\+")
            .Replace("\"", "\\\"").Replace("<", "\\<").Replace(">", "\\>").Replace(";", "\\;")
            .Replace("=", "\\=");
        if (escaped.StartsWith(' ') || escaped.StartsWith('#')) escaped = "\\" + escaped;
        if (escaped.EndsWith(' ')) escaped = escaped[..^1] + "\\ ";
        return escaped;
    }
}
