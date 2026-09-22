// Fixture: Cross-file SQL Injection (SAFE — parameterized query) — part 2 of 3
//
// Structurally identical to cross_file_sql_unsafe/UserSearchService.cs
// — the safety fix is entirely in UserRepository.cs's use of a SQL
// parameter, not in this file.

namespace FixtureApp.Services;

public class UserSearchService
{
    private readonly Repositories.UserRepository _repository;

    public UserSearchService(Repositories.UserRepository repository) =>
        _repository = repository;

    public List<Models.User> SearchUsers(string query)
    {
        return _repository.FindByNameLike(query);
    }
}
