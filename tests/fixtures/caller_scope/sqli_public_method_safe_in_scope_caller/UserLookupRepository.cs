// Fixture: injection class, public method with a safe in-scope caller (VULNERABLE) — part 1 of 2
//
// Expected review outcome: CONFIRMED HIGH SQL injection (CWE-89) in
// FindByDisplayName. See plays/finding-validation.md, "Rule — a sink whose
// callers are outside the review scope", injection class: the parameter is
// concatenated into raw SQL at the sink and the method is public, so its
// unseen callers can pass anything. The trap: rejecting it because the only
// in-scope caller (StatisticsService.cs) passes a constant.

using Microsoft.EntityFrameworkCore;

namespace FixtureApp.Data;

public class UserLookupRepository
{
    private readonly AppDbContext _db;

    public UserLookupRepository(AppDbContext db) => _db = db;

    public List<User> FindByDisplayName(string displayName)
    {
        return _db.Users
            .FromSqlRaw("SELECT * FROM Users WHERE DisplayName = '" + displayName + "'")
            .ToList();
    }
}

public class User
{
    public int Id { get; set; }
    public string DisplayName { get; set; } = "";
}
