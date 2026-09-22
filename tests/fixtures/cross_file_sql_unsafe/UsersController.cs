// Fixture: Cross-file SQL Injection (VULNERABLE) — part 1 of 3
//
// Expected review outcome: CONFIRMED CRITICAL/HIGH SQL Injection
// (CWE-89). See plays/data-security.md and plays/cross-file-data-flow.md
// — attacker-controlled input crosses two file boundaries
// (Controller -> Service -> Repository) before reaching the sink in
// UserRepository.cs; do not judge this file, or UserSearchService.cs,
// in isolation.
//
// Attack path starts here: `q` is an unauthenticated, attacker-
// controlled query-string value, passed through unmodified.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase
{
    private readonly UserSearchService _service;

    public UsersController(UserSearchService service) => _service = service;

    [HttpGet("search")]
    public IActionResult Search([FromQuery] string q)
    {
        // Step 1: attacker-controlled input enters here and is passed
        // through with no validation or encoding of its own — see
        // UserSearchService.cs for step 2.
        var results = _service.SearchUsers(q);
        return Ok(results);
    }
}
