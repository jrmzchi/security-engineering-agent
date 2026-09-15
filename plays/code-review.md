# Play: Code Review

Authoritative procedure for `skills/security-review`'s general workflow,
review modes, diff-aware review, and injection-class vulnerabilities that
are not covered by a more specific play.

## Review modes

### QUICK

Use for small diffs and PR reviews. Scope the review to the changed
attack surface: what did this diff add or change that touches input
handling, authentication, authorization, data access, file operations, or
configuration? Do not perform a full-repository architecture pass.

### STANDARD

Use for a normal repository review. Run the applicable scanners (see
`scripts/*/scan.*`) and perform semantic review of security-sensitive
code paths across the repository, not just recently changed files.

### DEEP

Use for release review, a security audit, an internet-facing application,
or a high-value system. Includes:

```text
architecture analysis
threat model (skills/threat-model)
full scanner run (Semgrep, Gitleaks, OSV-Scanner, Trivy, native audit tools)
manual semantic review of every security-sensitive area
independent validation (skills/security-validate) of every HIGH/CRITICAL
configuration review (plays/configuration-security.md)
dependency review (plays/dependency-security.md)
a complete security report (templates/security-report.md)
```

### TARGETED

Use for ordinary development-time changes, driven by
`skills/security-change-detection`'s classification rather than chosen
directly by whoever is requesting the review — see
`plays/secure-development-workflow.md` and `plays/scanner-selection.md`
(which defines this mode formally and covers scanner-tool selection).
Reviews only the domain(s) the classifier identified, using the same
"Where to look next" table QUICK/STANDARD/DEEP already use, just at
narrower scope. Not something a user picks explicitly the way they'd
ask for QUICK/STANDARD/DEEP — it's the mode the proactive workflow uses
on its own.

## Diff-aware review

When git is available:

```bash
git diff
git diff <base>...HEAD
```

Determine:

```text
What changed?
Did the attack surface change (new endpoint, new input, new sink)?
Did authorization logic change?
Were new dependencies introduced?
Did sensitive configuration change (auth settings, CORS, secrets handling)?
```

Do not limit the review strictly to changed lines when the surrounding
security context is necessary to judge the change safely — e.g. a changed
line inside a function needs the function's existing input validation
and caller context to assess correctly.

## Dangerous pattern ≠ vulnerability

This is the single most important principle in this play. None of the
following are automatically a vulnerability:

```text
eval exists                    ≠  code injection automatically exists
Process.Start exists           ≠  command injection automatically exists
innerHTML exists               ≠  XSS automatically exists
raw SQL exists                 ≠  SQL injection automatically exists
file upload exists             ≠  arbitrary file upload automatically exists
```

Determine whether attacker-controlled data reaches the dangerous
operation in a way that actually changes its behavior (query structure,
command structure, DOM structure, filesystem target) — see the attack
path model in `plays/finding-validation.md`.

## Framework-provided protections

Understand what the framework already prevents before flagging something
as a vulnerability:

```text
ASP.NET Core model binding, authorization middleware, antiforgery tokens
Entity Framework parameterization
Razor automatic encoding
React's default escaping (JSX text nodes)
Django ORM / SQLAlchemy parameterized queries
Express middleware ordering (e.g. body parsing before auth checks)
```

Do not report a vulnerability that an effective, correctly-configured
framework control prevents. But do not assume the framework is
configured correctly — verify (e.g. Razor's encoding does not help if the
code uses `Html.Raw`; EF's parameterization does not help if the code uses
`FromSqlRaw` with concatenated strings).

## Injection classes (general)

For each of the following, apply the attack path model: identify the
source, the sink, and whether anything between them prevents the input
from changing the sink's structure.

- **SQL injection** (CWE-89) — sink is a query executed against a
  database. Safe: parameterized queries, ORM query builders used as
  intended. Unsafe: string concatenation/formatting into a raw query
  string, even through an ORM's raw-SQL escape hatch.
- **OS command injection** (CWE-78) — sink is a shell or process spawn.
  Safe: argument arrays passed to an exec-family call without a shell.
  Unsafe: a single command string built by concatenation and passed
  through a shell.
- **Code injection** (CWE-94) — sink is `eval`, `Function`, dynamic
  `exec`, or a deserializer that can construct/execute arbitrary objects.
- **Template injection** (CWE-1336) — sink is a template engine rendering
  a template string that itself is attacker-controlled (not just template
  *variables*, which is normal and safe).
- **LDAP injection** (CWE-90) — sink is an LDAP filter built by string
  concatenation from user input.
- **XPath injection** (CWE-643) — sink is an XPath query built by string
  concatenation from user input.
- **Header / CRLF injection** (CWE-93 / CWE-113) — sink is an HTTP
  response header, log line, or similar line-oriented output where
  unescaped `\r\n` in user input could inject additional headers/log
  entries.

Language- and framework-specific patterns for these (what the safe API
looks like in ASP.NET, Python, Node, etc.) live in `references/`. Load
only the reference(s) matching the stack actually in use.

## Evidence and reporting

Every finding needs file path, line number, the relevant snippet, and the
traced data flow — see `plays/finding-validation.md` for the confidence
and severity models, and `templates/finding.md` for the output format.
