# Reference: macOS Security

macOS-specific platform semantics relevant to `plays/file-security.md`
and `plays/configuration-security.md`.

## Path semantics

```text
The default filesystem format (APFS, like its predecessor HFS+) is
    case-insensitive but case-preserving by default — see
    references/windows-security.md's path-semantics section for the
    risk-direction distinction (denylist checks can be bypassed by a
    case variant; allowlist/containment checks instead risk a false
    rejection, not a bypass). However, APFS/HFS+ can also be formatted
    case-sensitive (common on build/CI machines and some developer
    setups) — do not assume case-insensitivity; if the deployment
    target's filesystem case-sensitivity is not known, the containment
    check should not rely on either assumption and should instead
    compare fully resolved, canonical paths
`/` is the only path separator; there is no drive-letter or UNC-path
    equivalent to account for, unlike Windows
APFS is normalization-preserving but normalization-INSENSITIVE for
    lookups (has been since macOS 10.13) — a filename stored as NFC
    (precomposed, e.g. "café" as a single é character) and a request
    using the NFD form (decomposed, "e" + combining acute accent) can
    resolve to the SAME file even though the two byte sequences differ.
    A byte-level string comparison used in an authorization or
    allowlist/denylist check can be bypassed by an attacker submitting a
    differently-normalized but filesystem-equivalent name. Compare
    canonicalized paths (resolved via the filesystem, e.g. realpath)
    rather than raw byte/string equality, same principle as the
    case-sensitivity point above but a macOS-specific additional vector.
```

## Path resolution for containment checks

```text
realpath() (POSIX) / Python's pathlib.Path.resolve() resolve `..` AND
    symlinks to a canonical absolute path — the containment check must
    run on this resolved path, not the raw input.
Node's path.resolve() is NOT the same kind of function despite the
    similar name — it is a pure string operation (normalizes `..`
    segments, joins against an absolute argument) and never touches the
    filesystem or resolves symlinks. Use fs.realpath()/fs.realpathSync()
    in Node instead — see references/node-security.md.
Symlinks are common and routinely used (e.g. /tmp is itself a symlink
    to /private/tmp on macOS) — a naive check that only resolves `..`
    segments but does not also resolve symlinks can be bypassed by a
    symlink placed inside the base directory that points outside it
```

## File permissions

Standard POSIX permission bits (owner/group/other, read/write/execute)
apply, with the addition of extended attributes and, for
Gatekeeper-relevant scenarios, code-signing-related attributes (see
below). When reviewing deployment scripts or installers:

```text
Check that application support/data directories are not created with
    overly permissive modes (e.g. 0777) where a narrower mode
    (0700/0750) would suffice
```

## Gatekeeper and notarization (application distribution)

Not a file-permission concept, but relevant when this kit is used to
review a macOS application (not just a server-side service deployed to
macOS): unsigned or non-notarized applications distributed outside the
Mac App Store are blocked or warned against by Gatekeeper by default.
This is a distribution/trust concern rather than a traditional
CWE-mapped vulnerability class — note it as a finding only when
reviewing an actual distributable macOS application, and treat the
absence of code signing/notarization as a supply-chain/integrity gap
(a user has less assurance the binary they run is unmodified) rather
than trying to force-fit it into one of the standard vulnerability
categories in `plays/`.

## Temporary files

`mkstemp`-family APIs (available via the standard C library and exposed
by most language runtimes, e.g. Python's `tempfile.mkstemp`) create the
file atomically with restrictive permissions and are the correct choice
here, same as on other POSIX-like systems. Avoid building a predictable
path into `/tmp` manually and then opening it — the same TOCTOU race
noted in `references/python-security.md` applies.
