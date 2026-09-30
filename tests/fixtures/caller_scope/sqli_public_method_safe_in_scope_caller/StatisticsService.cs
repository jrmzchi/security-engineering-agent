// Fixture: injection class, public method with a safe in-scope caller (VULNERABLE) — part 2 of 2
//
// See UserLookupRepository.cs. The only in-scope caller passes a constant;
// that does not make the public repository method safe for its other callers.

namespace FixtureApp.Services;

public class StatisticsService
{
    private readonly Data.UserLookupRepository _users;

    public StatisticsService(Data.UserLookupRepository users) => _users = users;

    public int CountAdministrators()
    {
        return _users.FindByDisplayName("administrator").Count;
    }
}
