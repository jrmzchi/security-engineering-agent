// Fixture: Cross-file Path Traversal (SAFE — canonicalized containment
// check) — part 1 of 3
//
// Expected review outcome: NO confirmed path traversal finding.
// Structurally identical to cross_file_path_traversal_unsafe/
// DownloadController.cs — the fix is entirely in PathHelper.cs.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("reports")]
public class DownloadController : ControllerBase
{
    private readonly Services.FileService _fileService;

    public DownloadController(Services.FileService fileService) => _fileService = fileService;

    [HttpGet("download")]
    public IActionResult Download([FromQuery] string reportName)
    {
        var bytes = _fileService.GetReportBytes(reportName);
        if (bytes is null)
        {
            return NotFound();
        }
        return File(bytes, "application/octet-stream", reportName);
    }
}
