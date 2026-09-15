// Fixture: Entity Framework raw SQL - unsafe FromSqlRaw concatenation
// vs. safe FromSqlInterpolated, side by side
//
// Both methods look similar (both are "raw SQL" escape hatches on the
// same DbSet) - the point of pairing them in one file is to check that
// a reviewer distinguishes them by HOW the value reaches the query,
// not by which method name is used. See references/aspnet-security.md's
// Entity Framework section and references/sql-security.md.

using Microsoft.EntityFrameworkCore;

namespace FixtureApp.Data;

public class UserRepository
{
    private readonly AppDbContext _db;

    public UserRepository(AppDbContext db) => _db = db;

    // VULNERABLE (CWE-89): FromSqlRaw with the value concatenated
    // directly into the SQL string. Expected review outcome: CONFIRMED
    // SQL injection.
    public List<User> FindByNameUnsafe(string name)
    {
        return _db.Users
            .FromSqlRaw("SELECT * FROM Users WHERE Name = '" + name + "'")
            .ToList();
    }

    // SAFE: FromSqlInterpolated - despite the interpolated-string
    // syntax looking similar to string concatenation, the compiler
    // captures this as a FormattableString (holes kept separate from
    // the literal text) and EF Core binds each hole as a query
    // parameter at query-translation time; the value is never spliced
    // into the SQL text.
    // Expected review outcome: NO confirmed finding.
    public List<User> FindByNameSafe(string name)
    {
        return _db.Users
            .FromSqlInterpolated($"SELECT * FROM Users WHERE Name = {name}")
            .ToList();
    }

    // SAFE: FromSqlRaw is not unsafe by definition either - here it is
    // called with a separate parameters array rather than a
    // concatenated string, which is just as safe as FromSqlInterpolated
    // above. Expected review outcome: NO confirmed finding.
    public List<User> FindByNameSafeRawWithParams(string name)
    {
        return _db.Users
            .FromSqlRaw("SELECT * FROM Users WHERE Name = {0}", name)
            .ToList();
    }
}

public class User
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
}
