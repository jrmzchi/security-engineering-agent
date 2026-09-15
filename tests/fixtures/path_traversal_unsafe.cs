// Fixture: Directory traversal (VULNERABLE)
//
// Expected review outcome: CONFIRMED HIGH/CRITICAL path traversal
// (CWE-22). See plays/file-security.md and references/aspnet-security.md.
//
// Attack path: `fileName` is attacker-controlled (a query string
// value), combined with Path.Combine (which does not prevent
// traversal), and used directly to open a file — a request for
// /files?fileName=../../appsettings.json escapes the intended
// directory.
//
// (An earlier version of this fixture took `fileName` from the route
// — `/files/{fileName}` — instead of the query string. ASP.NET Core's
// routing normalizes and single-segment-constrains route parameters,
// so neither an encoded nor a literal "../" survived to reach
// Path.Combine that way; the claimed attack path did not actually
// work. Query string values are not path-normalized, so this version
// does.)

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("files")]
public class FilesController : ControllerBase
{
    private readonly string _baseDir = "/var/app/uploads";

    [HttpGet]
    public IActionResult GetFile([FromQuery] string fileName)
    {
        // VULNERABLE: Path.Combine does not stop ../ sequences or an
        // absolute path from escaping _baseDir, and the resolved path
        // is never checked against it before opening the file.
        var path = Path.Combine(_baseDir, fileName);
        if (!System.IO.File.Exists(path))
        {
            return NotFound();
        }
        var bytes = System.IO.File.ReadAllBytes(path);
        return File(bytes, "application/octet-stream");
    }
}
