# Play: File Security

Authoritative procedure for filesystem-related findings. This class
deserves special attention per the project's mandatory coverage.

## Scope

```text
Uploads
Downloads
ZIP extraction
Archive creation
Temporary files
File deletion
Directory traversal
Filename generation
Extension validation
MIME validation
Storage location
Static serving
```

## Directory traversal (CWE-22)

Any path built by concatenating a fixed base directory with
attacker-controlled input (a filename, an ID used as a path segment) is a
candidate. Check for:

```text
../ sequences (and encoded variants: %2e%2e%2f, double-encoding,
    Windows-style ..\)
Absolute paths supplied where a relative path was expected
    (e.g. "/etc/passwd" or "C:\Windows\..." accepted as a "filename")
UNC paths (\\server\share\...) on Windows
Windows drive-letter paths (C:\...) where a relative path was expected
Symlinks: does resolving the final path follow a symlink out of the
    intended base directory?
```

**Safe pattern:** resolve the final absolute path (canonicalize/realpath)
and verify it is still inside the intended base directory, *after*
resolution — checking the string for `..` before resolution is
insufficient on its own (encoding and symlink tricks can bypass a naive
string check). `Path.Combine` (.NET) and `os.path.join`/`pathlib` do not
prevent traversal by themselves; the base-directory containment check is
the actual control.

## Uploads

```text
File type validated only by extension or client-supplied MIME type
    -> both are attacker-controlled; validate by content (magic bytes)
    where the file type matters for later processing/serving
Filename taken from the client and used directly to build a storage path
    -> regenerate the filename (e.g. a UUID) or strictly sanitize it
No size limit
    -> resource exhaustion
Executable content (e.g. an uploaded .aspx/.php/.jsp) reachable under a
    path the web server maps to a script handler
    -> if the upload directory is inside the web root and the server is
    configured to execute scripts from it, an uploaded file requested
    directly is executed server-side BEFORE any application-level
    download handler runs — a Content-Disposition header set by that
    handler does not help, because the request never reaches it. Store
    uploads outside the web root, or in a location/origin explicitly
    configured with no script execution (static-only handler mapping).
    This applies to deployments where the web root itself is a script
    handler directory (classic ASP.NET/IIS, PHP, CGI). ASP.NET Core's
    wwwroot is NOT one of these by default — StaticFiles has no handler
    mapping for .aspx/.php/.jsp and does not execute anything; verify
    the actual hosting model (see references/iis-security.md) before
    treating this as the risk in an ASP.NET Core project. The same
    upload-into-web-root pattern is still a real risk there, just via a
    different mechanism — see the "Content containing embedded scripts"
    paragraph below, which covers a served-inline-and-renders-in-the-
    browser file (e.g. .html) rather than a server-executed one.

Content containing embedded scripts (e.g. an uploaded .svg or .html
    file) rendered directly in the browser
    -> this is a browser-side risk, not a server-execution risk; here
    Content-Disposition: attachment (forcing download instead of inline
    rendering) or serving from a separate, cookie-less origin is the
    correct control. Do not use this control as a substitute for the
    web-root/script-execution control above — they address different
    halves of "executable content".

Uploads stored under a directory the app serves statically (e.g.
    ASP.NET Core wwwroot/ via StaticFiles, Express static(), a
    Flask/Django static root) where the uploader influences the
    stored file's extension or served content type (no server-side
    extension allowlist or forced extension; a check on the
    client-supplied Content-Type does not count, see the first
    item above)
    -> the uploaded file is reachable at its own static URL, so an
    uploaded .html/.svg renders on the app's origin: unrestricted upload
    -> stored XSS (CWE-434 + CWE-79). A Content-Disposition header set
    by a separate download handler does NOT protect it: that header
    only applies to responses that handler sends, and a direct request
    for the static URL never reaches it. Check which response actually
    serves the file.
    -> report it as its OWN finding, even when the same code also has a
    confirmed path-traversal finding (e.g. the filename used unsanitized
    to build the path): fixing the traversal leaves this one open, so
    one finding must not absorb the other.

Whenever an upload is written under a web root or another directory the
    code names as served (e.g. wwwroot/, public/, static/), or under any
    directory that code in the review scope serves, work through these
    four checks before deciding the stored-XSS finding. Never skip them
    because a path-traversal finding on the same code was already
    written. (An upload stored outside any web root, with nothing in the
    review scope serving that directory, gets no stored-XSS finding; the
    other upload checks above still apply.)
    1. Hosting -- the code or configuration that serves that directory:
       app.UseStaticFiles(...) (the default web root, or its
       FileProvider), express.static(dir), a Flask/Django static root,
       or a web-server alias or virtual directory.
    2. Public URL -- the request path where a stored upload is reached:
       the storage path mapped through that configuration's prefix
       (e.g. RequestPath + the stored file name).
    3. Content type -- the uploader can get a browser-renderable type
       stored and served: no server-side extension allowlist or forced
       extension, and the served Content-Type follows the stored
       extension (e.g. .html -> text/html, .svg -> image/svg+xml).
       X-Content-Type-Options: nosniff does not stop a file that is
       served as text/html from rendering.
    4. Browser execution on the app's origin -- THAT static response
       renders inline (no Content-Disposition: attachment on it; one on
       a separate download handler does not count), from the same
       origin as the application (not a separate cookie-less origin,
       and not a CSP sandbox on that response).
    -> all four established from code in the review scope: CONFIRMED
       stored XSS, as its own finding.
    -> the upload lands under a web-root-like directory, but the hosting
       configuration (1) or the URL mapping (2) is not in the review
       scope: do NOT assume the directory is served.
       Middleware and hosting configuration the scope does not show are
       not assumed to exist (plays/finding-validation.md). Report
       NEEDS_VERIFICATION and name the missing hosting evidence; do not
       drop the candidate silently either.
    -> the code shows that a check fails (e.g. a forced safe extension,
       or attachment on the static response itself): no stored-XSS
       finding; say which control holds.
```

