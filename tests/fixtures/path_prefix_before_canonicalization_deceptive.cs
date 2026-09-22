// Fixture: Path traversal "protected" by a prefix check performed
// BEFORE canonicalization (DECEPTIVE — looks protected, is NOT)
//
// This is a false-negative-avoidance fixture, not a false-positive
// one, and is specifically designed to exercise
// plays/adversarial-validation.md's technique 6 (encoding/
// canonicalization differences) — a reviewer that sees "there's a
// StartsWith containment check right here" and moves on without
// actually tracing what value that check runs against must still flag
// this. Expected adversarialValidation result if this checklist is
// applied: BYPASS_FOUND (see plays/adversarial-validation.md's
// "Structured result metadata").
//
// Expected review outcome: CONFIRMED HIGH/CRITICAL path traversal
// (CWE-22), despite the containment check present in the code.
//
// Attack path: the check below runs `StartsWith` on the *raw,
// uncanonicalized* combined path — not on a resolved absolute path.
// A request for
// ?reportName=../../../../etc/passwd
// produces the combined string
// "/var/app/reports/../../../../etc/passwd"
// which STILL starts with the literal characters "/var/app/reports",
// so the check passes. Only after the check does the runtime resolve
// the "../" segments when the file is actually opened, at which point
// containment has already been (incorrectly) confirmed.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("reports")]
public class DownloadController : ControllerBase
{
    private readonly PathHelper _pathHelper;

    public DownloadController(PathHelper pathHelper) => _pathHelper = pathHelper;

    [HttpGet("download")]
    public IActionResult Download([FromQuery] string reportName)
    {
        var path = _pathHelper.ResolveReportPath(reportName);
        if (path is null || !System.IO.File.Exists(path))
        {
            return NotFound();
        }
        return File(System.IO.File.ReadAllBytes(path), "application/octet-stream");
    }
}

public class PathHelper
{
    private readonly string _reportsDir = "/var/app/reports";

    public string? ResolveReportPath(string reportName)
    {
        var combined = Path.Combine(_reportsDir, reportName);

        // DECEPTIVE: this looks like a containment check, and would
        // correctly reject an absolute path substitution like
        // "/etc/passwd" — but it runs against the *uncanonicalized*
        // string, which still starts with _reportsDir even when "../"
        // segments will later walk it outside that directory.
        if (!combined.StartsWith(_reportsDir, StringComparison.Ordinal))
        {
            return null;
        }

        return combined;
    }
}
