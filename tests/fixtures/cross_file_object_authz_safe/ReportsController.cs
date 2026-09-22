// Fixture: Cross-file Object Authorization / BOLA (SAFE — ownership
// check enforced) — part 1 of 3
//
// Expected review outcome: NO confirmed BOLA/IDOR finding. A reviewer
// must not flag this just because reportId is a route/query parameter
// on an [Authorize]-protected endpoint — see ReportService.cs for the
// actual ownership check.

using System.Security.Claims;
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
        var currentUserId = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        // The current caller's identity is passed down explicitly —
        // see ReportService.cs for where it's actually enforced.
        var report = _reportService.GetReport(reportId, currentUserId);
        if (report is null)
        {
            return NotFound();
        }
        return Ok(report);
    }
}
