// Fixture: Cross-file Object Authorization / BOLA (VULNERABLE) — part 2 of 3
//
// See ReportsController.cs for the attack path's start and
// ReportRepository.cs for the sink. This is where the missing check
// should have gone: the service has no notion of "the current caller"
// at all, so it cannot enforce ownership even in principle.

namespace FixtureApp.Services;

public class ReportService
{
    private readonly Repositories.ReportRepository _repository;

    public ReportService(Repositories.ReportRepository repository) => _repository = repository;

    public Models.Report? GetReport(int reportId)
    {
        // VULNERABLE: no ownership/policy check — any authenticated
        // caller who supplies a valid reportId gets that report back,
        // regardless of who created it.
        return _repository.FindById(reportId);
    }
}
