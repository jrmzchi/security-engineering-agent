"""V4 release corpus manifests (v4-release-corpus/1, kept as a record; v4-release-corpus/2, current) and the
V4-release replacement fixtures.

Deterministic checks only -- whether a reviewer reaches the right verdict needs a review run:
- 39 rows each; every replaced row keeps its form and its "no confirmed finding" expectation, names the V3 fixture it
  replaces and why, and points at an existing fixture; every other row maps to its unchanged V3 fixture and V3 result;
- each replacement fixture keeps the property its V3 row tests, and none returns user or account data.
"""

from __future__ import annotations

import ast
import json
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FIX = os.path.join(REPO, "tests", "fixtures")
V1 = os.path.join(REPO, "tests", "validation", "v4-release-corpus-manifest.json")
V2 = os.path.join(REPO, "tests", "validation", "v4-release-corpus-v2-manifest.json")
V3 = os.path.join(REPO, "tests", "validation", "v4-release-corpus-v3-manifest.json")
REPLACED_V2 = {"RV-02", "RV-04", "RV-13", "RV-20", "RV-22", "RV-24", "RV-35", "RV-37"}
REPLACED_V3 = REPLACED_V2 | {"RV-15", "RV-26", "RV-28"}
PERSONAL = re.compile(r"\b(user(name)?s?|e-?mail|password|account|balance|phone|ssn|birth|owner)\b", re.I)


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _code(path):
    """Source without comment lines (the corpus strips header comments before review)."""
    with open(path, encoding="utf-8") as fh:
        return "\n".join(ln for ln in fh.read().splitlines() if not ln.lstrip().startswith(("//", "#")))


def _v3_table():
    return [ln for ln in _read("tests", "validation", "expected-results.md").splitlines() if ln.startswith("| `")]


class ManifestTests(unittest.TestCase):
    def check_manifest(self, path, version, replaced, current=False):
        m = _load(path)
        self.assertEqual(m["version"], version)
        self.assertEqual([r["caseId"] for r in m["rows"]], [f"RV-{n:02d}" for n in range(1, 40)])
        table = _v3_table()
        self.assertEqual(len(table), 39)
        doc = _read("tests", "validation", "v4-release-corpus.md")
        for r in m["rows"]:
            with self.subTest(manifest=version, row=r["caseId"]):
                base = r["fixture"].rstrip("/")
                self.assertTrue(os.path.exists(os.path.join(FIX, base)), base)
                if r["caseId"] in replaced:
                    self.assertTrue(base.startswith("v4_release/"))
                    self.assertEqual(r["expected"], "NO_CONFIRMED")
                    self.assertEqual(r["expectationSource"], "tests/validation/v4-release-corpus.md")
                    old = r["replaces"]["fixture"]
                    hits = [ln for ln in table if f"`{old}`" in ln or f"`{old}/`" in ln]
                    self.assertEqual(len(hits), 1, old)
                    self.assertIn("No confirmed finding", hits[0])
                    if current:
                        self.assertIn(f"`tests/fixtures/{base}", doc)
                    self.assertTrue(os.path.exists(os.path.join(FIX, old)), old)
                    if not version.endswith("/1"):
                        self.assertTrue(r["replaces"].get("reason"))
                else:
                    self.assertNotIn("replaces", r)
                    self.assertEqual(r["expectationSource"], "tests/validation/expected-results.md")
                    hits = [ln for ln in table if f"`{base}`" in ln or f"`{base}/`" in ln]
                    if r["member"]:
                        hits = [ln for ln in hits if f"`{r['member']}`" in ln]
                    self.assertEqual(len(hits), 1, r)
                    self.assertEqual("No confirmed finding" not in hits[0], r["expected"] in ("CONFIRMED", "STILL_VULNERABLE"))

    def test_v1_record(self):
        self.check_manifest(V1, "v4-release-corpus/1", {"RV-02"})

    def test_v2_record(self):
        self.check_manifest(V2, "v4-release-corpus/2", REPLACED_V2)
        self.assertEqual(_load(V2)["supersedes"], "v4-release-corpus/1")

    def test_v3_current(self):
        self.check_manifest(V3, "v4-release-corpus/3", REPLACED_V3, current=True)
        self.assertEqual(_load(V3)["supersedes"], "v4-release-corpus/2")
        rows = {r["caseId"]: r for r in _load(V3)["rows"]}
        for cid, prev in (("RV-04", "v4_release/command_argument_array_allowlisted_safe.js"),
                          ("RV-24", "v4_release/public_document_download_safe.cs"),
                          ("RV-37", "v4_release/cross_file_public_manual_download_safe")):
            self.assertEqual(rows[cid]["replaces"]["previousV4Fixture"], prev)
            self.assertTrue(os.path.exists(os.path.join(FIX, prev)), prev)

    def test_v2_and_v3_keep_every_form_and_member_of_v1(self):
        v1 = {r["caseId"]: r for r in _load(V1)["rows"]}
        for r in _load(V2)["rows"] + _load(V3)["rows"]:
            with self.subTest(row=r["caseId"]):
                self.assertEqual((r["form"], r["member"], r["expected"]), (v1[r["caseId"]]["form"], v1[r["caseId"]]["member"], v1[r["caseId"]]["expected"]))

    def test_the_v3_sources_are_still_present_and_the_corpus_says_it_is_not_a_comparison(self):
        for name in ("sql_injection_safe.py", "command_injection_safe.js", "cookie_secure_safe.js", "redirect_local_safe.cs",
                     "ssrf_allowlist_safe.py", "path_traversal_safe.cs", "cross_file_sql_safe", "cross_file_path_traversal_safe"):
            self.assertTrue(os.path.exists(os.path.join(FIX, name)), name)
        self.assertIn("not a V3-versus-V4 comparison set", _read("tests", "validation", "v4-release-corpus.md"))


