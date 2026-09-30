# Publish commit map: `v4-release` (2026-09-30)

**Read this before resolving any commit hash in the V4 documents.** The reports, protocol revisions and
commit messages under `work/v4-release/` were written on a local, unpublished branch. **Every V4 commit hash they
cite** (for example `4e4e626`, `fe3f646`, `ae8753e`) **is that local history's, and does not exist on the remote
`v4-release` branch.** Neither do the hashes in the `(cherry picked from commit …)` trailers. The published commit
with the same content is the right-hand column below.

## How the published branch was built

- **Base.**
  - The published branch starts from the remote `v3-slim` at `39a7b0b`.
  - The V4 work was developed on `f5502cd`, the pre-rewrite local V3 Slim Golden Baseline. It does not exist on the
    remote.
  - The remote history was rewritten independently, and `39a7b0b` is its counterpart.
  - The two trees differ in one line only: `work/v3-slim/session2-fixes-report.md`, which names the author
    identity. `git diff --stat` between them: `1 file changed, 1 insertion(+), 1 deletion(-)`.
  - Where the V4 documents say "release base `f5502cd`", read `39a7b0b` for the published branch.
- **The V4 commits.**
  - All 37 commits of `f5502cd..ae8753e` were cherry-picked in order with `-x`, so each keeps a trailer naming its
    local original.
  - Their author and committer were then set to the remote history's identity. Dates, messages and trees were
    kept.
  - Each published commit's tree differs from its original's only in that inherited base line.
- **Added on this branch only,** both documents that change no product file:
  - `work/v4-release/followup-targeted-none-floor.md`;
  - this map, added by the branch's last commit, which is therefore not listed below.
- **What the published content is:**
  - the kit export equals the one revision 9 validated (`812115b5…`);
  - that validation is a single run per case (52 of 52 once), not a stability measure.
- **Not published:**
  - the `v4-planning` branch, including `72dadd1` cited by the protocol as the structured-channel library;
  - the local `v4-release` branch;
  - every tag.
  Hashes from them are local references only.

## Map (in branch order)

| # | Local original (unpublished) | Published on `v4-release` | Subject |
|---|---|---|---|
| 1 | `de2e7d4` | `1c915bd` | feat(v4): assemble the V4 product tree on the golden baseline |
| 2 | `eec0f3f` | `e266ba1` | fix(feedback-store): close four deferred reuse-safety defects before release |
| 3 | `5233964` | `c4cb89c` | fix(validation): define the out-of-scope-caller rule for finding validation |
| 4 | `fa3dfa4` | `a5ab9d1` | docs(v4): describe the V4 release and make the tree self-contained |
| 5 | `26a0d62` | `fda9758` | fix(review): turn Evidence Reuse off when no Python interpreter is available |
| 6 | `1f9b411` | `e449700` | fix(file-security): report upload-into-static-root as its own finding |
| 7 | `67908c0` | `1f3dd2f` | fix(v4): close the release review's Major and Minor findings |
| 8 | `c3782a3` | `58ce753` | docs(v4-release): completion report -- V4_RELEASE_NOT_READY |
| 9 | `4b1cb17` | `16680a8` | fix(v4): release fix cycle 2 -- class-limited caller rule; durable STALE invalidation |
| 10 | `644d419` | `c2aa885` | fix(v4): close the cycle-2 review findings (quarantine locking, quarantined-run lookup, class list) |
| 11 | `b66d191` | `1c1452c` | docs(v4-release): fix cycle 2 outcome -- still V4_RELEASE_NOT_READY |
| 12 | `cf6fe8d` | `5fe03dd` | docs(v4-release): pre-register the final per-case validation protocol |
| 13 | `9f4228c` | `5406f9b` | docs(v4-release): final pre-registered validation -- V4_RELEASE_NOT_READY |
| 14 | `ef8a9e4` | `b72ecff` | test(v4-release): versioned V4 release corpus with a corrected RV-02 fixture |
| 15 | `868ef5d` | `c943344` | docs(v4-release): pre-register revision 2 of the final validation protocol |
| 16 | `9db058a` | `603953e` | docs(v4-release): final validation revision 2 -- V4_RELEASE_NOT_READY |
| 17 | `53ef539` | `c2c452f` | test(v4-release): audit every safe corpus case; v4-release-corpus/2 |
| 18 | `7d1a767` | `a3967c4` | docs(v4-release): pre-register revision 3 of the final validation protocol |
| 19 | `728e66b` | `259b68a` | docs(v4-release): safe-fixture audit + final validation rev 3 -- V4_RELEASE_NOT_READY |
| 20 | `4e4e626` | `5a2cae7` | test(v4-release): strict safe-fixture audit; v4-release-corpus/3 |
| 21 | `cedcf19` | `787884c` | docs(v4-release): pre-register revision 4 of the final validation protocol |
| 22 | `526fef5` | `98ad63d` | docs(v4-release): record revision-4 validation, NOT_READY at RV-29 |
| 23 | `d67a81c` | `e6563ae` | test(v4-release): self-contained RV-29 fixture; v4-release-corpus/4 |
| 24 | `298fb31` | `36116f5` | docs(v4-release): pre-register revision 5 of the final validation protocol |
| 25 | `7b6212e` | `cfc2ed7` | docs(v4-release): record revision-5 validation, NOT_READY at RV-28 |
| 26 | `17edea1` | `c16d1c0` | test(v4-release): atomic RV-28 quota; hard-link threat model; corpus /5 |
| 27 | `bc7abdc` | `afd5b5f` | docs(v4-release): pre-register revision 6 of the final validation protocol |
| 28 | `3e7e770` | `920a557` | docs(v4-release): record revision-6 collect-all validation, gate NOT_MET |
| 29 | `b92b1ef` | `640d82d` | fix(review): require each selected domain's play; explicit stored-XSS checks for served uploads |
| 30 | `92af53c` | `50b836f` | docs(v4-release): pre-register revision 7 of the final validation protocol |
| 31 | `296e9ed` | `ea42be0` | docs(v4-release): record revision-7 validation, gate NOT_MET |
| 32 | `315af46` | `e317238` | fix(manifest): deterministic CSRF domain floor; domains are a minimum; trust-boundary rule for group identifiers |
| 33 | `b561c4c` | `db0ece0` | docs(v4-release): pre-register revision 8 of the final validation protocol |
| 34 | `51318a1` | `85b7c70` | docs(v4-release): record revision-8 validation, gate MET (52/52) |
| 35 | `fe3f646` | `e6159e6` | fix(workflow): CSRF signal floor also at NONE; record RV-15 local express-session check |
| 36 | `54d912a` | `c0ab3a5` | docs(v4-release): pre-register revision 9 of the final validation protocol |
| 37 | `ae8753e` | `6485ef2` | docs(v4-release): record revision-9 validation, gate MET (52/52) |
| 38 | — (new on this branch) | `f486b2d` | docs(v4-release): record the TARGETED/NONE signal-floor follow-up (not implemented) |
