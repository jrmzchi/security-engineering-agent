"""Shared secret-shape heuristic -- the ONE pattern list both
`tools/feedback_store` (record validation) and `tools/context_manifest`
(outbound Jev request redaction, V4 Batch 2) apply.

Moved here from `tools/feedback_store/schema.py` in Batch 2 so the two
packages can share it WITHOUT either importing the other:
`tools/feedback_store` must never import `tools/context_manifest`
(its own negative-control test), and `tools/context_manifest` must
never import `tools/feedback_store` (its scanner selection must have no
way to observe the Feedback store). A third, dependency-free module is
the only place a shared rule can live without breaking either
guarantee. Standard library only.

This is a DISCLOSED HEURISTIC, not a guarantee: it catches the common
accidental shapes (a real-looking AWS key, a PEM block, an inline
`key: "..."` / `password=...` assignment with a long value) and will
miss a secret in an unrecognized shape. Its job is a cheap fail-closed
backstop -- a caller must never treat "returned False" as proof a value
is safe.
"""

from __future__ import annotations

import re
from typing import Any, Iterator, Mapping, Sequence, Tuple

SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),                       # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),     # PEM private key
    # `\b` is defined relative to `\w`, which includes `_`, so a leading
    # `\bsecret\b` could never match inside "client_secret" -- the exact
    # snake_case shape most config/env-style secrets use; no leading
    # boundary on purpose. `['\"]?` before `[:=]` catches the JSON
    # quoted-key shape (`"api_key": "..."`).
    re.compile(r"(?i)(secret|password|api[_-]?key|token)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9+/=_\-@!#$%^&*.]{12,}"),
)


def looks_like_secret(value: str) -> bool:
    return any(p.search(value) for p in SECRET_PATTERNS)


REDACTED_KEY = "<redacted-key>"


def find_secret_paths(value: Any, path: str = "") -> Iterator[Tuple[str, str]]:
    """Walk any combination of mapping/list/tuple/string and yield
    `(field_path, kind)` for every string -- VALUE or mapping KEY -- that
    looks like a secret. Yields the PATH only, never the offending text,
    so a caller can build an error message that does not echo the
    secret. `kind` is "key" or "value". Non-string keys are skipped (they
    are not text).

    A mapping key that looks like a secret is replaced by the fixed
    segment `<redacted-key>` in its own path AND in every descendant
    path, so a deeper hit can never re-introduce the secret key.
    [FIXED, Batch 2 independent review #1: descendant paths used to be
    built from the raw key.]"""
    if isinstance(value, str):
        if looks_like_secret(value):
            yield (path or "<root>", "value")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                secret_key = looks_like_secret(key)
                segment = REDACTED_KEY if secret_key else key
                child = f"{path}.{segment}" if path else segment
                if secret_key:
                    yield (child, "key")
            else:
                child = f"{path}.<non-string-key>" if path else "<non-string-key>"
            yield from find_secret_paths(item, child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for i, item in enumerate(value):
            yield from find_secret_paths(item, f"{path}[{i}]")
