// Fixture: directory lookup over plain LDAP with an embedded service account (VULNERABLE)
//
// Expected review outcome: CONFIRMED, 3 findings --
//   (1) HIGH cleartext credential transmission: simple (Basic) bind on port
//       389 with no TLS sends the service-account password in cleartext (CWE-319);
//   (2) HIGH hardcoded service-account credential (CWE-798);
//   (3) HIGH LDAP injection: the search filter is built by concatenating the
//       caller-supplied name (CWE-90).
// See plays/enterprise-identity-security.md, "Directory connection, service
// account and query safety", plays/secrets-security.md and plays/code-review.md.
//
// Attack path (3): name = "*)(objectClass=*" widens the filter and returns
// every directory object. The endpoint then discloses their mail and phone
// attributes to any signed-in caller.
//
// Meta-note: the account name, host and password below are synthetic and not
// provisioned anywhere.

using System.DirectoryServices.Protocols;
using System.Net;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Identity;

[ApiController]
[Route("api/directory")]
[Authorize]
public class DirectoryLookupController : ControllerBase
{
    private const string BindUser = "CN=svc-intranet-lookup,OU=Service Accounts,DC=corp,DC=example";
    private const string BindPassword = "Wq7!rTz2-Ldp-9vKm"; // VULNERABLE: hardcoded

    [HttpGet("people")]
    public IActionResult Find([FromQuery] string name)
    {
        // VULNERABLE: plain LDAP (389), Basic bind, no TLS
        using var conn = new LdapConnection(new LdapDirectoryIdentifier("dc01.corp.example", 389));
        conn.AuthType = AuthType.Basic;
        conn.Bind(new NetworkCredential(BindUser, BindPassword));

        // VULNERABLE: filter built by string concatenation
        var filter = "(&(objectClass=user)(displayName=" + name + "))";
        var request = new SearchRequest("DC=corp,DC=example", filter, SearchScope.Subtree, "mail", "telephoneNumber");
        var response = (SearchResponse)conn.SendRequest(request);

        var people = response.Entries.Cast<SearchResultEntry>()
            .Select(e => new { mail = e.Attributes["mail"]?[0], phone = e.Attributes["telephoneNumber"]?[0] });
        return Ok(people);
    }
}
