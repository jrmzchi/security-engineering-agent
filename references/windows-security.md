# Reference: Windows Security

Windows-specific platform semantics relevant to `plays/file-security.md`
and `plays/configuration-security.md`.

## Path semantics

```text
Case-insensitive (but case-preserving) filesystem by default (NTFS) —
    the risk direction depends on which kind of check this affects:
    * Denylist / blocklist checks (rejecting a specific name, extension,
      or path segment, e.g. IIS request filtering blocking ".php") can
      be BYPASSED by a differently-cased variant that a case-sensitive
      string comparison fails to match but the filesystem still resolves
      the same way (".PHP", ".PhP").
    * Allowlist / containment checks (verifying a resolved path starts
      with an intended base directory) are NOT bypassed by case
      differences in this way — the filesystem still resolves to the
      same file either way, so a mismatch here causes a legitimate
      request to be wrongly REJECTED (an availability/correctness bug),
      not a security bypass. Do not report a case-sensitive containment
      comparison as a traversal vulnerability; report it as a
      false-rejection bug if anything.
Both `\` and `/` are commonly accepted as path separators by the OS and
    by many libraries — a traversal filter that only checks for `../`
    and not `..\` is incomplete
Drive letters (C:\, D:\, ...) — an "absolute path supplied where a
    relative filename was expected" check must reject these, not just
    reject a leading `\`
UNC paths (\\server\share\...) — can point to a network location;
    accepting one where a local relative path was expected can result
    in unexpected network access or, on older/misconfigured systems,
    credential relay
Reserved device names (CON, PRN, AUX, NUL, COM1-9, COM0, LPT1-9, LPT0,
    and the console-specific CONIN$/CONOUT$) as a filename (with or
    without an extension, e.g. "con.txt") have special OS-level behavior
    and can cause unexpected errors or behavior in file-handling code
    that does not account for them
```

## Upload/extension-filter bypasses specific to Windows

An extension-based allowlist/denylist for uploaded files (see
`plays/file-security.md`'s "Uploads" section) needs to account for
Windows-specific name handling that can defeat a naive check:

```text
Alternate Data Streams (ADS)   a filename like "shell.aspx:evil.txt" on
                                NTFS creates the data in an alternate
                                stream of a file named "shell.aspx" —
                                depending on how the upload/save code
                                and later the serving code each parse
                                the name, this can be used to smuggle
                                content past an extension check or to
                                write to an unexpected stream of an
                                existing file
Trailing dots and spaces        Win32 APIs silently strip trailing "."
                                and " " characters from a filename
                                (e.g. "shell.aspx." or "shell.aspx " is
                                saved/opened as "shell.aspx") — an
                                extension check performed on the
                                as-submitted name before this stripping
                                happens can be bypassed
8.3 short filenames             if 8.3 name generation is enabled on the
                                volume, a long filename that would fail
                                an extension check may still be
                                reachable via its auto-generated 8.3
                                short name (e.g. "malicious.aspx" as
                                "MALICI~1.ASP") if the serving path
                                resolves short names
```

## Path resolution for containment checks

```text
GetFullPath() / Path.GetFullPath() (.NET) resolves `..`, mixed
    separators, and relative segments to an absolute path — the
    containment check (does the resolved path start with the intended
    base directory) must run AFTER this resolution, not on the raw
    input string
Symlinks/junctions — Windows supports both NTFS symbolic links and
    directory junctions; a resolved path can still lead outside the
    intended directory via one of these even after GetFullPath()
    resolution, if the base directory itself (or a directory within it)
    contains a junction/symlink pointing elsewhere
```

## File permissions

Windows uses ACLs (access control lists) rather than the POSIX
owner/group/other model. When reviewing deployment/installation scripts:

```text
Check that application directories are not granted Everyone/Users
    "Full Control" or "Modify" where read-only (or no) access would
    suffice
Application pool identities (IIS) or service accounts should have the
    minimum ACL entries needed — see references/iis-security.md
```

## Temporary files

`Path.GetTempFileName()` creates a uniquely-named file but with weaker
guarantees than a true atomic create-and-open API — there is a brief
window between name generation and file creation. Prefer an API that
creates and opens the file in one step where available, and always set
restrictive permissions explicitly if the temp file will contain
sensitive data, rather than relying on the default temp-directory ACLs.

## Line endings and encoding (secondary consideration)

Not itself a security issue, but relevant when writing cross-platform
file-handling code reviewed under this play: Windows text-mode file APIs
translate `\n` to `\r\n` by default, which can affect the exact bytes
written to disk in ways that matter for CRLF-injection-adjacent findings
(see `plays/code-review.md`'s header/CRLF injection section) if log
files or generated content are later parsed elsewhere.