class Rv02CatalogTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIX, "v4_release", "catalog_lookup_parameterized_safe.py"), encoding="utf-8") as fh:
            self.tree = ast.parse(fh.read())

    def test_every_query_is_a_fixed_parameterized_string(self):
        calls = [n for n in ast.walk(self.tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute"]
        self.assertEqual(len(calls), 1)
        sql = calls[0].args[0]
        self.assertIsInstance(sql, ast.Constant)
        self.assertIn("?", sql.value)
        self.assertIsInstance(calls[0].args[1], ast.Tuple)
        self.assertEqual(sql.value.count("?"), len(calls[0].args[1].elts))
        m = re.match(r"\s*SELECT\s+(.*?)\s+FROM\s+(\w+)", sql.value, re.I | re.S)
        self.assertEqual({c.strip() for c in m.group(1).split(",")}, {"sku", "name", "category", "description"})
        self.assertEqual(m.group(2), "products")

    def test_the_response_exposes_only_catalog_fields(self):
        keys = {k.value for n in ast.walk(self.tree) if isinstance(n, ast.Dict) for k in n.keys if isinstance(k, ast.Constant)}
        self.assertEqual(keys - {"products"}, {"sku", "name", "category", "description"})


class Rv04ArgumentArrayTests(unittest.TestCase):
    def setUp(self):
        self.code = _code(os.path.join(FIX, "v4_release", "command_argument_array_allowlisted_safe.js"))

    def test_argument_array_without_a_shell(self):
        self.assertIn("execFile(", self.code)
        self.assertNotRegex(self.code, r"\bexec\(|spawn\(|shell\s*:")
        self.assertRegex(self.code, r"execFile\(\s*'convert',")

    def test_no_request_value_reaches_the_program_unmapped(self):
        args = re.search(r"execFile\(\s*'convert',\s*\[(.*?)\]", self.code, re.S).group(1)
        self.assertNotIn("req.", args)
        self.assertEqual([a.strip() for a in args.split(",")], ["source", "'-resize'", "`${size}x${size}`", "'png:-'"])
        self.assertRegex(self.code, r"const source = ASSETS\.get\(")
        self.assertRegex(self.code, r"new Map\(\[")
        self.assertIn("Number.isInteger(size)", self.code)
        self.assertNotRegex(self.code, r"endsWith|extname|\.png'\)")


class Rv13CookieTests(unittest.TestCase):
    def test_flags_random_value_and_no_login_semantics(self):
        code = _code(os.path.join(FIX, "v4_release", "cookie_flags_anonymous_session_safe.js"))
        for flag in ("httpOnly: true", "secure: true", "sameSite: 'strict'"):
            self.assertIn(flag, code)
        self.assertIn("crypto.randomBytes(32)", code)
        self.assertNotRegex(code, r"(?i)login|password|logged in|user")


class Rv20RedirectTests(unittest.TestCase):
    def test_local_redirect_only_and_no_credentials(self):
        code = _code(os.path.join(FIX, "v4_release", "local_redirect_preferences_safe.cs"))
        self.assertIn("!Url.IsLocalUrl(returnUrl)", code)
        self.assertIn("return LocalRedirect(returnUrl);", code)
        self.assertIn("[ValidateAntiForgeryToken]", code)
        self.assertIn("SupportedCultures.Contains(culture)", code)
        self.assertNotRegex(code, r"(?i)password|login|username")
        self.assertNotRegex(code, r"\bRedirect\(returnUrl")


class Rv22SsrfTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIX, "v4_release", "ssrf_allowlist_pinned_safe.py"), encoding="utf-8") as fh:
            self.src = fh.read()
        self.code = _code(os.path.join(FIX, "v4_release", "ssrf_allowlist_pinned_safe.py"))

    def test_allowlist_public_address_and_pinned_connection(self):
        self.assertIn("parsed.hostname not in ALLOWED_HOSTS", self.code)
        self.assertIn('parsed.scheme != "https"', self.code)
        self.assertIn(".is_global", self.code)
        self.assertRegex(self.code, r"HTTPSConnectionPool\(\s*address,")
        for kw in ("server_hostname=parsed.hostname", "assert_hostname=parsed.hostname", 'cert_reqs="CERT_REQUIRED"', "retries=False"):
            self.assertIn(kw, self.code)
        self.assertIn("redirect=False", self.code)
        self.assertIn("resp.read(MAX_BYTES + 1)", self.code)
        self.assertNotRegex(self.code, r"requests\.(get|post|request)|urlopen\(image_url")
        ast.parse(self.src)

    def test_returns_only_size_or_error(self):
        keys = set(re.findall(r'jsonify\(\{"(\w+)"', self.code))
        self.assertEqual(keys, {"error", "status"})


