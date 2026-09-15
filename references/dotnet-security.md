# Reference: .NET Security

General .NET platform security knowledge, independent of ASP.NET's web
layer (see `references/aspnet-security.md` for that). Used by
`plays/data-security.md`, `plays/api-security.md`, and
`plays/dependency-security.md` when the stack is .NET.

## Data Protection API

ASP.NET Core's Data Protection API is the framework-provided answer to
"how do I encrypt/decrypt data at rest safely" (cookies, tokens, anything
needing authenticated encryption) — prefer it over hand-rolled
`System.Security.Cryptography` usage for these purposes. Check that:

```text
The key ring is persisted somewhere durable across restarts/instances
    (default in-memory-only persistence loses keys on restart, breaking
    anything protected with them — not itself a vulnerability, but worth
    flagging as a reliability issue that tempts developers into unsafe
    workarounds)
Persisted keys are protected at rest
    (.PersistKeysToFileSystem(dir) with no corresponding
    .ProtectKeysWithDpapi() / .ProtectKeysWithDpapiNG() /
    .ProtectKeysWithCertificate() call leaves the key ring stored as
    plaintext XML on disk — this is the actual risk to check for. This
    matters most on Linux/containers, where DPAPI is unavailable and a
    certificate-based protector must be configured explicitly, or keys
    end up unprotected by default)
```

## Insecure deserialization

See `plays/api-security.md`'s "Insecure deserialization" section for the
general risk and validation approach. .NET-specific detail: `Newtonsoft.Json`
with `TypeNameHandling` set to anything other than `None` on
attacker-reachable input allows type substitution during deserialization
and should be treated the same as `BinaryFormatter`/
`NetDataContractSerializer` — a candidate for arbitrary type
instantiation, not just a data-parsing concern. `System.Text.Json` has no
`TypeNameHandling`-equivalent feature and does not carry this risk in its
default configuration. Classic ASP.NET's `LosFormatter`/
`ObjectStateFormatter` (ViewState serialization) carry the same class of
risk as `BinaryFormatter` when ViewState MAC validation is disabled —
check `<pages enableViewStateMac="false">` is not set.

## Insecure random generation

See `plays/data-security.md` for the general principle (CSPRNG required
for tokens/keys/IVs). .NET-specific detail: the correct API is
`System.Security.Cryptography.RandomNumberGenerator.GetBytes` (static
method, .NET 6+); `RNGCryptoServiceProvider` is obsolete since .NET 6
(`SYSLIB0023`) — do not suggest it in new remediation code.

## File and SQL APIs (non-EF / non-web-layer)

Not every .NET application uses Entity Framework or ASP.NET Core — a
console app, worker service, or classic ASP.NET application may use
these APIs directly. See `references/aspnet-security.md` for the web
layer and `references/sql-security.md` for the cross-language
parameterization pattern this exemplifies.

```csharp
// Unsafe: string-concatenated SQL via raw ADO.NET
var cmd = new SqlCommand("SELECT * FROM Users WHERE Name = '" + name + "'", conn);

// Safe: parameterized via SqlParameter
var cmd = new SqlCommand("SELECT * FROM Users WHERE Name = @name", conn);
cmd.Parameters.AddWithValue("@name", name);
```

```csharp
// Path.Combine does NOT prevent path traversal by itself — an absolute
// second argument overrides the first entirely, and ../ sequences
// survive it. The actual control is resolving the final path and
// verifying it stays within the intended base directory:
var combined = Path.Combine(baseDir, userPath);
var full = Path.GetFullPath(combined);
if (!full.StartsWith(Path.GetFullPath(baseDir) + Path.DirectorySeparatorChar))
    throw new UnauthorizedAccessException();
using var fs = new FileStream(full, FileMode.Open, FileAccess.Read);
```

See `plays/file-security.md` for the general containment-check principle
this follows.

## HttpClient

```text
HttpClientHandler.ServerCertificateCustomValidationCallback returning
    true unconditionally disables certificate validation entirely
HttpClient instances created per-request instead of reused/pooled
    (via IHttpClientFactory) is a reliability/resource issue, not a
    security one directly — but note it if seen alongside SSRF findings
    since it often indicates less mature handling of outbound requests
    generally
```

See `plays/api-security.md` for the SSRF analysis of what URL the
`HttpClient` is actually asked to fetch.

## Process.Start

```csharp
// Unsafe: shell-interpreted string built from user input
Process.Start("cmd.exe", "/c " + userInput);

// Safer: ProcessStartInfo with ArgumentList, UseShellExecute = false
var psi = new ProcessStartInfo("tool.exe") { UseShellExecute = false };
psi.ArgumentList.Add(userInput);
Process.Start(psi);
```

`Process.Start` existing is not command injection by itself — see
`plays/code-review.md`'s "dangerous pattern ≠ vulnerability" principle.
The finding is string-built commands passed through a shell
(`UseShellExecute = true` with a concatenated argument string, or
invoking `cmd.exe /c` with untrusted content).

## Configuration and secrets

```text
appsettings.json / appsettings.Development.json committed with real
    connection strings, API keys, or certificates
    -> see plays/secrets-security.md
User Secrets (dotnet user-secrets) used only for local dev, not a
    production secret store by itself — appropriate for its intended
    scope, not a substitute for a real secret manager in production
Environment-variable-based configuration overriding appsettings.json
    values in production is the expected, safe pattern
```

## Logging and exception handling

```text
Full exception details (including stack traces, connection strings in
    exception messages) returned to the client in production
    -> see plays/configuration-security.md's "Verbose errors"
Sensitive values (passwords, tokens, full request bodies on auth
    endpoints) written to application logs
```

## Dependency auditing

```powershell
dotnet list package --vulnerable
dotnet list package --vulnerable --include-transitive
```

See `plays/dependency-security.md` for how to combine this with
OSV-Scanner/Trivy results without double-counting.
