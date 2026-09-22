// Fixture: Cross-file Object Authorization / BOLA (VULNERABLE) — part 3 of 3
//
// See ReportsController.cs for the attack path's start and
// ReportService.cs for the missing check. `Id` is a sequential
// database identity column — predictable/enumerable, which amplifies
// (but does not by itself cause) the missing-authorization finding
// above; see plays/authorization.md's note that predictable IDs are a
// severity amplifier, not a separate vulnerability on their own. This
// fixture pair is also the component findings used in
// tests/validation/v3-attack-chain-test-cases.md's positive chain
// example (predictable ID + missing object authorization = any
// authenticated user can enumerate every report in the system).

namespace FixtureApp.Repositories;

public class ReportRepository
{
    private readonly List<Models.Report> _reports;

    public ReportRepository(List<Models.Report> reports) => _reports = reports;

    public Models.Report? FindById(int reportId)
    {
        // Sequential, auto-incrementing IDs (1, 2, 3, ...) — trivially
        // enumerable by an attacker once combined with the missing
        // ownership check one layer up.
        return _reports.FirstOrDefault(r => r.Id == reportId);
    }
}
