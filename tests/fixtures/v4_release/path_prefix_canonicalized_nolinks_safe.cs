// Fixture: path containment check, canonicalized correctly (SAFE), V4 release corpus row RV-26
//
// Expected review outcome: NO confirmed path traversal finding. The
// control-holds counterpart to path_prefix_before_canonicalization_deceptive.cs
// (the same StartsWith-on-a-combined-path shape, but checked on the
// canonical path).
//
// Why it's safe: Path.GetFullPath resolves "../" before the containment
// check; the check compares against the base directory with a trailing
// separator, so a sibling such as "/var/app/reports_other" cannot pass; and
// no link or other reparse point is followed, either as the file itself or
// as any directory between the base directory and the file, so the result
// does not depend on the directory's contents.
//
// Replaces tests/fixtures/path_prefix_after_canonicalization_safe.cs for the
// V4 release corpus only: that fixture leaves symlinks inside the base
// directory out of scope, an assumption about the environment rather than
// something the fixture shows. See tests/validation/v4-release-corpus.md.

namespace FixtureApp.Helpers;

public class PathHelper
{
    private readonly string _reportsDir =
        Path.GetFullPath("/var/app/reports") + Path.DirectorySeparatorChar;

    public string? ResolveReportPath(string reportName)
    {
        if (string.IsNullOrEmpty(reportName))
        {
            return null;
        }
        var canonical = Path.GetFullPath(Path.Combine(_reportsDir, reportName));
        if (!canonical.StartsWith(_reportsDir, StringComparison.Ordinal))
        {
            return null;
        }
        if (!File.Exists(canonical) || (File.GetAttributes(canonical) & FileAttributes.ReparsePoint) != 0)
        {
            return null;
        }
        var baseDir = _reportsDir.TrimEnd(Path.DirectorySeparatorChar);
        for (var dir = Path.GetDirectoryName(canonical); dir is not null && dir.Length >= baseDir.Length; dir = Path.GetDirectoryName(dir))
        {
            if ((File.GetAttributes(dir) & FileAttributes.ReparsePoint) != 0)
            {
                return null;
            }
        }
        return canonical;
    }
}
