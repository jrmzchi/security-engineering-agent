// Fixture: directory lookup over LDAPS with an injected secret and escaped filter (SAFE)
//
// Expected review outcome: no confirmed finding.
// See plays/enterprise-identity-security.md, "Directory connection, service
// account and query safety".
//
// Why it is safe: LDAPS on 636 with the default server-certificate validation
// (no validation callback is installed); the bind credential comes from
// configuration bound to a secret store at deployment, not from source;
// the caller-supplied value is escaped per RFC 4515 before it enters the
// filter; the search is limited to one OU, two attributes and a size limit;
// missing options stop the request instead of binding without a password.

using System.DirectoryServices.Protocols;
using System.Net;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;

namespace FixtureApp.Identity;

public sealed class DirectoryOptions
{
    public string Host { get; set; } = "";
    public string BindDn { get; set; } = "";
    public string BindPassword { get; set; } = ""; // supplied by the secret store at deployment
    public string PeopleBase { get; set; } = "";
}

public static class LdapFilter
{
    // RFC 4515 section 3: escape \ * ( ) and NUL in an assertion value.
    public static string Escape(string value)
    {
        var sb = new StringBuilder(value.Length);
        foreach (var ch in value)
        {
            sb.Append(ch switch
            {
                '\\' => @"\5c",
                '*' => @"\2a",
                '(' => @"\28",
                ')' => @"\29",
                '\0' => @"\00",
                _ => ch.ToString(),
            });
        }
        return sb.ToString();
    }
}

[ApiController]
[Route("api/directory")]
[Authorize]
public class DirectoryLookupController : ControllerBase
{
    private readonly DirectoryOptions _options;

    public DirectoryLookupController(IOptions<DirectoryOptions> options)
    {
        _options = options.Value;
        if (string.IsNullOrEmpty(_options.Host) || string.IsNullOrEmpty(_options.BindDn)
            || string.IsNullOrEmpty(_options.BindPassword) || string.IsNullOrEmpty(_options.PeopleBase))
        {
            throw new InvalidOperationException("Directory options are not configured; refusing to query");
        }
    }

    [HttpGet("people")]
    public IActionResult Find([FromQuery] string name)
    {
        using var conn = new LdapConnection(new LdapDirectoryIdentifier(_options.Host, 636));
        conn.SessionOptions.SecureSocketLayer = true;
        conn.AuthType = AuthType.Basic;
        conn.Bind(new NetworkCredential(_options.BindDn, _options.BindPassword));

        var filter = "(&(objectClass=user)(displayName=" + LdapFilter.Escape(name) + "))";
        var request = new SearchRequest(_options.PeopleBase, filter, SearchScope.OneLevel, "mail", "telephoneNumber")
        {
            SizeLimit = 25,
        };
        var response = (SearchResponse)conn.SendRequest(request);

        var people = response.Entries.Cast<SearchResultEntry>()
            .Select(e => new { mail = e.Attributes["mail"]?[0], phone = e.Attributes["telephoneNumber"]?[0] });
        return Ok(people);
    }
}
