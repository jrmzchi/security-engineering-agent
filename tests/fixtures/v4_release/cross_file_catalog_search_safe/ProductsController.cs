// Fixture: cross-file SQL (SAFE -- parameterized), V4 release corpus row RV-35 -- part 1 of 3
//
// Expected review outcome: NO confirmed finding. See ProductRepository.cs:
// the query is bound as a SQL parameter three layers down. The endpoint is
// a public catalog search returning only published product fields, so no
// authentication is needed. Replaces tests/fixtures/cross_file_sql_safe/
// for the V4 release corpus only (that fixture returns users' e-mail
// addresses to unauthenticated callers). See
// tests/validation/v4-release-corpus.md.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("api/catalog")]
public class ProductsController : ControllerBase
{
    private readonly Services.ProductSearchService _service;

    public ProductsController(Services.ProductSearchService service) => _service = service;

    [HttpGet("search")]
    public IActionResult Search([FromQuery] string q)
    {
        if (string.IsNullOrWhiteSpace(q) || q.Length > 100)
        {
            return BadRequest();
        }
        return Ok(_service.SearchProducts(q));
    }
}
