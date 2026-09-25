# Hard links in RV-24, RV-26 and RV-37: evidence and threat model (2026-09-26)

**Question.** Revision 3 added a reparse-point check to three V4-release path fixtures, covering the file and every
directory from it up to the base. The revision-5 review asked whether a hard link inside the base directory defeats
that check. "The check does not detect hard links" is not by itself a vulnerability. This record establishes, per
case:
- whether an attacker can create such a link;
- what it could point to;
- whether the service would then serve unauthorised content.

**Result.**
- The check indeed does not detect hard links. This was verified on NTFS.
- None of the three cases gives an attacker any way to create one, so the attack is **not established**.
- The fixtures were not changed. No protection was added or claimed for hard links.

## Per case

| Case | Fixture | Base directory (in the case) | Attacker input | Any write path into the base? |
|---|---|---|---|---|
| RV-24 | `tests/fixtures/v4_release/public_document_download_nolinks_safe.cs` | `/var/app/published-manuals` | `fileName` query value (GET) | none: one read-only GET action, `PhysicalFile` |
| RV-26 | `tests/fixtures/v4_release/path_prefix_canonicalized_nolinks_safe.cs` | `/var/app/reports` | `reportName` argument of `ResolveReportPath` | none: a path helper that only returns a path |
| RV-37 | `tests/fixtures/v4_release/cross_file_public_manual_download_nolinks_safe/` | `/var/app/published-manuals` | `manualName` query value (GET) | none: GET action → service → path helper, `File.ReadAllBytes` |

In every case the attacker controls only a **name**, which is canonicalised and contained inside the base. The
content of the base directory is decided by whoever deploys or publishes into it, not by any code in the case.

## What a hard link would need

1. **A new name inside the base directory.** That requires write access to the base directory itself. No code in any
   of the three cases writes anywhere.
2. **The same filesystem.** A hard link cannot cross filesystems, and cannot name a directory.
3. **A target the linker could not simply copy.** Otherwise a hard link gives nothing that placing a copy in the
   published directory would not. On Linux, the platform these `/var/app/...` paths name, `fs.protected_hardlinks=1`
   (the usual distribution default) only lets a user hard-link a file they own or can read and write. So a publisher
   can only link what they could already publish.
   - The residual case is a system with `protected_hardlinks=0` and a local account that can write into the base but
     cannot read the linked file. That is a deployment condition outside every case. The kit does not confirm a
     finding on a condition the case does not show (`plays/finding-validation.md`), and this record does not claim
     that condition away.
   - `protected_hardlinks` behaviour and Windows' hard-link permission rules were **not tested here**.

A remote caller of any of the three endpoints has none of 1–3. The actor who has 1 already controls what the service
publishes.

## Evidence: the mechanism test (scratchpad, not part of the corpus)

**Setup.**
- The RV-26 and RV-37 helpers were compiled **unchanged except for their base-directory string**, pointed at a
  scratch directory.
- RV-24's checks were copied verbatim into a function.
- The build was .NET 8 on Windows 11 / NTFS, with 0 warnings and 0 errors.
- The scratch base held:
  - a normal file and a file in a subdirectory;
  - a **hard link** (Python `os.link`) to a file **outside** the base;
  - a **junction** (`mklink /J`) to the outside directory;
  - a symbolic link, which could **not** be created: WinError 1314, the privilege is not held.

| Requested name | RV-24 | RV-26 | RV-37 |
|---|---|---|---|
| `manual.pdf` (normal file) | accepted | accepted | accepted |
| `sub\sub.pdf` (subdirectory) | accepted | accepted | accepted |
| `hardlinked.pdf` (hard link to a file outside the base) | **accepted, outside content served** | **accepted** | **accepted** |
| `junction\secret.txt` (through a junction) | rejected | rejected | rejected |
| `symlinked.pdf` (symbolic link) | rejected only because the link does not exist: **not verified** | same | same |
| `..\outside\secret.txt` | rejected | rejected | rejected |

**What this shows.**
- The reparse-point check stops junctions, and `..` is stopped by containment.
- A hard link that is already in the base directory is served like any other file there.

**What it does not show.**
- that anyone can create such a link through the case — nothing in the case can;
- symbolic-link rejection on this machine;
- Linux behaviour.

## Consequence for the corpus

- RV-24, RV-26 and RV-37 stay expected-safe, with their `/3` fixtures unchanged. RV-24 and RV-26 passed in the
  revision-4 and revision-5 runs. RV-37 has not yet been reached by any run with this fixture.
- Their "no link ... is followed" wording means reparse points: symbolic links, junctions and mount points. It does
  **not** mean hard links. A hard link is not something that is followed; it is another name of the same file. Hard
  links are covered by this threat model, not by a check in the code.
- If a review CONFIRMS a hard-link finding on one of these rows, protocol rule 10 applies: it is reported as a failed
  case and not dismissed. It would then be classified as a fixture question to settle against this record.
