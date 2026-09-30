"""The NONE gate: the check a change must pass before it may stop at NONE. [V4 release hardening]

Item 0 -- the sensitivity and domain classification -- is agent reasoning, not code. The workflow's "NONE -> stop
here" (plays/secure-development-workflow.md) comes before skills/security-review step 1, which is the only other
place the signal floor (signal_floor.py) runs. So without this gate, an agent that classifies a change NONE and does
not notice the CSRF signal pair never runs the deterministic check at all.

    the change's files -> read their whole texts -> signal_floor.required_domains()
        |- no domain required               -> STOP_NONE           (cli exit 0)
        |- a domain required (web-security) -> TARGETED_EXCEPTION  (cli exit 1)
        '- a file unreadable, no files, or
           the check itself failed          -> MANUAL_CHECK        (cli exit 2)

The scope is the files the change touches as they are after it (untracked files included, deleted files left out),
and each file's WHOLE text, not the diff: that matches the floor's own definition and is the conservative direction.
It can fire for a comment-only change to a file that already holds the pair; the cost is one play read.

What this guarantees:
- `decide()` calls `signal_floor.required_domains()` on the texts it read before it can return STOP_NONE.
- No failure returns STOP_NONE. An unreadable or missing file, a file that looks like UTF-16/32 but cannot be decoded
  reliably, an empty file list, a bad argument, or an exception from
  the floor returns MANUAL_CHECK with the reason. When the files that could be read already require a domain, the
  result is TARGETED_EXCEPTION even if others could not be read: the unread files cannot remove a domain. The
  unread files are returned separately (`unread`, and `unread:` lines from the CLI) so the report can say so.
- The CLI exits 0 only for STOP_NONE. Any other exit -- including Python's own exit 1 for an interpreter that cannot
  import this package -- means "do not stop at NONE".

What it does not guarantee: that the agent calls it. The workflow is Markdown that the agent follows. The documents
require the gate before every NONE stop and give a manual check for when it cannot run, but nothing in code can force
an agent that skips both. This is a disclosed limit, not a mechanical guarantee.

Nothing here prints or stores file contents. Reasons name files by the path the caller gave.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable as _Iterable
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Mapping, Tuple

from . import signal_floor

STOP_NONE = "STOP_NONE"
TARGETED_EXCEPTION = "TARGETED_EXCEPTION"
MANUAL_CHECK = "MANUAL_CHECK"


@dataclass(frozen=True)
class NoneGateDecision:
    action: str                                              # STOP_NONE | TARGETED_EXCEPTION | MANUAL_CHECK
    domains: FrozenSet[str] = frozenset()                    # the domains the exception reviews
    reasons: Tuple[str, ...] = ()                            # why
    unread: Tuple[str, ...] = ()                             # given files the gate could not read, and why
    scope_texts: Mapping[str, str] = field(default_factory=dict)  # the texts checked: pass the same to
    #                                                          produce_manifest(scope_texts=...) on the exception path


# BOM -> the encodings it can mean, checked longest first (FF FE 00 00 is UTF-32 LE, or UTF-16 LE text that starts
# with U+0000).
_BOMS = (
    (b"\x00\x00\xfe\xff", ("utf-32-be",)),
    (b"\xff\xfe\x00\x00", ("utf-32-le", "utf-16-le")),
    (b"\xfe\xff", ("utf-16-be",)),
    (b"\xff\xfe", ("utf-16-le",)),
)
_WIDE = ("utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")


_NON_ASCII = re.compile(r"[^\x00-\x7f]")
_WIDE_LIMIT = 1024 * 1024   # bytes; a larger file with NUL bytes is not decoded as UTF-16/32 (MANUAL_CHECK)


def _readings(data: bytes):
    """All readings of one file's bytes, and why it cannot be relied on (None if it can). [V4 release hardening]

    Every signal is ASCII. The UTF-8 reading (bad bytes replaced) keeps ASCII intact for UTF-8 and for every
    ASCII-compatible legacy encoding (Big5, Shift-JIS, GBK, Latin-1, ...). It does not for UTF-16/UTF-32, where every
    ASCII character carries a 0x00 byte. So for a file that holds a NUL byte, whatever its BOM says:
    - UTF-16 LE/BE at both code-unit alignments and UTF-32 LE/BE at all four are decoded (bad units replaced), so each
      segment of a file whose byte order, width or alignment changes part-way -- or disagrees with its BOM -- is read
      correctly by one of them;
    - a UTF-16/32 BOM's own encoding(s) are decoded after it, NUL or not.
    Every reading is also added with each non-ASCII character replaced by a space. A wrong-alignment or wrong-encoding
    neighbour then cannot glue itself to an ASCII signal and break a `\b` boundary, and non-ASCII route text cannot
    cut a pattern. All readings are checked together; the floor only adds domains, so extra readings can only add.

    The file cannot be relied on (the caller must not stop at NONE on it, MANUAL_CHECK) when:
    - it has a UTF-16/32 BOM that its named encoding(s) cannot decode strictly;
    - it has NUL bytes and no BOM, and none of UTF-16 LE/BE, UTF-32 LE/BE decodes it strictly (a binary file, say);
    - it has NUL bytes and is larger than _WIDE_LIMIT: decoding it that many ways would cost too much.

    Not covered: an encoding that is neither ASCII-compatible nor UTF-16/32 (EBCDIC, UTF-7); a signal whose own
    characters are malformed, or whose characters are split across two encodings."""
    texts = [data.decode("utf-8", errors="replace")]
    why = None
    has_nul = b"\x00" in data
    if has_nul and len(data) > _WIDE_LIMIT:
        why = f"NUL bytes in a file over {_WIDE_LIMIT // (1024 * 1024)} MiB, not decoded as UTF-16/32"
    else:
        for bom, encodings in _BOMS:
            if data.startswith(bom):
                body = data[len(bom):]
                strict = False
                for enc in encodings:
                    texts.append(body.decode(enc, errors="replace"))
                    try:
                        body.decode(enc)
                        strict = True
                    except UnicodeDecodeError:
                        pass
                if not strict:
                    why = "UTF-16/32 BOM, but its encoding does not decode the file"
                break
        if has_nul:
            strict = False
            for enc in _WIDE:
                width = 2 if enc.startswith("utf-16") else 4
                for offset in range(width):
                    texts.append(data[offset:].decode(enc, errors="replace"))
                try:
                    data.decode(enc)
                    strict = True
                except UnicodeDecodeError:
                    pass
            if not strict and why is None and not any(data.startswith(b) for b, _ in _BOMS):
                why = "NUL bytes, but no UTF-16/32 decoding accepts the file"
    texts += [y for y in (_NON_ASCII.sub(" ", x) for x in texts) if y not in texts]
    return texts, why


def read_scope_texts(paths: Iterable[str], root: str = ".") -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Read each file's whole text. Returns (texts keyed by the given path, problems). A file's text is all of its
    readings (see `_readings`) joined. A file that looks like UTF-16/32 but that no candidate decodes reliably is a
    problem, so the gate cannot stop at NONE on it."""
    texts: Dict[str, str] = {}
    problems = []
    for p in paths:
        if not isinstance(p, str) or not p.strip():
            problems.append(f"{p!r}: not a file path")
            continue
        full = os.path.join(root, p)
        if not os.path.isfile(full):
            problems.append(f"{p}: not found or not a regular file")
            continue
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            problems.append(f"{p}: unreadable ({type(exc).__name__})")
            continue
        readings, why = _readings(data)
        texts[p] = "\n".join(readings)
        if why is not None:
            problems.append(f"{p}: cannot be decoded reliably ({why})")
    return texts, tuple(problems)


