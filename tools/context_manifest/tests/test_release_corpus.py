"""V4 release corpus (tests/validation/v4-release-corpus-manifest.json) and its RV-02 fixture.

Deterministic checks only -- whether a reviewer reaches the right verdict needs a review run:
- the manifest has 39 rows; RV-02 maps to the V4-release fixture, every other row to its unchanged V3 fixture and
  V3 expected result;
- the RV-02 fixture's query is a fixed, parameterized string (no concatenation, f-string or formatting), and neither
  the selected columns nor the response fields expose user or account data.
"""

from __future__ import annotations

import ast
import json
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MANIFEST = os.path.join(REPO, "tests", "validation", "v4-release-corpus-manifest.json")
RV02 = os.path.join(REPO, "tests", "fixtures", "v4_release", "catalog_lookup_parameterized_safe.py")
ALLOWED_COLUMNS = {"sku", "name", "category", "description"}
PERSONAL = re.compile(r"user|email|e-mail|password|passwd|account|token|phone|address|ssn|birth|owner", re.I)


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def _manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


class ManifestTests(unittest.TestCase):
    def test_version_and_row_count(self):
        m = _manifest()
        self.assertEqual(m["version"], "v4-release-corpus/1")
        self.assertEqual([r["caseId"] for r in m["rows"]], [f"RV-{n:02d}" for n in range(1, 40)])

    def test_rv02_is_the_v4_release_fixture_and_the_only_difference(self):
        rows = {r["caseId"]: r for r in _manifest()["rows"]}
        rv02 = rows["RV-02"]
        self.assertEqual(rv02["fixture"], "v4_release/catalog_lookup_parameterized_safe.py")
        self.assertEqual(rv02["expected"], "NO_CONFIRMED")
        self.assertEqual(rv02["expectationSource"], "tests/validation/v4-release-corpus.md")
        self.assertEqual(rv02["replaces"], {"rowId": "sqli-safe", "fixture": "sql_injection_safe.py"})
        others = [r for cid, r in rows.items() if cid != "RV-02"]
        self.assertEqual(len(others), 38)
        self.assertFalse([r for r in others if "replaces" in r or r["fixture"].startswith("v4_release/")])
        self.assertEqual({r["expectationSource"] for r in others}, {"tests/validation/expected-results.md"})

    def test_every_other_row_matches_the_unchanged_v3_table(self):
        table = [ln for ln in _read("tests", "validation", "expected-results.md").splitlines() if ln.startswith("| `")]
        self.assertEqual(len(table), 39)
        for r in _manifest()["rows"]:
            if r["caseId"] == "RV-02":
                continue
            base = r["fixture"].rstrip("/")
            hits = [ln for ln in table if f"`{base}`" in ln or f"`{base}/`" in ln]
            if r["member"]:
                hits = [ln for ln in hits if f"`{r['member']}`" in ln]
            with self.subTest(row=r["caseId"]):
                self.assertEqual(len(hits), 1, r)
                confirmed = "No confirmed finding" not in hits[0]
                self.assertEqual(confirmed, r["expected"] in ("CONFIRMED", "STILL_VULNERABLE"), hits[0])
                self.assertTrue(os.path.exists(os.path.join(REPO, "tests", "fixtures", base)), base)

    def test_the_v3_row_is_still_in_the_v3_table_unchanged(self):
        self.assertIn("| `sql_injection_safe.py` | No confirmed finding |", _read("tests", "validation", "expected-results.md"))
        self.assertTrue(os.path.exists(os.path.join(REPO, "tests", "fixtures", "sql_injection_safe.py")))

    def test_the_corpus_document_says_it_is_not_a_v3_comparison(self):
        doc = _read("tests", "validation", "v4-release-corpus.md")
        self.assertIn("not a V3-versus-V4 comparison set", doc)
        self.assertIn("| `tests/fixtures/v4_release/catalog_lookup_parameterized_safe.py` | No confirmed finding |", doc)


class Rv02FixtureTests(unittest.TestCase):
    def setUp(self):
        with open(RV02, encoding="utf-8") as fh:
            self.tree = ast.parse(fh.read())

    def _executes(self):
        return [n for n in ast.walk(self.tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "execute"]

    def test_every_query_is_a_fixed_parameterized_string(self):
        calls = self._executes()
        self.assertEqual(len(calls), 1)
        for call in calls:
            sql = call.args[0]
            self.assertIsInstance(sql, ast.Constant, "query text must be a literal, not built from data")
            self.assertIsInstance(sql.value, str)
            self.assertIn("?", sql.value)
            self.assertNotIn("%", sql.value)
            self.assertNotIn("{", sql.value)
            self.assertEqual(len(call.args), 2, "the value must be passed as a separate parameter")
            self.assertIsInstance(call.args[1], ast.Tuple)
            self.assertEqual(sql.value.count("?"), len(call.args[1].elts))

    def test_selected_columns_and_table_carry_no_personal_or_account_data(self):
        sql = self._executes()[0].args[0].value
        m = re.match(r"\s*SELECT\s+(.*?)\s+FROM\s+(\w+)", sql, re.I | re.S)
        self.assertIsNotNone(m)
        self.assertEqual({c.strip() for c in m.group(1).split(",")}, ALLOWED_COLUMNS)
        self.assertEqual(m.group(2), "products")
        self.assertIsNone(PERSONAL.search(sql))

    def test_the_response_exposes_only_catalog_fields(self):
        keys = {k.value for n in ast.walk(self.tree) if isinstance(n, ast.Dict)
                for k in n.keys if isinstance(k, ast.Constant)}
        self.assertEqual(keys - {"products"}, ALLOWED_COLUMNS)

    def test_no_pretend_authentication_layer(self):
        src = ast.unparse(self.tree)
        for word in ("login_required", "authenticate", "Authorization", "session[", "current_user"):
            self.assertNotIn(word, src)


if __name__ == "__main__":
    unittest.main()
