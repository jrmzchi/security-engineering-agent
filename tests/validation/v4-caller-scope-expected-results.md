# V4 caller-scope cases: Expected Results

One row per case in `tests/fixtures/caller_scope/` (V4 release). These cases
exercise `plays/finding-validation.md`'s "Rule — a sink whose callers are
outside the review scope". This set is its own figure. It is **not** part of
`tests/validation/expected-results.md` (the V3 corpus), its "Summary counts", or
a V3 corpus pass. Run a pass the way `tests/validation/README.md` describes,
stripping each fixture's header comment first. A cross-file case is one
directory reviewed together.

| Fixture (under `tests/fixtures/caller_scope/`) | Expected outcome | Category / CWE | Trap being tested |
|---|---|---|---|
| `authz_callerless_repository_unverified.cs` | No confirmed finding (NEEDS_VERIFICATION acceptable) | — | reviewer confirms BOLA/IDOR because the data-access method is public and has no ownership filter, although no caller (where that control belongs) is in scope |
| `authz_unsafe_in_scope_path/` (all 3 files) | CONFIRMED, HIGH | IDOR / BOLA / CWE-639 | reviewer lets the safe `Get()` path through `DocumentService`, or the repository's unseen callers, hide the in-scope `Export()` path that returns any document without an ownership check |
| `sqli_public_method_safe_in_scope_caller/` (both files) | CONFIRMED, HIGH | SQL injection / CWE-89 | reviewer rejects the raw-SQL concatenation because the only in-scope caller passes a constant, although the public method stays unsafe for its unseen callers |

```text
Caller-scope set -- must produce a CONFIRMED finding:     2
Caller-scope set -- must NOT produce a CONFIRMED finding: 1
```

## How the rule's required cases are covered

| # | Required behaviour | Case |
|---|---|---|
| 1 | Safe cross-file object authorization: the caller enforces ownership, so there is no CONFIRMED authorization finding | V3 corpus `cross_file_object_authz_safe/` |
| 2 | Unsafe cross-file object authorization: the caller reaches the object without ownership enforcement, so the finding stays detectable | V3 corpus `cross_file_object_authz_unsafe/` |
| 3 | Caller-less raw SQL with directly evidenced unsafe concatenation keeps its intended result (CONFIRMED) | V3 corpus `ef_fromsqlraw_vs_interpolated.cs` (`FindByNameUnsafe`); also `sqli_public_method_safe_in_scope_caller/` above |
| 4 | Caller-less authorization sink with no evidence about its caller or control is not auto-CONFIRMED | `authz_callerless_repository_unverified.cs` |
| 5 | An out-of-scope caller (or another safe path) does not erase the evidence of a separately unsafe in-scope path | `authz_unsafe_in_scope_path/` |

The play's text for each of these behaviours is also checked automatically by
`tools/context_manifest/tests/test_release_caller_scope.py`. That test does not
judge findings; judging them needs a review run over the fixtures.
