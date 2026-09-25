// Fixture: cross-file SQL (SAFE -- parameterized), V4 release corpus row RV-35 -- part 3 of 3
//
// Why it's safe: `query` is bound through SqlCommand.Parameters, so it
// never becomes part of the SQL text; the pattern characters of LIKE are
// added by the SQL itself, not by string concatenation in C#. Only
// published catalog fields are selected, and at most 50 rows are returned.

using Microsoft.Data.SqlClient;

namespace FixtureApp.Repositories;

public class ProductRepository
{
    private readonly string _connectionString;

    public ProductRepository(string connectionString) => _connectionString = connectionString;

    public List<Models.Product> FindPublishedByNameLike(string query)
    {
        var results = new List<Models.Product>();
        using var connection = new SqlConnection(_connectionString);
        connection.Open();

        using var command = new SqlCommand(
            "SELECT TOP (50) Sku, Name, Category FROM Products WHERE Published = 1 AND Name LIKE '%' + @query + '%'",
            connection);
        command.Parameters.AddWithValue("@query", query);
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            results.Add(new Models.Product
            {
                Sku = reader.GetString(0),
                Name = reader.GetString(1),
                Category = reader.GetString(2),
            });
        }
        return results;
    }
}
