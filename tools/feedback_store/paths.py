"""Repository-relative path normalization and validation.

`context-manifest-schema.md` section 5's `evidence.path` /
`dependencies` / `reachabilityPath[].path` fields are always
repository-relative paths. This module is the single place that
decides what "the same path" means -- every other module in this
package compares paths only through `normalize()`/`same_path()`, never
with a bare `==` on a raw string, so the rule is enforced in one place
rather than re-implemented (and potentially re-implemented
inconsistently) at each call site.

Case sensitivity, decided explicitly (not left to whatever filesystem
happens to be running this code). `[CHANGED, per explicit instruction
closing a Round 4 independent review Minor]`: comparison is
CASE-INSENSITIVE (Unicode `casefold()` after separator normalization),
on every platform, through ONE helper (`canonical()` / `same_path()`)
that identity, eligibility, and direct/central invalidation all share.

Why one rule and why this direction: the earlier version compared
case-SENSITIVELY, arguing that was fail-closed. That argument is only
true for the IDENTITY comparison ("is this the same occurrence?" --
treating `Foo.cs`/`foo.cs` as different costs at most an extra
re-validation). For STALENESS DETECTION it is exactly backwards: a
record whose stored path is `src/r.cs` while `git diff` reports the
change as `src/R.cs` (case-insensitive filesystem, `core.ignorecase`,
a tool that normalized case differently) would NEVER be seen as "the
same file changed", so a real edit at the sink went undetected and the
record kept being reused -- fail-OPEN, and permanent, since
`changed_files` is a per-change diff that is never re-examined. Two
different rules for the two uses would leave the inconsistency the
Round 4 reviewer flagged (identity strict, staleness lax = the record
survives forever); one case-insensitive rule closes the staleness gap
and costs identity only a theoretical collision requiring, on a
case-sensitive filesystem, two files differing solely by case AND an
identical category AND an identical ordered chain of
namespace-qualified `qualifiedSymbol`s -- disclosed, accepted.

`validate()` still RETURNS the path as given (original case and
Unicode form, for storage/display); only `canonical()`/`same_path()`
normalize to NFC and fold case, and only for comparison. See
`canonical()`'s docstring for exactly what that folding merges -- it
is more than upper/lower case.
"""

from __future__ import annotations

import unicodedata


class InvalidPathError(ValueError):
    """A path is not a valid repository-relative path."""


def normalize(raw: str) -> str:
    """Normalize separators (backslash -> forward slash) and collapse
    `./`/redundant segments, WITHOUT resolving `..` -- a `..` segment
    surviving normalization is exactly what `validate()` below must
    reject, so this function must never silently eat one.
    """
    if not isinstance(raw, str):
        raise InvalidPathError(f"path must be a string, got {raw!r}")
    if not raw:
        raise InvalidPathError("path must not be empty")
    posix_form = raw.replace("\\", "/")
    # posixpath.normpath collapses "a/./b" -> "a/b" and "a//b" -> "a/b"
    # but ALSO collapses "a/../b" -> "b" -- exactly the collapsing this
    # function must not do silently, since a `..` segment must be
    # rejected, not quietly resolved away. Do the safe subset of
    # normalization (separators, redundant slashes, "./") by hand
    # instead of delegating to normpath.
    parts = [p for p in posix_form.split("/") if p not in ("", ".")]
    # [ADDED, Batch 2 preflight, per explicit instruction closing a Round
    # 6 disclosure]: a segment that is nothing but whitespace (`" "`,
    # `"\t"`) names no file and used to pass straight through -- as a
    # whole path it even survived `validate()`'s empty check, since
    # `" "` is not `""`. Rejected here so every consumer of normalize/
    # validate/canonical (identity, reuse, invalidation) agrees. A
    # segment that merely CONTAINS whitespace (`"my file.cs"`) is a
    # legitimate file name and still passes.
    #
    # Scope of "whitespace" here is `str.strip()`, i.e. Unicode
    # White_Space. Format characters (general category Cf, e.g. U+200B
    # ZERO WIDTH SPACE, U+200D, U+FEFF) are NOT White_Space and are NOT
    # rejected: a segment made only of U+200B currently passes. No
    # policy on format characters in paths exists yet; that decision is
    # deferred to a later batch rather than widened here (Batch 2
    # independent review, extra finding; pinned by
    # tests/test_batch2_review_fixes.py).
    for p in parts:
        if not p.strip():
            raise InvalidPathError(f"path contains a whitespace-only segment: {raw!r}")
    return "/".join(parts)


def validate(raw: str) -> str:
    """Normalize `raw` and reject it if it is not a valid
    repository-relative path. Returns the normalized form.

    Rejects: empty, absolute (POSIX `/...`, Windows drive-letter
    `C:\\...` or `C:/...`, UNC `\\\\server\\share`), and any path
    containing a `..` segment (whether or not it would actually escape
    the repository root -- rejected unconditionally, per the "禁止 `..`
    跳出 repository" requirement, not merely "if it would escape").
    """
    if not isinstance(raw, str) or not raw:
        raise InvalidPathError(f"path must be a non-empty string, got {raw!r}")
    if len(raw) >= 2 and raw[1] == ":":
        raise InvalidPathError(f"absolute (drive-letter) path not allowed: {raw!r}")
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise InvalidPathError(f"UNC/absolute path not allowed: {raw!r}")
    posix_form = raw.replace("\\", "/")
    if posix_form.startswith("/"):
        raise InvalidPathError(f"absolute path not allowed: {raw!r}")
    normalized = normalize(raw)
    if any(seg == ".." for seg in normalized.split("/")):
        raise InvalidPathError(f"'..' path segment not allowed: {raw!r}")
    if not normalized:
        # [ADDED, per a round-2 independent review Minor]: `"."` and
        # `"./"` normalize to "" -- an empty repository-relative path
        # names no file at all and must never silently stand in for
        # "the whole repository" (a caller who actually meant that,
        # e.g. a central-component path prefix, must say so some other
        # way -- this module has no such wildcard).
        raise InvalidPathError(f"path normalizes to empty, which names no file: {raw!r}")
    return normalized


