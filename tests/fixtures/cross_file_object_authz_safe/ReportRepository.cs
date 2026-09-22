// Fixture: Cross-file Object Authorization / BOLA (SAFE — ownership
// check enforced) — part 3 of 3
//
// Structurally identical to cross_file_object_authz_unsafe/
// ReportRepository.cs, including the still-sequential IDs — the fix
// is entirely the ownership check in ReportService.cs, not making IDs
// unguessable. See plays/authorization.md: predictable IDs are a
// severity amplifier for a missing check, not a vulnerability to fix
// by obscuring the ID.

namespace FixtureApp.Repositories;

public class ReportRepository
{
    private readonly List<Models.Report> _reports;

    public ReportRepository(List<Models.Report> reports) => _reports = reports;

    public Models.Report? FindById(int reportId)
    {
        return _reports.FirstOrDefault(r => r.Id == reportId);
    }
}
