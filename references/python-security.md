# Reference: Python Security

## subprocess / os.system

```python
# Unsafe: shell=True with concatenated/formatted input
subprocess.run("tool " + user_value, shell=True)
subprocess.run(f"tool {user_value}", shell=True)
os.system(f"tool {user_value}")

# Safe: argument list, no shell
subprocess.run(["tool", user_value])
```

`subprocess.run(["tool", user_value])` must NOT automatically be
considered command injection — passing an argument list without
`shell=True` does not invoke a shell, so shell metacharacters in
`user_value` are passed as a literal argument, not interpreted. The
finding is `shell=True` (or `os.system`, which always uses a shell)
combined with untrusted input in the command string.

**Windows exception:** on Windows, `subprocess` builds the child
process's command line via `list2cmdline`, which escapes for the target
program's own C-runtime argument parsing but does not account for
`cmd.exe`'s metacharacters. If the target of an argument-list call is
itself a `.bat`/`.cmd` file, Windows invokes it through `cmd.exe`
regardless of `shell=False`, and shell metacharacters in an argument can
still be interpreted (the same underlying issue as Node's
CVE-2024-27980 "BatBadBut" — see `references/node-security.md`). The
argument-list-without-shell safety guarantee holds for ordinary `.exe`
targets; it does not fully hold when the target is a `.bat`/`.cmd` file
on Windows.

## eval / exec

```python
eval(user_input)             # code injection if user_input is attacker-
                              # controlled (CWE-94)
exec(user_input)              # same, broader (statements, not just
                              # expressions)
ast.literal_eval(user_input)  # safe alternative when the goal is only
                              # parsing a literal (numbers, strings,
                              # tuples, lists, dicts, booleans, None) —
                              # does not execute arbitrary code
```

## pickle

```python
pickle.loads(untrusted_bytes)   # arbitrary code execution if the bytes
                                  # are attacker-controlled (CWE-502) —
                                  # pickle is not a data format safe for
                                  # untrusted input under any
                                  # circumstances
```

Safe alternatives for untrusted data: `json`, or a schema-validated
format (protobuf, msgpack with a fixed schema) — not a substitute
one-for-one with pickle's flexibility, but appropriate for
attacker-reachable data.

## yaml

```python
yaml.load(untrusted_input)                          # see version note below
yaml.load(untrusted_input, Loader=yaml.SafeLoader)   # safe
yaml.load(untrusted_input, Loader=yaml.FullLoader)   # safe against
                                                       # arbitrary code
                                                       # execution, but
                                                       # still check the
                                                       # PyYAML version
                                                       # (see below)
yaml.safe_load(untrusted_input)                       # safe, equivalent
                                                       # to SafeLoader
```

Check both the PyYAML version and which `Loader` is passed — the exact
safe/unsafe boundary has moved across versions, so do not treat a single
version cutoff as definitive without confirming against the version
actually pinned:

```text
< 5.1     yaml.load(data) with no Loader argument uses the fully
          unsafe loader and can construct arbitrary Python objects —
          always unsafe on untrusted input.
5.1–5.4.x yaml.load(data) with no Loader argument defaults to
          FullLoader rather than the fully unsafe loader — this closed
          the arbitrary-code-execution primitive, but FullLoader has
          had its own disclosed bypasses (e.g. CVE-2020-1747,
          CVE-2020-14343); do not treat FullLoader as equivalent to
          SafeLoader for genuinely untrusted input.
>= 6.0    the Loader argument is required — yaml.load(data) with no
          Loader raises TypeError, so this specific call shape cannot
          reach production unnoticed on this version.
```

`yaml.safe_load`/`Loader=yaml.SafeLoader` is the correct choice for
untrusted input across all versions — prefer checking for that directly
rather than relying on version-dependent default behavior.

## Temporary files

```python
# Unsafe: predictable path, race condition between check and use
path = f"/tmp/{name}"
open(path, "w")

# Safe: atomic create-and-open, unpredictable name
import tempfile
fd, path = tempfile.mkstemp()
```

`tempfile.mkstemp`/`NamedTemporaryFile` create the file atomically with
restrictive permissions; building a path manually into `/tmp` and then
opening it is subject to a race condition (TOCTOU) and predictable-name
attacks (CWE-377/379).

## Path handling

```python
# Unsafe: naive string check, or no check at all
if ".." not in user_path:
    open(os.path.join(base_dir, user_path))

# Safer: resolve and verify containment
full = os.path.realpath(os.path.join(base_dir, user_path))
if not full.startswith(os.path.realpath(base_dir) + os.sep):
    raise ValueError("path escapes base directory")
```

See `plays/file-security.md` — `os.path.join` does not prevent
traversal; an absolute path as the second argument overrides the first
entirely (mirrors .NET's `Path.Combine` behavior — see
`references/aspnet-security.md`).

## requests / TLS validation

```python
requests.get(url, verify=False)   # disables certificate validation —
                                    # CWE-295, defeats TLS's protection
                                    # against MITM
```

Only acceptable, if ever, against a genuinely internal/self-signed
endpoint where the certificate is instead pinned or validated some other
explicit way — not as a general workaround for certificate errors.

## SQL

See `references/sql-security.md` for the parameterization pattern. In
Python specifically:

```python
# Unsafe
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
cursor.execute("SELECT * FROM users WHERE name = '" + name + "'")

# Safe: parameterized
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
# SQLAlchemy ORM / Core with bound parameters is likewise safe
session.query(User).filter(User.name == name)
```

The placeholder style (`%s` above) is not universal — PEP 249 lets each
DB-API driver choose its own `paramstyle` (`?` for `sqlite3`, `%s` for
`psycopg2`/`mysqlclient`, `:name` for `oracledb`). Check the driver in
use rather than assuming `%s` — see `references/sql-security.md` for the
cross-driver table. What matters for the safety judgment is that the
value is passed separately from the query text, not which placeholder
syntax is used.

## Flask / FastAPI / Django

```text
Flask     debug=True in production exposes the Werkzeug interactive
          debugger — an unauthenticated remote code execution primitive
          if reachable (check app.run(debug=...) and FLASK_DEBUG/
          FLASK_ENV against the actual deployed configuration, not the
          repository default)
FastAPI   Pydantic models used as request bodies give you input
          validation "for free" — but check that a model used for
          output (response_model) actually excludes fields it should
          (see plays/api-security.md's sensitive-fields section);
          dependency-injected auth (Depends(...)) needs to be present
          on every router that needs it, not just the app-level default
Django    the ORM parameterizes by default (safe); raw SQL via
          .raw() or connection.cursor().execute() needs the same
          parameterization check as any other raw SQL. Django's
          template autoescaping is on by default — |safe filter or
          mark_safe() on attacker-influenced content reintroduces XSS
          (see plays/web-security.md)
```

## Serialization (general)

Beyond pickle/yaml: `marshal` (never for untrusted input, similar risk
profile to pickle), and any custom `__reduce__`/`__setstate__` on classes
that get deserialized from untrusted sources — these can be abused the
same way pickle itself can.

## Dependency management

```bash
pip-audit
```

See `plays/dependency-security.md` for combining with OSV-Scanner/Trivy
without double-counting. Also check for unpinned versions in
`requirements.txt` (`package` with no version specifier) — not a
vulnerability by itself, but it means the exact vulnerable/fixed version
in use cannot be determined from the manifest alone; check the lockfile
(`requirements.txt` with hashes, `poetry.lock`, `Pipfile.lock`) if one
exists.