def canonical(raw: str) -> str:
    """The single comparison form for a repository-relative path, in
    this exact order: (1) `validate()` -- separators normalized,
    absolute/UNC/`..`/empty rejected; (2) Unicode NFD decomposition;
    (3) `casefold()`; (4) Unicode NFC recomposition (see the last
    paragraph for why (2)/(4) bracket the fold). EVERY path comparison in this package -- identity
    (`same_path`), eligibility's `hop_key`/check (c), and both
    invalidation mechanisms -- goes through this one function, so the
    rule cannot drift between them. Raises `InvalidPathError` on a
    malformed path; never returns a guess. NOT for storage: store
    `validate()`'s original result.

    [ADDED, per explicit instruction closing a Round 5 independent
    review Minor]: step (2). Without it, a record whose stored path was
    the NFC spelling of `src/café.cs` never matched a diff that
    reported the NFD spelling (macOS HFS+/APFS and several tools emit
    NFD), so `find_directly_stale` returned nothing and `decide_reuse`
    reused a record whose sink had changed -- the exact permanent
    fail-open the case rule was introduced to close, in a different
    representation.

    What `casefold()` merges -- disclosed precisely, per the same
    review: it is NOT "just case". It applies full Unicode case folding,
    so e.g. `ß` and `ss` compare equal (`src/Straße.cs` ==
    `src/STRASSE.cs`), as do other language-specific foldings. Two such
    names are distinct files on most filesystems; treating them as one
    path here errs toward invalidating more / reusing less (identity
    additionally needs an identical category and an identical ordered
    chain of namespace-qualified `qualifiedSymbol`s to collide) -- the
    accepted direction, same as the case rule itself.

    [CORRECTED, per explicit instruction closing a Round 6 independent
    review finding]: the Round 5 form `NFC(x).casefold()` was NOT a
    closed comparison key. `casefold()` does not preserve normalization
    form -- for the characters it decomposes (`ǰ` U+01F0, `ΐ`/`ΰ`, `ẖ`,
    Greek with ypogegrammeni, ...), a string that differs from another
    in BOTH case AND normalization form folded to two different
    code-point sequences (the reviewer enumerated ~1.05M letter+marks
    strings and found 458 such pairs, e.g. `ǰ` + U+0323 vs `J` + U+0323
    + U+030C) -- two keys for what Unicode's caseless-match definition
    (D145) calls one string, so a diff in the other spelling missed the
    stale record. The comparison form is now
    `NFC(NFD(x).casefold())`: decompose first so folding sees canonical
    order, fold, then recompose so the result is a stable form. This is
    idempotent (`canonical(canonical(x)) == canonical(x)`, tested) and
    collapsed the enumerated pairs to zero without merging anything
    D145 keeps distinct. `validate()`'s stored result is untouched; only
    the comparison key uses this form.
    """
    validated = validate(raw)
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", validated).casefold())


def same_path(a: str, b: str) -> bool:
    """True iff `a` and `b` name the same repository-relative path
    under this package's one path-comparison rule (`canonical()`)."""
    return canonical(a) == canonical(b)


def same_reachability_path(a, b) -> bool:
    """True iff two `reachabilityPath` sequences (each an iterable of
    mappings with `path`/`qualifiedSymbol` keys) match EXACTLY: same
    length, same order, every position matching on BOTH `path` (via
    `same_path`) AND `qualifiedSymbol` (exact string equality -- a
    symbol is not a filesystem path, so it is never run through path
    normalization).

    `[RENAMED, per explicit instruction closing a round-2 independent
    review Major]`: compares `qualifiedSymbol`, not the old bare
    `symbol` field -- see schema.py's own note on why. `lineRange`
    (when present) is deliberately NEVER read or compared here at all
    -- per explicit instruction it is evidence-location/diagnostic
    metadata only, never part of occurrence identity, so a pure line
    shift (e.g. a comment added above an unchanged hop) must never by
    itself change what this function returns.

    Comparing as an ORDERED sequence, element-by-element, is
    deliberate -- context-manifest-schema.md section 5.1 condition
    (iii) requires an exact ordered chain match, not a set/multiset
    comparison (which would let a path with hops in a different order,
    or a differently-shaped chain that happens to contain the same
    elements, wrongly match).
    """
    a = list(a)
    b = list(b)
    if len(a) != len(b):
        return False
    for entry_a, entry_b in zip(a, b):
        symbol_a = entry_a.get("qualifiedSymbol")
        symbol_b = entry_b.get("qualifiedSymbol")
        # [ADDED, per a Round 3 independent review Major, defense in
        # depth]: require both sides to actually BE non-empty strings
        # before comparing them, not just unequal. Plain `!=` would let
        # two hops that both OMIT qualifiedSymbol (both `.get()` return
        # `None`), or both carry an empty/whitespace string, compare
        # EQUAL to each other -- a spurious match on "both sides have no
        # real identity here" rather than a real one. This does not
        # depend on the caller-side data ever having been schema-
        # validated (a live candidate trace never is), so it holds
        # regardless of what validation layers exist elsewhere.
        if not (isinstance(symbol_a, str) and symbol_a.strip()):
            return False
        if not (isinstance(symbol_b, str) and symbol_b.strip()):
            return False
        if symbol_a != symbol_b:
            return False
        try:
            if not same_path(entry_a.get("path"), entry_b.get("path")):
                return False
        except InvalidPathError:
            return False
    return True