class PublicManualTests(unittest.TestCase):
    def test_rv24_containment_public_content_and_no_links(self):
        code = _code(os.path.join(FIX, "v4_release", "public_document_download_safe.cs"))
        self.assertIn("Path.GetFullPath(Path.Combine(_baseDir, fileName))", code)
        self.assertIn("StartsWith(_baseDir + Path.DirectorySeparatorChar, StringComparison.Ordinal)", code)
        self.assertIn("FileAttributes.ReparsePoint", code)
        self.assertIn("/var/app/published-manuals", code)
        self.assertNotRegex(code, r"(?i)upload|report|user")

    def test_rv37_containment_across_three_files(self):
        d = os.path.join(FIX, "v4_release", "cross_file_public_manual_download_safe")
        self.assertEqual(sorted(os.listdir(d)), ["ManualDownloadController.cs", "ManualFileService.cs", "ManualPathHelper.cs"])
        helper = _code(os.path.join(d, "ManualPathHelper.cs"))
        self.assertIn('Path.GetFullPath("/var/app/published-manuals") + Path.DirectorySeparatorChar', helper)
        self.assertIn("canonical.StartsWith(_manualsDir, StringComparison.Ordinal)", helper)
        self.assertIn("FileAttributes.ReparsePoint", helper)
        service = _code(os.path.join(d, "ManualFileService.cs"))
        self.assertIn("Path.GetFileName(path)", service)
        for f in os.listdir(d):
            self.assertNotRegex(_code(os.path.join(d, f)), r"(?i)upload|report|user")


class Rv35CatalogSearchTests(unittest.TestCase):
    def test_parameterized_like_across_three_files_and_catalog_fields_only(self):
        d = os.path.join(FIX, "v4_release", "cross_file_catalog_search_safe")
        self.assertEqual(sorted(os.listdir(d)), ["ProductRepository.cs", "ProductSearchService.cs", "ProductsController.cs"])
        repo = _code(os.path.join(d, "ProductRepository.cs"))
        sql = re.search(r'new SqlCommand\(\s*"([^"]+)"', repo).group(1)
        self.assertIn("@query", sql)
        self.assertNotRegex(repo, r'"\s*\+\s*query|query\s*\+\s*"|\$"')
        self.assertIn('command.Parameters.AddWithValue("@query", query);', repo)
        cols = re.match(r"SELECT TOP \(50\) (.*?) FROM Products", sql).group(1)
        self.assertEqual({c.strip() for c in cols.split(",")}, {"Sku", "Name", "Category"})
        for f in os.listdir(d):
            self.assertIsNone(PERSONAL.search(_code(os.path.join(d, f))), f)


