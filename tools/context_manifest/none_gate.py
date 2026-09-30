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
- STOP_NONE requires, all together: every given file read, every file plain UTF-8 text (no NUL byte; the whole
  file decodes strictly as UTF-8), `required_domains()` completed, and no domain required. Nothing else can give it.
- No failure returns STOP_NONE. An unreadable or missing file, a file that is not plain UTF-8 (UTF-16/32, a legacy
  encoding, a binary file), an empty file list, a bad argument, or an exception from
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

import json
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


_WIDE = ("utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")
_NON_ASCII = re.compile(r"[^\x00-\x7f]")
_WIDE_LIMIT = 1024 * 1024   # bytes; above this, a file that is not plain UTF-8 gets no UTF-16/32 detection readings


def plain_utf8_problem(data: bytes):
    """None if the bytes are plain UTF-8 text -- no NUL byte, and the whole file decodes strictly as UTF-8 (a UTF-8
    BOM is allowed) -- else why not. Only such a file can let the gate stop at NONE. [V4 release hardening, policy]

    This is the whole reliability rule, on purpose. It does not try to recognise UTF-16/32, legacy encodings or
    binary files as "reliable": a decoder that accepts some bytes is not evidence that the file's real text was read.
    Every other file is reported unread, so the gate returns MANUAL_CHECK (or TARGETED_EXCEPTION if a signal is
    found anyway).

    Not covered, disclosed: a 7-bit encoding whose bytes are all ASCII (UTF-7, ISO-2022-*, HZ) is valid UTF-8, so it
    counts as plain here, although its real text differs from its UTF-8 reading."""
    if b"\x00" in data:
        return "not plain UTF-8 text: it contains NUL bytes"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "not plain UTF-8 text: it is not valid UTF-8"
    return None


def _readings(data: bytes):
    """The texts the floor searches for one file, and why the file cannot be relied on (None if it can).

    A plain UTF-8 file (see `plain_utf8_problem`) is read once, and that reading is the one the STOP_NONE decision
    rests on. Any other file is unreliable, full stop. Its readings are for DETECTION only -- to take the exception
    when a signal pair is visible anyway, never to allow STOP_NONE:
    - UTF-8 with bad bytes replaced (keeps ASCII for ASCII-compatible legacy encodings);
    - for a file with NUL bytes (up to _WIDE_LIMIT), UTF-16 LE/BE at both alignments and UTF-32 LE/BE at all four.
    Every reading, plain files' included, is also added with each non-ASCII character replaced by a space, so a
    signal glued to a non-ASCII letter (a CJK character right before `ConfigureApplicationCookie(`) still matches.
    Readings never decide reliability: that is `plain_utf8_problem` alone. The floor only adds domains, so extra
    readings can only add."""
    why = plain_utf8_problem(data)
    texts = [data.decode("utf-8", errors="replace")]
    if why is not None and b"\x00" in data and len(data) <= _WIDE_LIMIT:
        for enc in _WIDE:
            width = 2 if enc.startswith("utf-16") else 4
            texts += [data[offset:].decode(enc, errors="replace") for offset in range(width)]
    texts += [y for y in (_NON_ASCII.sub(" ", x) for x in texts) if y not in texts]
    return texts, why


def read_scope_texts(paths: Iterable[str], root: str = ".") -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Read each file's whole text. Returns (texts keyed by the given path, problems). A file's text is all of its
    readings (see `_readings`) joined. Every file that is not plain UTF-8 is a problem, so the gate cannot stop at
    NONE on it."""
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


def exception_manifest(decision: NoneGateDecision, target_files: Iterable[str]):
    """The signal-pair exception's manifest, built by the approved entry and validated. [V4 release hardening, r11]

    Calls `orchestrator.produce_manifest()` in TARGETED mode with item 0's NONE classification and the SAME file
    texts the gate read as `scope_texts`, so the signal floor adds the domain exactly as it did for the gate. No token
    is offered, so no Jev call is made and the built-in producer runs. Nothing is filled in by hand.

    Returns (manifest, None) when the manifest passed the validator and carries the gate's domains, else (None, why).
    A caller must never replace a failed manifest with a hand-written one."""
    if decision.action != TARGETED_EXCEPTION:
        return None, "no signal-pair exception"
    try:
        from . import orchestrator
        from .validator import Classification
        res = orchestrator.produce_manifest(
            review_mode="TARGETED",
            classification=Classification(sensitivity="NONE", implicated_domains=frozenset()),
            target_change_files=list(target_files),
            scope_texts=decision.scope_texts,
            token_provider=lambda: None,
        )
    except Exception as exc:  # noqa: BLE001 -- a manifest that could not be built is never replaced by a guess
        return None, f"the manifest could not be built ({type(exc).__name__})"
    m = res.manifest
    problems = []
    if res.produced_by != "built_in" or res.audit.get("jev_called"):
        problems.append("not the built-in producer")
    if not (isinstance(m.get("validity"), dict) and m["validity"].get("passed") is True):
        problems.append("did not pass validation")
    if not set(decision.domains) <= set(m.get("domains") or ()):
        problems.append("does not carry the gate's domains")
    if m.get("reviewMode") != "TARGETED" or m.get("sensitivity") != "NONE":
        problems.append("is not a TARGETED/NONE manifest")
    if problems:
        return None, "the manifest " + "; ".join(problems)
    return m, None


def manifest_line(manifest) -> str:
    """One line, as the CLI prints it after `manifest: `. Canonical JSON (sorted keys) of the validated manifest."""
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
