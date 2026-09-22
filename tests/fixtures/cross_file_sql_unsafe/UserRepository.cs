// Fixture: Cross-file SQL Injection (VULNERABLE) — part 3 of 3 (the sink)
//
// See UsersController.cs for the attack path's start and
// UserSearchService.cs for the intermediate hop. This is where the
// three-file chain reaches an unparameterized SQL sink.

using Microsoft.Data.SqlClient;
using FixtureApp.Models;

namespace FixtureApp.Repositories;

public class UserRepository
{
    private readonly string _connectionString;

    public UserRepository(string connectionString) => _connectionString = connectionString;

    public List<User> FindByNameLike(string query)
    {
        var results = new List<User>();
        using var connection = new SqlConnection(_connectionString);
        connection.Open();

        // VULNERABLE: `query` — attacker-controlled since Controller ->
        // Service -> here — is interpolated directly into the SQL text
        // instead of being passed as a parameter. No single file in
        // this three-file chain shows a complete SQL injection on its
        // own; the vulnerable sink only becomes reachable once the
        // Controller's unvalidated input is traced all the way here.
        using var command = new SqlCommand(
            $"SELECT Id, Name, Email FROM Users WHERE Name LIKE '%{query}%'",
            connection);
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            results.Add(new User
            {
                Id = reader.GetInt32(0),
                Name = reader.GetString(1),
                Email = reader.GetString(2),
            });
        }
        return results;
    }
}