class Revision3FixtureTests(unittest.TestCase):
    """Controls the strict audit required to be visible inside the case (work/v4-release/safe-fixture-audit.md)."""

    def test_rv04_bounded_work_and_same_argument_rules(self):
        code = _code(os.path.join(FIX, "v4_release", "command_argument_array_bounded_safe.js"))
        args = re.search(r"execFile\(\s*'convert',\s*\[(.*?)\]", code, re.S).group(1)
        self.assertEqual([a.strip() for a in args.split(",")], ["source", "'-resize'", "`${size}x${size}`", "'png:-'"])
        self.assertNotRegex(code, r"\bexec\(|spawn\(|shell\s*:")
        self.assertIn("if (running >= MAX_CONCURRENT)", code)
        self.assertIn("res.status(429)", code)
        self.assertEqual(code.count("running += 1"), 1)
        self.assertEqual(code.count("running -= 1"), 1)
        self.assertRegex(code, r"const source = ASSETS\.get\(")

    def test_rv15_session_middleware_and_route_guard_are_in_the_case(self):
        code = _code(os.path.join(FIX, "v4_release", "cors_allowlist_session_guarded_safe.js"))
        self.assertIn("require('express-session')", code)
        self.assertRegex(code, r"SESSION_SECRET\.length < 32\)\s*\{\s*throw")
        for opt in ("httpOnly: true", "secure: true", "sameSite: 'lax'", "saveUninitialized: false"):
            self.assertIn(opt, code)
        self.assertIn("typeof req.session.userId !== 'number'", code)
        self.assertIn("res.status(401)", code)
        self.assertRegex(code, r"app\.get\('/api/preferences', requireSignedIn,")
        self.assertIn("ALLOWED_ORIGINS.has(origin)", code)
        self.assertIn("res.vary('Origin')", code)
        self.assertEqual(len(re.findall(r"app\.(get|post|put|delete|patch)\(", code)), 1)
        self.assertNotRegex(code, r"(?i)email|balance|account|password")

    def check_no_links(self, code, file_var, base_expr):
        plain = code.replace("System.IO.", "")
        self.assertIn(f"(File.GetAttributes({file_var}) & FileAttributes.ReparsePoint) != 0", plain)
        self.assertRegex(code, r"for \(var dir = Path\.GetDirectoryName\(" + file_var + r"\); dir is not null && dir\.Length >= " + base_expr)
        self.assertIn("(File.GetAttributes(dir) & FileAttributes.ReparsePoint) != 0", plain)

    def test_rv24_rv26_rv37_follow_no_links(self):
        rv24 = _code(os.path.join(FIX, "v4_release", "public_document_download_nolinks_safe.cs"))
        self.check_no_links(rv24, "resolved", r"_baseDir\.Length")
        self.assertIn("StartsWith(_baseDir + Path.DirectorySeparatorChar, StringComparison.Ordinal)", rv24)
        rv26 = _code(os.path.join(FIX, "v4_release", "path_prefix_canonicalized_nolinks_safe.cs"))
        self.check_no_links(rv26, "canonical", r"baseDir\.Length")
        self.assertIn('Path.GetFullPath("/var/app/reports") + Path.DirectorySeparatorChar', rv26)
        self.assertIn("canonical.StartsWith(_reportsDir, StringComparison.Ordinal)", rv26)
        d = os.path.join(FIX, "v4_release", "cross_file_public_manual_download_nolinks_safe")
        self.assertEqual(sorted(os.listdir(d)), ["ManualDownloadController.cs", "ManualFileService.cs", "ManualPathHelper.cs"])
        rv37 = _code(os.path.join(d, "ManualPathHelper.cs"))
        self.check_no_links(rv37, "canonical", r"baseDir\.Length")
        self.assertIn("canonical.StartsWith(_manualsDir, StringComparison.Ordinal)", rv37)
        for f in os.listdir(d):
            self.assertNotRegex(_code(os.path.join(d, f)), r"(?i)upload|report|user")

    def test_rv28_access_control_cookie_and_upload_rules_are_in_the_case(self):
        path = os.path.join(FIX, "v4_release", "file_upload_authenticated_safe.py")
        code = _code(path)
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        upload = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "upload")
        self.assertEqual([ast.unparse(d) for d in upload.decorator_list],
                         ["app.route('/upload', methods=['POST'])", "signed_in_required"])
        self.assertIn('isinstance(session.get("user_id"), int)', code)
        self.assertIn("abort(401)", code)
        for cfg in ("SESSION_COOKIE_HTTPONLY=True", "SESSION_COOKIE_SECURE=True", 'SESSION_COOKIE_SAMESITE="Strict"',
                    "MAX_CONTENT_LENGTH=5 * 1024 * 1024"):
            self.assertIn(cfg, code)
        self.assertRegex(code, r"if len\(SECRET_KEY\) < 32:\s*raise")
        self.assertIn("sniff_extension(data)", code)
        self.assertIn('f"{uuid.uuid4().hex}.{ext}"', code)
        self.assertIn("MAX_FILES_PER_USER", code)
        self.assertNotIn("f.filename", code)
        self.assertNotRegex(code, r"static")


if __name__ == "__main__":
    unittest.main()