def decide(paths: Iterable[str], root: str = ".") -> NoneGateDecision:
    """May this change stop at NONE? See the module docstring for the three results."""
    if isinstance(paths, (str, bytes)) or not isinstance(paths, _Iterable):
        return NoneGateDecision(MANUAL_CHECK, reasons=("the NONE gate needs a list of file paths",))
    try:
        paths = list(paths)
    except Exception as exc:  # noqa: BLE001
        return NoneGateDecision(MANUAL_CHECK, reasons=(f"the file list could not be read ({type(exc).__name__})",))
    if not paths:
        return NoneGateDecision(MANUAL_CHECK, reasons=("no files given: the NONE gate needs the change's files",))
    try:
        texts, problems = read_scope_texts(paths, root)
    except Exception as exc:  # noqa: BLE001 -- a check that could not run is never a NONE stop
        return NoneGateDecision(MANUAL_CHECK, reasons=(f"reading the scope failed ({type(exc).__name__})",))
    try:
        floor = signal_floor.required_domains(texts)
    except Exception as exc:  # noqa: BLE001
        return NoneGateDecision(MANUAL_CHECK, reasons=(f"the signal floor raised {type(exc).__name__}",),
                                unread=problems, scope_texts=texts)
    if floor.domains:
        # The unread files cannot remove a domain today (one rule, add-only). They are reported, not dropped: the
        # exception's report lists them as not covered. Re-check this branch if the floor ever gains a second rule.
        return NoneGateDecision(TARGETED_EXCEPTION, domains=floor.domains, reasons=floor.reasons, unread=problems,
                                scope_texts=texts)
    if problems:
        return NoneGateDecision(MANUAL_CHECK, reasons=("some given files could not be read",), unread=problems,
                                scope_texts=texts)
    return NoneGateDecision(STOP_NONE, reasons=floor.reasons, scope_texts=texts)