## Downloads / static serving

```text
Requested filename/path passed through to the filesystem without
    validating containment in the intended base directory (see
    Directory traversal above)
Authorization checked at the "list files" step but not re-checked at
    the "fetch this specific file" step
```

## ZIP / archive extraction — Zip Slip (CWE-22 via archive entries)

When extracting an archive, each entry's name can itself contain `../`
sequences or absolute paths, allowing a malicious archive to write files
outside the intended extraction directory. Check that extraction code
validates each entry's resolved output path is inside the target
directory *before* writing it — this is independent of, and in addition
to, the general directory-traversal check above, since the untrusted path
here comes from inside the archive rather than directly from a request.

## Archive creation

Building an archive from user-influenced paths can leak files outside
the intended set if entry paths are not restricted to the expected
source directory, or can create entries with absolute/traversal paths
that later trigger Zip Slip in whatever extracts them.

## Temporary files (CWE-377 / CWE-379)

```text
Predictable temp filename in a shared/world-writable directory
    -> race condition / symlink attack risk; use the platform's
    secure temp-file API (e.g. tempfile.mkstemp, Path.GetTempFileName
    is weaker — prefer APIs that create-and-open atomically)
Temp file left world-readable when it contains sensitive data
Temp file not deleted after use (leaves sensitive data on disk)
```

## File deletion

Deleting a path built from user input needs the same containment check as
reads/writes — an attacker-controlled delete path is a directory-traversal
variant with a more destructive impact (arbitrary file deletion rather
than read).

## Overwrite attacks

Writing to a path derived from user input without checking whether it
already exists (or without proper locking) can let one user overwrite
another user's file, or overwrite a file the application depends on.

## Windows and macOS path semantics

Consider both when the deployment target is cross-platform — see
`references/windows-security.md` and `references/macos-security.md` for
the platform-specific detail (case-insensitivity's risk direction
depending on denylist vs. allowlist checks, path-separator acceptance,
drive letters/UNC paths, reserved device names, Unicode normalization).
