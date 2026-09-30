// Fixture: cross-file path traversal (SAFE), V4 release corpus row RV-37 (corpus revision 3) -- part 1 of 3
//
// Expected review outcome: NO confirmed finding. See ManualPathHelper.cs:
// the requested name is canonicalized and contained two layers down. The
// files are the product's published manuals (public content shipped with
// the deployment), so no authentication is needed. Replaces
// tests/fixtures/cross_file_path_traversal_safe/ for the V4 release corpus
// only (that fixture serves a "reports" directory to unauthenticated
// callers). See tests/validation/v4-release-corpus.md.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("manuals")]
public class ManualDownloadController : ControllerBase
{
    private readonly Services.ManualFileService _files;

    public ManualDownloadController(Services.ManualFileService files) => _files = files;

    [HttpGet("download")]
    public IActionResult Download([FromQuery] string manualName)
    {
        var manual = _files.GetManual(manualName);
        if (manual is null)
        {
            return NotFound();
        }
        return File(manual.Value.Bytes, "application/pdf", manual.Value.FileName);
    }
}
