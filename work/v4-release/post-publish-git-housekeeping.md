# Post-publish Git housekeeping: recommendations only (2026-09-30)

**Status: nothing here has been executed.** This record is kept apart from the product fixes on purpose: none of
these items changes what the kit does, and none of them may be done in place of a product fix. Every command below
is a suggestion to run later, after its own decision. No history is rewritten by any of them unless the item says
so, and none of those is recommended.

State checked read-only on 2026-09-30:

| Ref | Where | Points at |
|---|---|---|
| `v4-release` | remote | `6f90d0d` (published, 39 commits on remote `v3-slim`) |
| `v3-slim` | remote | `39a7b0b` |
| `master` | remote | `dc51ce9` |
| `v3-slim-golden-baseline` | remote tag | `39a7b0b` |
| `v3-slim-golden-baseline` | local annotated tag | `f5502cd` |
| `v4-release-publish` | local branch | `6f90d0d` (the published content) |
| `refs/original/refs/heads/v4-release-publish` | local backup ref | `f2f39f8` |
| `v4-release-hardening` | local branch | this branch (not published) |

## 1. The origin URL

- **Fact.** The local `origin` still names the repository's old owner. GitHub reports the repository moved to
  `jrmzchi/security-engineering-agent`, and the old URL still redirects.
- **Recommendation.** Update it; this changes local configuration only, nothing on the remote.
  1. Confirm that the new URL serves the same refs: `git ls-remote https://github.com/jrmzchi/security-engineering-agent.git`.
  2. Then: `git remote set-url origin https://github.com/jrmzchi/security-engineering-agent.git`.

## 2. The same-named tag

- **Fact.** Local and remote `v3-slim-golden-baseline` point at different commits:
  - the local tag is `f5502cd`, the pre-rewrite base the V4 work was developed and validated on;
  - the remote tag is `39a7b0b`, its rewritten counterpart. The two trees differ in one line;
    `publish-commit-map.md` records the mapping.
- **Recommendation.** Keep both as they are for now, and move neither.
  - A plain `git fetch --tags` refuses to overwrite the local tag, so the difference stays visible.
  - Never use `git fetch --tags --force` in this clone: it would silently repoint the local tag and lose the
    `f5502cd` name that the V4 records cite.
  - If a later step needs the remote tag locally, first give the local one a second name so its commit keeps a
    name. For example: `git tag v3-slim-golden-baseline-local-f5502cd f5502cd`.

## 3. The old-identity backup ref

- **Fact.** `refs/original/refs/heads/v4-release-publish` (`f2f39f8`) was left behind by the identity rewrite.
  - It holds the V4 commits before their author and committer were changed.
  - It is local and was never pushed.
  - The same content, with the same old identity, is also on the local `v4-release` branch (`ae8753e`), so the
    backup is not the only copy.
- **Recommendation.** Keep it until a decision about publishing this hardening branch has been made and carried out.
  Then delete it with `git update-ref -d refs/original/refs/heads/v4-release-publish`. Deleting it removes a local
  name only; nothing published changes.

## 4. The scratch publish worktree

- **Fact.** The publish branch `v4-release-publish` is checked out in a worktree inside a session scratch directory.
  - Its content equals the published `v4-release`.
  - Its long path is why the Python tests could not run there (Windows path length). This hardening branch uses a
    short sibling path instead.
- **Recommendation.** Remove the worktree when it is no longer needed: `git worktree remove <that path>`. That
  refuses if the tree has local changes; it has none today.
  - The branch can then stay as a local name for the published commit.
  - Or delete it with `git branch -d v4-release-publish`. It is an ancestor of `v4-release-hardening`, so `-d`
    will not force anything.

## 5. The published early commits with a personal identity

- **Fact.** The first three commits of the published history carry a personal, company-domain author and committer
  identity: the root `1d73569`, then `98e012a` and `12081af`.
  - They were already public on the remote `master` and `v3-slim` before any V4 work.
  - `v4-release` inherits them because it is built on `v3-slim`.
  - (An earlier note called them "three root commits". There is one root commit; the other two follow it.)
- **Recommendation.** Do not rewrite this automatically.
  - Removing the identity means rewriting every published branch that contains these commits and force-pushing
    them. Every published hash would change, including the ones cited in this repository's records.
  - Existing clones, forks and caches would keep the old commits anyway.
  - If it is wanted, it is a separate, explicit decision covering all branches at once, with the hash maps
    regenerated. It is not part of any release step.
