"""Feedback store kit runtime (V4 Batch 1).

Standard-library-only Python package implementing
work/v4-planning/context-manifest-schema.md sections 4/5/5.1/5.2 and
work/v4-planning/v4-design.md section 3's four named mechanisms
(Evidence Reuse, Selective Invalidation, Selective Revalidation,
Feedback Learning) against a new, separate `.security/feedback.json`
store -- deliberately not folded into `.security/baseline.json` or
`.security/attack-surface.json`, to isolate this new schema from those
two already-shipped V3 formats.

No Jev runtime call exists anywhere in this package. Every judgment
this package's own code cannot make mechanically (is a changed file a
central/load-bearing component; does re-inspected code still match a
recorded natural-language `safetyPattern`) is left as an explicit
input the calling agent supplies, the same way
`tools/context_manifest/domains.py`'s DEEP algorithm leaves
architecture-fact recognition to the calling agent rather than
inventing brittle content-pattern heuristics in code.
"""
