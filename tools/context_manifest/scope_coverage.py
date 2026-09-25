"""Group 3 Scope coverage check -- implementation-batches.md Batch 0 criterion 7.

Live-parses each of the four Group 3 plays' current "## Scope" section
(criterion 7a) and compares that item set, symmetrically, against
domains.py's own per-domain rule-table item labels (criterion 7c). This
is deliberately NOT a comparison against a second, hand-maintained
coverage-map data file -- domains.py's rule table already IS the
coverage map (each item's key is exactly the item this repository
claims to have a rule, and therefore a fixture-backed isolation test,
for -- see tests/test_domains.py's coverage-completeness test, which
fails loudly if any item in this table lacks a registered isolation
case). Introducing a THIRD copy of the 42 item labels (a coverage-map
file distinct from both the play's prose and this rule table) would
recreate exactly the "same list, kept in more than one place" defect
this whole redesign exists to eliminate -- see
context-manifest-schema.md section 3a's own revision history.

Never hardcodes the item count or the item text anywhere in this
module -- every comparison reads the play file fresh at call time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple

from . import domains

REPO_ROOT = Path(__file__).resolve().parents[2]

# domain -> the authoritative play file, per
# context-manifest-schema.md section 3a's "Authoritative source, per
# domain" table. This mapping (which FILE is authoritative for which
# domain) is structural and stable; it is not the thing criterion 7
# guards against drifting -- the ITEM LIST inside each file is.
PLAY_FILES: Mapping[str, str] = {
    "web-security": "plays/web-security.md",
    "api-security": "plays/api-security.md",
    "data-security": "plays/data-security.md",
    "file-security": "plays/file-security.md",
}

_SCOPE_HEADING_RE = re.compile(r"^##\s+Scope\s*$", re.MULTILINE)
_FENCE_RE = re.compile(r"```text\r?\n(.*?)```", re.DOTALL)


class ScopeParseError(RuntimeError):
    """Raised when a play's Scope section cannot be reliably parsed.

    context-manifest-schema.md's own execution rule: "An implementer
    that cannot enumerate a play's current Scope items reliably ... must
    default the domain to applicable rather than skip the check
    silently" -- callers of parse_scope_items must treat this as a hard
    failure of the coverage check (criterion 7e's ERROR exit code), not
    as "zero items, therefore nothing to compare".
    """


def parse_scope_items(play_path: Path) -> Tuple[str, ...]:
    """Parse the fenced item list immediately under a play's "## Scope" heading.

    Structural, not line-number-based (criterion 7a's own requirement):
    finds the "## Scope" heading, then the first ```text fenced block
    after it, and returns its non-blank lines verbatim (no
    normalization beyond stripping surrounding whitespace -- the item
    text itself, exactly as the play states it, is the comparison key).
    """
    text = play_path.read_text(encoding="utf-8")
    heading_match = _SCOPE_HEADING_RE.search(text)
    if not heading_match:
        raise ScopeParseError(f"no '## Scope' heading found in {play_path}")
    remainder = text[heading_match.end():]
    fence_match = _FENCE_RE.search(remainder)
    if not fence_match:
        raise ScopeParseError(f"no fenced ```text block found under '## Scope' in {play_path}")
    lines = [line.strip() for line in fence_match.group(1).splitlines()]
    items = tuple(line for line in lines if line)
    if not items:
        raise ScopeParseError(f"'## Scope' fenced block in {play_path} parsed to zero items")
    return items


@dataclass(frozen=True)
class DomainCoverageResult:
    domain: str
    live_items: Tuple[str, ...]
    implemented_items: Tuple[str, ...]
    missing_from_implementation: Tuple[str, ...]  # in play, no rule
    stale_in_implementation: Tuple[str, ...]  # rule exists, not in play

    @property
    def ok(self) -> bool:
        return not self.missing_from_implementation and not self.stale_in_implementation


def check_domain(domain: str, repo_root: Path = REPO_ROOT) -> DomainCoverageResult:
    if domain not in PLAY_FILES:
        raise ValueError(f"not a Group 3 domain: {domain!r}")
    play_path = repo_root / PLAY_FILES[domain]
    live_items = parse_scope_items(play_path)
    implemented_items = tuple(domains.group3_scope_items(domain))
    live_set = set(live_items)
    implemented_set = set(implemented_items)
    return DomainCoverageResult(
        domain=domain,
        live_items=live_items,
        implemented_items=implemented_items,
        missing_from_implementation=tuple(sorted(live_set - implemented_set)),
        stale_in_implementation=tuple(sorted(implemented_set - live_set)),
    )


def check_all(repo_root: Path = REPO_ROOT) -> Dict[str, DomainCoverageResult]:
    return {domain: check_domain(domain, repo_root) for domain in PLAY_FILES}


def format_report(results: Mapping[str, DomainCoverageResult]) -> str:
    lines = ["SCOPE_COVERAGE"]
    any_hit = False
    for domain, result in results.items():
        if result.ok:
            continue
        any_hit = True
        for item in result.missing_from_implementation:
            lines.append(f"  {PLAY_FILES[domain]}")
            lines.append(f"  domain={domain} item=\"{item}\" -- no rule/fixture coverage (new or renamed Scope item)")
        for item in result.stale_in_implementation:
            lines.append(f"  {PLAY_FILES[domain]}")
            lines.append(f"  domain={domain} item=\"{item}\" -- rule/fixture references an item no longer in this play's Scope (removed or renamed)")
    if not any_hit:
        return ""
    return "\n".join(lines)
