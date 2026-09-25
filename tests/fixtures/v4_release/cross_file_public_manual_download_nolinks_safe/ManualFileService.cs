// Fixture: cross-file path traversal (SAFE), V4 release corpus row RV-37 (corpus revision 3) -- part 2 of 3
//
// See ManualDownloadController.cs and ManualPathHelper.cs.

namespace FixtureApp.Services;

public class ManualFileService
{
    private readonly Helpers.ManualPathHelper _paths;

    public ManualFileService(Helpers.ManualPathHelper paths) => _paths = paths;

    public (byte[] Bytes, string FileName)? GetManual(string manualName)
    {
        var path = _paths.ResolveManualPath(manualName);
        if (path is null || !File.Exists(path))
        {
            return null;
        }
        return (File.ReadAllBytes(path), Path.GetFileName(path));
    }
}
