// Fixture: Cross-file Object Authorization / BOLA (VULNERABLE) — part 1 of 3
//
// Expected review outcome: CONFIRMED HIGH BOLA/IDOR (CWE-639). See
// plays/authorization.md and plays/cross-file-data-flow.md — this
// test proves authentication != object authorization: [Authorize]
// only confirms *a* user is logged in, not that this user owns
// *this* report. Object-level authorization is missing across the
// whole Controller -> Service -> Repository chain; do not judge this
// file, or ReportService.cs, in isolation. See ReportService.cs for
// where the missing check should have been.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("api/reports")]
[Authorize]
public class ReportsController : ControllerBase
{
    private readonly Services.ReportService _reportService;

    public ReportsController(Services.ReportService reportService) => _reportService = reportService;

    [HttpGet("{reportId}")]
    public IActionResult GetReport(int reportId)
    {
        // Step 1: [Authorize] confirms the caller is authenticated,
        // nothing more — reportId is still attacker-controlled and
        // sequential (see ReportRepository.cs). See ReportService.cs
        // for step 2.
        var report = _reportService.GetReport(reportId);
        if (report is null)
        {
            return NotFound();
        }
        return Ok(report);
    }
}
