// Fixture: Directory traversal (SAFE — resolved-path containment check)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to path_traversal_unsafe.cs — a reviewer must
// not flag this just because a query parameter reaches a file-open
// call.
//
// Why it's safe: the combined path is resolved with Path.GetFullPath
// and explicitly checked to still be inside the intended base
// directory before being opened. A traversal or absolute-path attempt
// fails the containment check instead of escaping it. (Not covered by
// this fixture: a symlink placed inside the base directory pointing
// outside it — GetFullPath does not resolve symlinks. See
// plays/file-security.md's note on that as a separate, additional
// consideration; it is out of scope for what this fixture is
// demonstrating, which is the "../" / absolute-path containment check
// specifically.)

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("files")]
public class FilesController : ControllerBase
{
    private readonly string _baseDir = Path.GetFullPath("/var/app/uploads");

    [HttpGet]
    public IActionResult GetFile([FromQuery] string fileName)
    {
        var combined = Path.Combine(_baseDir, fileName);
        var resolved = Path.GetFullPath(combined);

        // SAFE: containment check runs on the fully resolved path.
        if (!resolved.StartsWith(_baseDir + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        {
            return Forbid();
        }
        if (!System.IO.File.Exists(resolved))
        {
            return NotFound();
        }
        var bytes = System.IO.File.ReadAllBytes(resolved);
        return File(bytes, "application/octet-stream");
    }
}
