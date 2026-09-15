# Reference: Node.js Security

Node-specific server-side concerns. See `references/javascript-security.md`
for language-level concerns (eval, prototype pollution) that apply here
too.

## child_process

```javascript
// Unsafe: shell-interpreted string built from user input
const { exec } = require('child_process');
exec(`convert ${userFile} output.png`);

// Safe: argument array, no shell
const { execFile } = require('child_process');
execFile('convert', [userFile, 'output.png']);
```

`exec()` always spawns a shell and interprets shell metacharacters;
`execFile()`/`spawn()` without `{ shell: true }` do not. This is the same
distinction as Python's `subprocess` (`references/python-security.md`)
and .NET's `Process.Start` (`references/dotnet-security.md`) — argument
array without a shell is safe, a shell-interpreted string built from
untrusted input is not.

**Windows exception:** `execFile`/`spawn` without `shell: true`, when the
target executable is a `.bat` or `.cmd` file, is still routed through
`cmd.exe` by Windows itself (this is how the OS invokes batch files) —
Node versions before the fix for CVE-2024-27980 ("BatBadBut") did not
adequately escape arguments in this case, allowing shell metacharacters
in an argument to be interpreted. Check the Node version (fixed in
18.20.2/20.12.2/21.7.2 and later) before treating `execFile('build.bat',
[userInput])` as safe on Windows; on a current Node version this is
safe, on an older one it is not. Invoking a `.exe` directly (not through
a `.bat`/`.cmd` wrapper) is not affected.

## Express: routing and middleware ordering

```javascript
// Auth middleware registered AFTER the routes it should protect —
// those routes are unprotected regardless of the middleware's own
// correctness
app.use('/admin', adminRoutes);
app.use(authMiddleware); // too late for /admin

// Correct order
app.use(authMiddleware);
app.use('/admin', adminRoutes);
```

Express executes middleware in registration order — this makes ordering
itself a security-relevant fact, not just a style choice. Also check
body-parsing middleware is registered before any handler that reads
`req.body`, and that error-handling middleware (4-arg signature) is
registered last so it actually catches errors from routes above it.

## JWT handling

```text
Algorithm confusion: verifying with jwt.verify(token, key) without
    pinning the expected algorithm allows an attacker to submit a token
    signed with a different, weaker algorithm (e.g. 'none', or HS256
    when the server expects RS256 and the "key" it uses for HS256
    verification is actually the RS256 public key, which is not secret)
    -> pass { algorithms: ['RS256'] } (or whatever is actually expected)
       explicitly to jwt.verify
Secret/key hardcoded in source -> plays/secrets-security.md
No expiration (missing exp claim, or not checked)
```

**Version matters for the algorithm-confusion check.** `jsonwebtoken`
>= 9.0.0 (which fixed CVE-2022-23540 and CVE-2022-23541) derives the
allowed algorithm set from the key's type by default, so a call without
an explicit `algorithms` option is not automatically exploitable on a
current version — check the installed version before treating a missing
`algorithms` option as a confirmed finding; on a current version it is a
hardening recommendation, not a vulnerability, per
`plays/code-review.md`'s "framework-provided protections" principle. On
`jsonwebtoken` < 9.0.0, treat it as a real finding.

## Cookie configuration

```javascript
// Unsafe: defaults, no flags set
res.cookie('session', token);

// Safer
res.cookie('session', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict', // or 'lax' only if no GET endpoint has side effects
});
```

See `plays/web-security.md`'s CSRF section for why `sameSite: 'lax'`
alone is not sufficient for a GET endpoint with side effects.

## CORS

```javascript
// Unsafe: reflecting the request origin, or wildcard + credentials
app.use(cors({ origin: true, credentials: true }));

// Safer: explicit allowlist
app.use(cors({ origin: ['https://trusted.example.com'], credentials: true }));
```

## Filesystem operations / path handling

```javascript
// Unsafe: no containment check
fs.readFile(path.join(baseDir, req.params.name), cb);

// Unsafe: containment check runs on a path that has not been resolved
// through the filesystem — path.resolve/path.join are pure string
// operations in Node (they never touch the filesystem or resolve
// symlinks). A symlink placed inside baseDir that points outside it
// will still pass this check, then get followed when the file is
// actually opened:
const resolved = path.resolve(baseDir, req.params.name);
if (!resolved.startsWith(path.resolve(baseDir) + path.sep)) {
  throw new Error('path escapes base directory');
}
fs.readFile(resolved, cb); // may still follow a symlink out of baseDir

// Safer: resolve through the filesystem (follows symlinks) before the
// containment check
const realBase = await fs.promises.realpath(baseDir);
const realTarget = await fs.promises.realpath(path.resolve(baseDir, req.params.name));
if (!realTarget.startsWith(realBase + path.sep)) {
  throw new Error('path escapes base directory');
}
fs.readFile(realTarget, cb);
```

`path.join` and `path.resolve` are not interchangeable here: `path.join`
concatenates and normalizes (so `..` segments still escape `baseDir`) but
an absolute second argument does **not** override the first —
`path.join('/base', '/etc/passwd')` produces a path still rooted under
`/base`. `path.resolve`, by contrast, treats each argument as a new
starting point when it is absolute, so an absolute second argument DOES
override the first — this is the .NET `Path.Combine`/Python
`os.path.join` "absolute path overrides" behavior's actual Node
equivalent, not `path.join`. Either way, neither function resolves
symlinks — that requires `fs.realpath`/`fs.realpathSync`, as shown above.
See `plays/file-security.md` for the general containment-check
principle and `references/macos-security.md`/`references/windows-security.md`
for the platform-level symlink/junction considerations.

## Template engines

Most template engines (EJS, Pug, Handlebars) auto-escape by default in
their standard output syntax — check for the escape-hatch syntax used on
attacker-influenced data:

```text
EJS         <%- value %>   (unescaped) vs <%= value %> (escaped)
Handlebars  {{{ value }}}  (unescaped) vs {{ value }} (escaped)
```

## SQL libraries / NoSQL injection

```javascript
// SQL: see references/sql-security.md for the general pattern —
// parameterized queries via pg/mysql2/knex bound params, not string
// interpolation into the query text

// NoSQL (MongoDB) - unsafe: query operators from unvalidated JSON body
db.collection('users').find({ username: req.body.username, password: req.body.password });
// if req.body.password is {"$ne": null}, this becomes a query operator
// injection that can bypass the password check entirely (CWE-943)

// Safer: validate/cast input types before use in a query, or use a
// schema validator (e.g. Mongoose schemas with strict typing) that
// rejects non-scalar values where a scalar is expected
```

NoSQL injection in MongoDB-style query APIs is not about escaping
characters (there is no SQL string to escape) — it is about the query
API interpreting a JSON object where a plain scalar was expected. Check
that request input is validated/typed before being placed into a query
filter, not merely passed through.

## npm dependencies

```bash
npm audit
```

See `plays/dependency-security.md` for combining with OSV-Scanner/Trivy.
Also check `package.json` for scripts (`preinstall`/`postinstall`) on new
or unfamiliar dependencies — an install script that runs arbitrary code
at `npm install` time is a supply-chain risk independent of any known CVE.
