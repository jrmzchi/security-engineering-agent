// Fixture: cross-file path traversal (SAFE), V4 release corpus row RV-37 (corpus revision 3) -- part 3 of 3
//
// Why it's safe: Path.GetFullPath resolves "../" before the containment
// check, which compares against the base directory with a trailing
// separator (so a sibling like "/var/app/published-manuals_old" cannot
// pass); an empty name is refused, and no link or other reparse point is
// followed -- neither the file nor any directory from the base directory
// down to it (revision 2 checked only the file itself).

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
        if (!File.Exists(canonical) || (File.GetAttributes(canonical) & FileAttributes.ReparsePoint) != 0)
        {
            return null;
        }
        var baseDir = _manualsDir.TrimEnd(Path.DirectorySeparatorChar);
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
