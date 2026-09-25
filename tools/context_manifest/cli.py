"""CLI entry points invoked by scripts/{windows,macos}/consistency-check.*.

Both platform scripts call this module as a subprocess and relay its
exit code -- neither reimplements any judgment logic of its own (see
scope_coverage.py's module docstring for why a second, independently
maintained copy of this logic is exactly the defect shape this whole
mechanism exists to prevent).

Usage:
    python -m tools.context_manifest.cli scope-coverage-check

Exit codes (matching scripts/*/consistency-check.*'s existing
convention):
    0   PASS -- no drift between the four Group 3 plays' live Scope
        sections and this package's rule table.
    1   REVIEW_REQUIRED -- drift detected. Unlike this tool's other
        categories, every SCOPE_COVERAGE hit is a confirmed defect
        requiring a code change, not a judgment call (see
        plays/repository-consistency.md's SCOPE_COVERAGE entry).
    2   ERROR -- the check itself could not run (a play's Scope section
        could not be parsed at all, or an unexpected exception).
"""

from __future__ import annotations

import sys

from . import scope_coverage

# [DISCLOSED, per independent review]: this module's own exit-code
# contract (0/1/2) can collide with Python's default uncaught-exception
# exit code (1), which would be indistinguishable from a genuine
# REVIEW_REQUIRED SCOPE_COVERAGE hit to a caller that only inspects the
# exit code. main() below catches any exception _scope_coverage_check
# itself doesn't already handle and maps it to ERROR (2). This does
# NOT cover an interpreter too old to import this file at all --
# `from __future__ import annotations` (used throughout this package)
# itself requires Python 3.7+, so an incompatible interpreter fails
# before any code in this module can run. That check belongs, and is
# implemented, in the calling wrapper script's own interpreter-
# candidate probe (scripts/{windows,macos}/consistency-check.*), not
# here -- see those scripts' own comments.


def _scope_coverage_check() -> int:
    try:
        results = scope_coverage.check_all()
    except scope_coverage.ScopeParseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive, mirrors
        # consistency-check.*'s own "filesystem error" ERROR case.
        print(f"ERROR: scope coverage check failed to run: {exc}", file=sys.stderr)
        return 2

    report = scope_coverage.format_report(results)
    if not report:
        print("SCOPE_COVERAGE")
        print("PASS")
        return 0
    print(report)
    print("")
    print("REVIEW_REQUIRED")
    return 1


_COMMANDS = {
    "scope-coverage-check": _scope_coverage_check,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in _COMMANDS:
        print(f"Usage: python -m tools.context_manifest.cli <{'|'.join(_COMMANDS)}>", file=sys.stderr)
        return 2
    try:
        return _COMMANDS[argv[0]]()
    except Exception as exc:  # pragma: no cover - defensive
        # Anything not already caught inside the command itself (e.g. a
        # bug in format_report, not just check_all) still maps to
        # ERROR (2), never Python's default uncaught-exception exit
        # code (1) -- which this module's own contract also uses for
        # REVIEW_REQUIRED, and the two must never be indistinguishable
        # to a caller that only inspects the exit code.
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
