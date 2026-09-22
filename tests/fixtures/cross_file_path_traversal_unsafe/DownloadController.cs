// Fixture: Cross-file Path Traversal (VULNERABLE) — part 1 of 3
//
// Expected review outcome: CONFIRMED HIGH/CRITICAL path traversal
// (CWE-22). See plays/file-security.md and
// plays/cross-file-data-flow.md — attacker-controlled input crosses
// two file boundaries (Controller -> FileService -> PathHelper) before
// reaching the containment check that fails to contain it; do not
// judge this file, or FileService.cs, in isolation. See
// PathHelper.cs for the actual defect.
//
// Attack path starts here: `reportName` is a query-string value (not
// a route parameter — ASP.NET Core route-parameter normalization does
// not apply to query strings, so an encoded or literal "../" survives
// to the sink).

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
        // Step 1: attacker-controlled input enters here and is passed
        // through unmodified — see FileService.cs for step 2.
        var bytes = _fileService.GetReportBytes(reportName);
        if (bytes is null)
        {
            return NotFound();
        }
        return File(bytes, "application/octet-stream", reportName);
    }
}
