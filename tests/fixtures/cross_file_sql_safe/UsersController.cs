// Fixture: Cross-file SQL Injection (SAFE — parameterized query) — part 1 of 3
//
// Expected review outcome: NO confirmed SQL Injection finding.
// False-positive-avoidance counterpart to cross_file_sql_unsafe/ — a
// reviewer must not flag this just because raw ADO.NET is used and
// input crosses multiple files; see UserRepository.cs for why it's
// actually safe (parameterization, not the multi-file structure
// itself).
//
// Structurally identical to cross_file_sql_unsafe/UsersController.cs
// — this file's role in the chain does not change between the unsafe
// and safe versions.

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
        var results = _service.SearchUsers(q);
        return Ok(results);
    }
}
