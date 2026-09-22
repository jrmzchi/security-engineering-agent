// Fixture: Cross-file Object Authorization / BOLA (SAFE — ownership
// check enforced) — part 2 of 3
//
// Why it's safe: the report is only returned if it belongs to the
// caller whose ID was passed in from the controller. A deliberately
// vague "NotFound" is returned rather than "Forbidden" so a caller
// cannot distinguish "doesn't exist" from "exists but isn't yours" —
// see plays/authorization.md for that disclosure-policy tradeoff.

namespace FixtureApp.Services;

public class ReportService
{
    private readonly Repositories.ReportRepository _repository;

    public ReportService(Repositories.ReportRepository repository) => _repository = repository;

    public Models.Report? GetReport(int reportId, int currentUserId)
    {
        var report = _repository.FindById(reportId);
        // SAFE: object-level authorization — confirm the caller owns
        // this specific report before returning it. An unguessable ID
        // is NOT what makes this safe (the repository below still uses
        // plain sequential IDs) — the explicit ownership check is.
        if (report is null || report.OwnerUserId != currentUserId)
        {
            return null;
        }
        return report;
    }
}
