# Reference: SQL Security

Cross-language parameterization patterns and SQL-specific edge cases.
Language-specific examples also appear in
`references/aspnet-security.md`, `references/python-security.md`, and
`references/node-security.md` — this file is the cross-reference point
for the general pattern and the cases that don't fit neatly into "just
parameterize it".

## The core pattern

Safe: the query text is fixed at the time the database driver parses it;
values are supplied separately and never become part of the query's
grammar, no matter what characters they contain.

```text
.NET / EF Core          LINQ, or FromSqlInterpolated / FromSqlRaw with a
                        separate parameters array (not string-embedded values)
.NET / raw ADO.NET      SqlCommand + SqlParameter (see references/dotnet-security.md)
Python / sqlite3        cursor.execute("... WHERE x = ?", (value,))
Python / psycopg2       cursor.execute("... WHERE x = %s", (value,))
Python / mysqlclient    cursor.execute("... WHERE x = %s", (value,))
Python / oracledb       cursor.execute("... WHERE x = :name", {"name": value})
Python / SQLAlchemy     ORM/Core with bound parameters (paramstyle-agnostic)
Node / pg               client.query("... WHERE x = $1", [value])
Node / mysql2           connection.query("... WHERE x = ?", [value])
Java / JDBC             PreparedStatement with ? placeholders
```

The placeholder syntax (`?`, `%s`, `$1`, `:name`, ...) is chosen by the
driver/DB-API (in Python, per PEP 249's `paramstyle` attribute) — it is
not a portable indicator of safety by itself. What makes any of the rows
above safe is that the value is supplied to the driver separately from
the query text, regardless of which placeholder syntax the driver uses.

Unsafe: the value is concatenated or interpolated into the query string
before the driver ever sees it — regardless of language, ORM, or
whether escaping/quoting was attempted manually.

## What parameterization does NOT cover

Bound parameters protect *values* — they do not help when the
attacker-controlled input needs to become part of the query's
*structure*: a table name, a column name, an `ORDER BY` direction/column,
or a raw fragment of SQL.

```text
# Unsafe even with "parameterized" values elsewhere in the same query:
query = f"SELECT * FROM users ORDER BY {sort_column}"
```

For structural elements, validate against an explicit allowlist of known
valid identifiers (e.g. a fixed set of column names the UI is allowed to
sort by) rather than attempting to sanitize/escape the identifier —
identifier escaping rules differ by database and are easy to get subtly
wrong.

## Stored procedures

Calling a stored procedure with parameters is generally safe by the same
mechanism as parameterized queries. The finding to look for is a stored
procedure that itself builds and executes dynamic SQL internally (e.g.
T-SQL `EXEC(@sql)` where `@sql` was built by concatenating a parameter) —
the injection risk moves inside the procedure and is not visible from the
calling application code alone. If application code calls a stored
procedure that is documented or known to build dynamic SQL internally,
trace what it does with its parameters before calling it safe.

## Second-order SQL injection

Data that was safely parameterized on the way *into* the database can
still be unsafe on the way *out*, if a later query builds SQL by
concatenating a previously-stored value rather than parameterizing it
again at read time. Check that the safe pattern is applied at every
point a value is used in a query, not just where it was first written.

## ORMs are not a blanket exemption

An ORM being in use is a strong signal of safety, not a guarantee — check
specifically for the ORM's own raw-SQL escape hatches
(`FromSqlRaw`/`ExecuteSqlRaw` in EF, `.raw()` in Django, raw/literal
query builders in Sequelize/Knex/TypeORM) used with concatenated input,
since these bypass the ORM's own parameterization.
