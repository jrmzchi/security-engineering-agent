"""CLI entry points invoked by scripts/{windows,macos}/consistency-check.*.

Both platform scripts call this module as a subprocess and relay its
exit code -- neither reimplements any judgment logic of its own (see
scope_coverage.py's module docstring for why a second, independently
maintained copy of this logic is exactly the defect shape this whole
mechanism exists to prevent).

Usage:
    python -m tools.context_manifest.cli scope-coverage-check
    python -m tools.context_manifest.cli none-gate [--root DIR] FILE...
    (run from the kit's root; FILE paths are relative to DIR, the
    repository under review)

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

`none-gate` ([V4 release hardening], see none_gate.py) is run before a
change stops at NONE, on the change's files. Its exit codes follow the
same shape:
    0   STOP_NONE -- no signal pair; the NONE stop stands.
    1   TARGETED_EXCEPTION -- a signal pair requires a domain; review it
        (plays/secure-development-workflow.md's NONE row).
    2   MANUAL_CHECK -- the gate could not decide (a file unreadable, no
        files given, or the check failed); do the manual check instead.
Only exit 0 permits the NONE stop. It prints no file contents. Each
`unread: <path>: <why>` line names a given file the gate could not read.

"""

from __future__ import annotations

import sys

from . import none_gate, scope_coverage

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


def _none_gate(args) -> int:
    root = "."
    if args[:1] == ["--root"]:
        if len(args) < 2:
            print("NONE_GATE")
            print("MANUAL_CHECK")
            print("reason: --root needs a directory")
            return 2
        root, args = args[1], args[2:]
    decision = none_gate.decide(args, root=root)
    print("NONE_GATE")
    if decision.action == none_gate.TARGETED_EXCEPTION:
        print(f"{decision.action} {' '.join(sorted(decision.domains))}")
    else:
        print(decision.action)
    for reason in decision.reasons:
        print(f"reason: {reason}")
    for item in decision.unread:
        print(f"unread: {item}")
    return {none_gate.STOP_NONE: 0, none_gate.TARGETED_EXCEPTION: 1}.get(decision.action, 2)


_COMMANDS = {
    "scope-coverage-check": lambda args: _scope_coverage_check(),
    "none-gate": _none_gate,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in _COMMANDS:
        print(f"Usage: python -m tools.context_manifest.cli <{'|'.join(_COMMANDS)}>", file=sys.stderr)
        return 2
    try:
        return _COMMANDS[argv[0]](list(argv[1:]))
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
