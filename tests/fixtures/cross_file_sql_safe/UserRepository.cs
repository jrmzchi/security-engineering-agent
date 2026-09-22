// Fixture: Cross-file SQL Injection (SAFE — parameterized query) — part 3 of 3
//
// Why it's safe: `query` is bound as a SQL parameter (@query), never
// concatenated or interpolated into the command text — the database
// treats it strictly as data, so no attacker-supplied SQL metacharacter
// can change the query's structure, regardless of how many files the
// value passed through to get here.

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

        // SAFE: parameterized query — `query` is bound as data via
        // SqlParameter, never concatenated into the SQL text.
        using var command = new SqlCommand(
            "SELECT Id, Name, Email FROM Users WHERE Name LIKE '%' + @query + '%'",
            connection);
        command.Parameters.AddWithValue("@query", query);
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
