// Fixture: Path traversal containment check, canonicalized correctly
// (SAFE — the checklist must not manufacture a bypass here)
//
// This is the control-holds counterpart to
// path_prefix_before_canonicalization_deceptive.cs — structurally the
// same shape (a StartsWith containment check on a combined path), but
// the check here runs against a canonicalized absolute path, so it
// actually works. Exists specifically so
// plays/adversarial-validation.md's checklist has a negative case to
// exercise: applying the same techniques (alternate representations,
// encoding, canonicalization tricks) must produce
// adversarialValidation result CONTROL_HOLDS, not a fabricated
// BYPASS_FOUND — see that play's "Findings this checklist genuinely
// doesn't apply to" is NOT the reason this passes (this finding IS on
// the trigger list, since it's exactly the SSRF/path-canonicalization
// case named there); it passes because the control genuinely holds
// under scrutiny, not because the checklist wasn't applied.
//
// Expected review outcome: NO confirmed path traversal finding.
//
// Why it's safe: Path.GetFullPath resolves "../" segments and any
// symlink-independent redundancy in the path *before* the containment
// check runs, and the check compares against _reportsDir with a
// trailing directory separator (preventing a sibling directory like
// "/var/app/reports_other" from passing a naive prefix match). A
// request for ?reportName=../../../../etc/passwd resolves to
// "/etc/passwd", which does not start with "/var/app/reports/" — the
// check correctly rejects it. (Not covered by this fixture: a symlink
// placed inside the base directory pointing outside it — GetFullPath
// does not resolve symlinks. See plays/file-security.md's note on
// that as a separate, additional consideration; it is out of scope
// for what this fixture is demonstrating.)

namespace FixtureApp.Helpers;

public class PathHelper
{
    private readonly string _reportsDir =
        Path.GetFullPath("/var/app/reports") + Path.DirectorySeparatorChar;

    public string? ResolveReportPath(string reportName)
    {
        var combined = Path.Combine(_reportsDir, reportName);
        var canonical = Path.GetFullPath(combined);

        // SAFE: containment check runs against the canonicalized
        // absolute path, with a trailing separator on the base
        // directory to prevent a same-prefix sibling directory from
        // passing.
        if (!canonical.StartsWith(_reportsDir, StringComparison.Ordinal))
        {
            return null;
        }

        return canonical;
    }
}
