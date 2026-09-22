# V3 Slim Batch 7 — Pre-record (before verification)

Per user instruction (2026-09-22): record candidate, affected fixed
case(s), current load, expected savings, and possible missed security
rules *before* doing the semantic check — not after.

## Search for a second candidate (documented, not silently dropped)

Grepped every play for the same shape (a "See `references/X`" pointer
sentence) — only 2 exist in the whole kit:
`plays/configuration-security.md`'s IIS section (already minimal: one
pointer sentence + one non-redundant nuance, not a restated list — a
**good** counter-example, not a candidate) and
`plays/file-security.md`'s "Windows and macOS path semantics" section
below (the only one that also restates a full bulleted list the
reference already covers in more depth). Also checked `templates/attack-surface-map.md`
(a single non-repeating worked JSON example covering every node/edge
type once — no internal duplication found) and
`templates/project-security-baseline.md` (same shape, clean) as possible
second candidates; neither showed a comparable pattern. Proceeding with
**one** candidate, not forcing a second, per "最多 2 個" allowing fewer.

## Candidate: `plays/file-security.md`'s "Windows and macOS path semantics" vs. `references/windows-security.md`'s "Path semantics"

- **Location**: `plays/file-security.md:139-155` (17 lines: header, one
  framing sentence, a bulleted summary of Windows facts + macOS facts,
  then "See `references/windows-security.md` and
  `references/macos-security.md` for platform-specific detail.")
- **Authoritative detail already exists at**: `references/windows-security.md:6-40+`
  ("Path semantics" — same topics: case-insensitivity and which
  check-direction it actually breaks, `\`/`/` separator acceptance,
  drive letters, UNC paths, reserved device names, elaborated in much
  more depth, including the denylist-vs-allowlist bypass-direction
  nuance the play's summary omits) and `references/macos-security.md`
  (not yet re-read in this batch — will check before finalizing).

## Affected fixed case(s)

- **Case 3** (authenticated file-download endpoint) in `baseline.md` /
  `batch3-baseline.md`: loads `plays/file-security.md` (155 lines) +
  `references/aspnet-security.md` (149) + `references/windows-security.md`
  (117) + `plays/authorization.md` (98) = 519 lines routing-only total.
- Also relevant to any other case that routes to `plays/file-security.md`
  for the "File upload/download/paths" domain generally, not just case 3
  specifically — the section is part of the play's fixed content
  regardless of which reference also gets loaded.

## Current load (this section specifically)

17 lines within `plays/file-security.md`'s 155-line total.

## Expected savings if trimmed to a bare pointer

Replacing the bulleted summary with a short pointer sentence (matching
`plays/configuration-security.md`'s IIS section's shape) would reduce
this section to roughly 4 lines (header + one sentence), saving
approximately **13 lines** from `plays/file-security.md` (155 -> ~142),
which lowers case 3's routing-only total from 519 to approximately 506.

## Possible missed security rules if trimmed (to check, not assumed)

- The play's summary mentions specific facts (reserved device names,
  UNC paths, drive letters, case-insensitivity) that a reviewer might
  use as direct recognition cues while reading a diff, without first
  deciding to open `references/windows-security.md` separately.
- Unlike `plays/file-security.md`'s own internal pointer being the
  *only* mechanism steering a reader to `references/windows-security.md`,
  `skills/security-review/SKILL.md`'s "Where to look next" coarse table
  **already independently lists** `references/windows-security.md` for
  the "File upload/download/paths" domain ("plus `references/windows-security.md`
  or `references/macos-security.md` for the deployment OS") — meaning the
  outer routing layer, not just this play's own internal pointer,
  already guarantees the reference gets loaded for this domain. This is
  the load-bearing question the semantic check below needs to confirm,
  not assume.
