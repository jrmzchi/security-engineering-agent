"""Outbound request redaction gate for the Jev producer -- V4 Batch 2.

Minimum-data principle (batch instruction, Part 5): only decision
inputs go to Jev, and even those are scanned before they leave the
process. Scans every string -- mapping keys AND values, at every depth
of mapping/list/tuple -- with the SAME heuristic the Batch 1 record
validators apply to stored records (`tools/secret_heuristic.py`, a
neutral module; this package never imports the record-store package,
and that package never imports this one). On any hit: fail closed -- the
request is NOT sent, the orchestrator falls back to the built-in
producer, and the refusal names the field path only, never the text
(a secret-shaped mapping key appears as `<redacted-key>` in its own
path and every descendant path).

This gate is a secret-SHAPE heuristic only. It does not bound the
length or the kind of content in free-text fields; keeping those to
minimum decision data is the caller's responsibility
(skills/security-review/SKILL.md step 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

from .. import secret_heuristic


@dataclass(frozen=True)
class RedactionRefusal:
    """Where a suspected secret was found (paths only, never values)."""

    hits: Tuple[Tuple[str, str], ...]  # (field_path, "key" | "value")

    def describe(self) -> str:
        return "; ".join(f"{kind} at {path}" for path, kind in self.hits)


def scan_request(state: Any, questions: Any) -> List[Tuple[str, str]]:
    hits = list(secret_heuristic.find_secret_paths(state, "state"))
    hits += list(secret_heuristic.find_secret_paths(questions, "questions"))
    return hits


def refuse_if_secret(state: Any, questions: Any) -> "RedactionRefusal | None":
    hits = scan_request(state, questions)
    if hits:
        return RedactionRefusal(hits=tuple(hits))
    return None
