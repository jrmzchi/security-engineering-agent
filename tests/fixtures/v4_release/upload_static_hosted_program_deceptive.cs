// Fixture (V4 release corpus only, row RV-29): upload into a directory the
// application itself serves as static content -- the self-contained V4
// replacement for upload_webroot_content_disposition_deceptive.cs (DECEPTIVE:
// the download endpoint looks protected by Content-Disposition, but the
// uploaded file is also reachable directly through static-file serving).
//
// Why a V4 replacement exists: the V3 fixture asserts in comments only that
// wwwroot/uploads is served by UseStaticFiles(); its code contains no hosting
// configuration. With comments stripped, a review that assumes no control or
// execution path the case does not show (plays/finding-validation.md) cannot
// establish the static-serving step, so the stored-XSS impact cannot be
// CONFIRMED from that file. This file is a complete single-file ASP.NET Core
// app (a Program.cs with top-level statements) in which the hosting path is
// code: UploadStorage.Directory is both the directory UploadController writes
// into and the PhysicalFileProvider that UseStaticFiles() publishes under
// UploadStorage.RequestPath ("/uploads"), with the default extension-based
// content types (".html" -> "text/html").
//
// Expected review outcome (tests/validation/v4-release-corpus.md): CONFIRMED,
// three separate findings --
//   1. path traversal on upload (arbitrary file write): the client-supplied
//      IFormFile.FileName is combined into the destination path unchecked;
//   2. path traversal on download (arbitrary file read): the query parameter
//      "name" is combined into the read path unchecked;
//   3. unrestricted upload -> stored XSS on the application's own origin: an
//      uploaded "x.html" is written into UploadStorage.Directory and served
//      inline as text/html at GET /uploads/x.html by the static-file
//      middleware below, which never runs DownloadController, so its
//      Content-Disposition: attachment header never applies.

using FixtureApp;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();

var app = builder.Build();

Directory.CreateDirectory(UploadStorage.Directory);
app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new PhysicalFileProvider(UploadStorage.Directory),
    RequestPath = UploadStorage.RequestPath,
    ContentTypeProvider = new FileExtensionContentTypeProvider(),
});

app.MapControllers();
app.Run();

namespace FixtureApp
{
    [ApiController]
    [Route("upload")]
    public class UploadController : ControllerBase
    {
        [HttpPost]
        public async Task<IActionResult> Upload(IFormFile file)
        {
            var path = Path.Combine(UploadStorage.Directory, file.FileName);
            await using var stream = System.IO.File.Create(path);
            await file.CopyToAsync(stream);
            return Ok(new { url = $"{UploadStorage.RequestPath}/{file.FileName}" });
        }
    }

    public static class UploadStorage
    {
        public static readonly string Directory =
            Path.Combine(AppContext.BaseDirectory, "wwwroot", "uploads");

        public const string RequestPath = "/uploads";
    }

    [ApiController]
    [Route("download")]
    public class DownloadController : ControllerBase
    {
        [HttpGet]
        public IActionResult Download([FromQuery] string name)
        {
            var path = Path.Combine(UploadStorage.Directory, name);
            var bytes = System.IO.File.ReadAllBytes(path);
            Response.Headers.Append("Content-Disposition", $"attachment; filename=\"{name}\"");
            return File(bytes, "application/octet-stream");
        }
    }
}
