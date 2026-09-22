// Fixture: Cross-file Path Traversal (VULNERABLE) — part 3 of 3 (the sink)
//
// See DownloadController.cs for the attack path's start and
// FileService.cs for the intermediate hop. This is where the
// three-file chain reaches a containment check that does not actually
// contain anything — see plays/file-security.md's canonicalization
// guidance for what this is missing.

namespace FixtureApp.Helpers;

public class PathHelper
{
    private readonly string _reportsDir = "/var/app/reports";

    public string? ResolveReportPath(string reportName)
    {
        // VULNERABLE: Path.Combine does not stop "../" sequences from
        // escaping _reportsDir, and — unlike the safe version — the
        // result is never canonicalized (Path.GetFullPath) and checked
        // against the intended base directory before use. A request
        // for ?reportName=../../../etc/passwd escapes the intended
        // directory.
        return Path.Combine(_reportsDir, reportName);
    }
}
