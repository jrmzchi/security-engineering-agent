# V4 release validation corpus (`v4-release-corpus/1`)

The V4 release is validated against a versioned corpus,
`tests/validation/v4-release-corpus-manifest.json`: 39 rows, `RV-01` to `RV-39`.
38 of them are the V3 corpus rows of `tests/validation/expected-results.md`, unchanged
(same fixtures, members, forms and expected results). Only **RV-02** differs.

**This corpus is not a V3-versus-V4 comparison set.** Because one row differs, a
result on it cannot be compared row-for-row with any historical V3 or Batch 5 figure.
Those figures, the V3 fixture `tests/fixtures/sql_injection_safe.py` and
`tests/validation/expected-results.md` are unchanged. The enterprise-identity set
(`v4-enterprise-identity-expected-results.md`, 13 rows) is used as it is.

## Why RV-02 differs

The V3 row `sql_injection_safe.py` tests one property: a parameterized query must not
be reported as SQL injection. Its `/users` route, however, also returns users' e-mail
addresses to any caller, with no authentication check. That is a real missing-
authentication finding (CWE-306), and a correct review reports it. As a "no confirmed
finding" fixture it therefore punishes a correct answer. Treating that finding as out of
scope would weaken the rule that a safe case has no CONFIRMED finding, so the finding is
not suppressed, and the V3 fixture is not edited either.

For the V4 release corpus, RV-02 is instead
`tests/fixtures/v4_release/catalog_lookup_parameterized_safe.py`. It keeps the same
tested property (a request parameter bound into a fixed query), but on a public
product-catalog lookup. That lookup returns only published catalog fields (SKU, name,
category, description), no user, account or other personal data, so it is genuinely
safe to serve without authentication. No pretend authentication layer was added.

| Fixture | Expected outcome | Category / CWE | Trap being tested |
|---|---|---|---|
| `tests/fixtures/v4_release/catalog_lookup_parameterized_safe.py` | No confirmed finding | — | reviewer flags any DB query touched by request data, regardless of parameterization |

`tools/context_manifest/tests/test_release_corpus.py` checks this deterministically:
- the fixture's query stays a fixed, parameterized string;
- its selected columns and response fields contain no user or account data;
- the manifest maps RV-02 to this fixture and every other row to its unchanged V3
  fixture and expected result.
