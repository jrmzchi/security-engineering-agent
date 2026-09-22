// Fixture: Cross-file Path Traversal (SAFE — canonicalized containment
// check) — part 2 of 3
//
// Structurally identical to cross_file_path_traversal_unsafe/
// FileService.cs — the fix is entirely in PathHelper.cs.

namespace FixtureApp.Services;

public class FileService
{
    private readonly Helpers.PathHelper _pathHelper;

    public FileService(Helpers.PathHelper pathHelper) => _pathHelper = pathHelper;

    public byte[]? GetReportBytes(string reportName)
    {
        var path = _pathHelper.ResolveReportPath(reportName);
        if (path is null || !File.Exists(path))
        {
            return null;
        }
        return File.ReadAllBytes(path);
    }
}
