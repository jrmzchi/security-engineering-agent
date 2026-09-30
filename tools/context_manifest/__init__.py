"""Context Manifest kit runtime (V4 Batch 0).

Standard-library-only Python package implementing the deterministic
logic named in work/v4-planning/context-manifest-schema.md and
work/v4-planning/v4-design.md: the DEEP domain-applicability algorithm
(section 3a), the manifest validity checker (section 3), the merged
review-budget entry point (v4-design.md section 7), and the Group 3
Scope coverage check (implementation-batches.md Batch 0 criterion 7).

This package is invoked identically from scripts/windows/*.ps1 and
scripts/macos/*.sh (thin wrappers only -- see cli.py) so both platforms
run exactly one implementation, never two independently maintained
copies. No third-party dependency: everything here uses only the
Python 3 standard library.
"""
