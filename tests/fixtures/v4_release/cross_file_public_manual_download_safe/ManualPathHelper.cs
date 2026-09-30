// Fixture: cross-file path traversal (SAFE), V4 release corpus row RV-37 -- part 3 of 3
//
// Why it's safe: Path.GetFullPath resolves "../" before the containment
// check, which compares against the base directory with a trailing
// separator (so a sibling like "/var/app/published-manuals_old" cannot
// pass); an empty name, or a link or other reparse point, is refused.

namespace FixtureApp.Helpers;

public class ManualPathHelper
{
    private readonly string _manualsDir = Path.GetFullPath("/var/app/published-manuals") + Path.DirectorySeparatorChar;

    public string? ResolveManualPath(string manualName)
    {
        if (string.IsNullOrEmpty(manualName))
        {
            return null;
        }
        var canonical = Path.GetFullPath(Path.Combine(_manualsDir, manualName));
        if (!canonical.StartsWith(_manualsDir, StringComparison.Ordinal))
        {
            return null;
        }
        if (File.Exists(canonical) && (File.GetAttributes(canonical) & FileAttributes.ReparsePoint) != 0)
        {
            return null;
        }
        return canonical;
    }
}
