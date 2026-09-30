// Fixture: directory traversal (SAFE -- resolved-path containment check), V4 release corpus row RV-24
//
// Expected review outcome: NO confirmed finding. False-positive-avoidance
// counterpart to path_traversal_unsafe.cs -- a reviewer must not flag this
// just because a query parameter reaches a file-open call.
//
// Why it's safe: the combined path is resolved with Path.GetFullPath and
// must still lie inside the base directory (compared with a trailing
// separator) before anything is opened; a link or other reparse point is
// refused. The base directory holds the product's published manuals,
// shipped with the deployment: public content, so serving it without
// authentication is correct.
//
// Replaces tests/fixtures/path_traversal_safe.cs for the V4 release corpus
// only: that fixture serves an "uploads" directory (user-supplied content)
// to any unauthenticated caller. See tests/validation/v4-release-corpus.md.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("manuals")]
public class PublicManualsController : ControllerBase
{
    private readonly string _baseDir = Path.GetFullPath("/var/app/published-manuals");

    [HttpGet]
    public IActionResult GetManual([FromQuery] string fileName)
    {
        if (string.IsNullOrEmpty(fileName))
        {
            return BadRequest();
        }
        var resolved = Path.GetFullPath(Path.Combine(_baseDir, fileName));
        if (!resolved.StartsWith(_baseDir + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        {
            return Forbid();
        }
        if (!System.IO.File.Exists(resolved)
            || (System.IO.File.GetAttributes(resolved) & FileAttributes.ReparsePoint) != 0)
        {
            return NotFound();
        }
        return PhysicalFile(resolved, "application/pdf", Path.GetFileName(resolved));
    }
}
