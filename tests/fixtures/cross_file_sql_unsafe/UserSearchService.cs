// Fixture: Cross-file SQL Injection (VULNERABLE) — part 2 of 3
//
// See UsersController.cs for the attack path's start and
// UserRepository.cs for the sink. This file adds no sanitization or
// parameterization of its own — the attacker-controlled `query` value
// passes through unchanged.

namespace FixtureApp.Services;

public class UserSearchService
{
    private readonly Repositories.UserRepository _repository;

    public UserSearchService(Repositories.UserRepository repository) =>
        _repository = repository;

    public List<Models.User> SearchUsers(string query)
    {
        // Step 2: no validation, no allowlist, no length/charset check
        // — passed straight to the repository layer.
        return _repository.FindByNameLike(query);
    }
}
