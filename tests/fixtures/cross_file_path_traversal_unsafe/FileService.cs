// Fixture: Cross-file Path Traversal (VULNERABLE) — part 2 of 3
//
// See DownloadController.cs for the attack path's start and
// PathHelper.cs for the sink. This file adds no validation of its
// own — `reportName` passes through unchanged into the path
// resolution step.

namespace FixtureApp.Services;

public class FileService
{
    private readonly Helpers.PathHelper _pathHelper;

    public FileService(Helpers.PathHelper pathHelper) => _pathHelper = pathHelper;

    public byte[]? GetReportBytes(string reportName)
    {
        // Step 2: no validation here — resolution and containment are
        // (supposedly) PathHelper's job. See PathHelper.cs.
        var path = _pathHelper.ResolveReportPath(reportName);
        if (path is null || !File.Exists(path))
        {
            return null;
        }
        return File.ReadAllBytes(path);
    }
}
