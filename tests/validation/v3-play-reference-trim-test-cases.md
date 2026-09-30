# V3 Play-Reference Trim Test Cases

Validates that trimming a play's inline summary of reference material
(replacing a restated fact list with a pointer, per V3 Slim's
reduction batches) does not remove a reviewer's actual path to that
detail — the routing mechanism that reaches the reference must be
independent of the play's own trimmed text, not just assumed to be.
See `tests/validation/README.md` for how to run a validation pass. Add
a case here whenever a future Slim batch trims a play's reference
summary, following case 1's shape.

## Case 1: `plays/file-security.md`'s Windows/macOS path semantics trim

Before V3 Slim batch 7, `plays/file-security.md:139-155` restated a
bulleted summary of Windows and macOS path facts (case-insensitivity,
drive letters, UNC paths, reserved device names, etc.) that
`references/windows-security.md` and `references/macos-security.md`
already covered in more depth, then pointed to those files. The batch
trimmed the section to a pointer plus a parenthetical topic list,
matching `plays/configuration-security.md`'s existing IIS-section shape.

| Step | Check | Result |
|---|---|---|
| 1 | Does `skills/security-review/SKILL.md`'s "Where to look next" coarse table route to `references/windows-security.md`/`references/macos-security.md` for the "File upload/download/paths" domain, independent of `plays/file-security.md`'s own text? | Yes — `skills/security-review/SKILL.md:131`'s row explicitly names both references for this domain. This routing does not read or depend on `plays/file-security.md`'s content. |
| 2 | Does any existing fixture or test case rely on the specific facts that were trimmed (drive letters, UNC paths, reserved device names, Unicode normalization, case-insensitivity)? | No — checked (`grep` across `tests/`): zero matches. `tests/fixtures/path_prefix_before_canonicalization_deceptive.cs`/`_safe.cs` (the closest related fixtures) exercise canonicalization-ordering and encoding tricks generically, not any Windows/macOS-specific fact. |
| 3 | Fixed case 3 (authenticated file-download endpoint, `baseline.md`/`batch3-baseline.md`) — does its routing outcome change? | No — still routes to the same 4 files (`plays/file-security.md`, `references/aspnet-security.md`, `references/windows-security.md`, `plays/authorization.md`); only `plays/file-security.md`'s own line count drops (155 -> 145), lowering the case's routing-only total from 519 to 509. |
| 4 | Does a reviewer who reaches `plays/file-security.md` via `skills/security-review/references/quick-reference.md`'s row 24 directly (which names only `plays/file-security.md`, no reference — a pre-existing characteristic, not introduced by this trim, see `baseline.md`'s case-3 finding) lose anything they had before? | No new loss — the play's summary was already a less complete version of the reference material before this trim (it never covered the denylist-vs-allowlist bypass-direction nuance or the Unicode NFC/NFD issue); it was not a reliable standalone substitute either way. |

**Result: routing guarantee confirmed independent of the trimmed
content; no existing case depends on what was removed.**
