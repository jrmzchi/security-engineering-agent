// Fixture: Cross-file Path Traversal (SAFE — canonicalized containment
// check) — part 3 of 3
//
// Why it's safe: the combined path is canonicalized with
// Path.GetFullPath *before* the containment check, and the check
// compares against the base directory with a trailing separator — so
// neither "../" traversal nor a sibling-directory name that merely
// starts with the same characters (e.g. "/var/app/reports_secret")
// can pass. See plays/file-security.md's canonicalization guidance —
// a naive StartsWith check on the *uncanonicalized* string, or one
// without the trailing separator, would not actually be safe. (Not
// covered by this fixture: a symlink placed inside the base directory
// pointing outside it — GetFullPath does not resolve symlinks. See
// plays/file-security.md's note on that as a separate, additional
// consideration; it is out of scope for what this fixture is
// demonstrating.)

namespace FixtureApp.Helpers;

public class PathHelper
{
    private readonly string _reportsDir = Path.GetFullPath("/var/app/reports") + Path.DirectorySeparatorChar;

    public string? ResolveReportPath(string reportName)
    {
        // SAFE: resolve to an absolute, canonical path first, then
        // confirm it is actually contained within _reportsDir.
        var combined = Path.Combine(_reportsDir, reportName);
        var canonical = Path.GetFullPath(combined);
        if (!canonical.StartsWith(_reportsDir, StringComparison.Ordinal))
        {
            return null;
        }
        return canonical;
    }
}
