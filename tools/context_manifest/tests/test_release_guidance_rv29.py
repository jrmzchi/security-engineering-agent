"""RV-29 regression (V4 release, protocol revision 7): the stored-XSS miss and the guidance that must prevent it.

Revision 6's RV-29 review confirmed both path traversals and never reported the stored XSS. The case file shows
app.UseStaticFiles publishing the upload directory, and the play already named the risk. The runner had read only
skills/security-review/SKILL.md, never plays/file-security.md.

Deterministic checks only -- whether a reviewer now reports it needs a review run:
- every manifest domain has a play of the same name, and SKILL.md step 5 makes reading each selected domain's play
  mandatory at every budget level;
- plays/file-security.md's Uploads section carries the four stored-XSS checks (hosting, public URL, content type,
  same-origin inline rendering), confirms only when all four are established, and names the missing hosting
  evidence as NEEDS_VERIFICATION instead of assuming it;
- applied to the two RV-29 fixtures, those checks give CONFIRMED for the V4-release fixture, whose hosting is code,
  and NEEDS_VERIFICATION -- never CONFIRMED -- for the V3 fixture, whose hosting exists only in stripped comments.
"""

from __future__ import annotations

import os
import re
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO)
from tools.context_manifest.domains import ALL_DOMAINS  # noqa: E402

FIX = os.path.join(REPO, "tests", "fixtures")
V4_FIXTURE = os.path.join(FIX, "v4_release", "upload_static_hosted_program_deceptive.cs")
V3_FIXTURE = os.path.join(FIX, "upload_webroot_content_disposition_deceptive.cs")


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def _code(path):
    """The case as a runner sees it: comment lines removed."""
    with open(path, encoding="utf-8") as fh:
        return "\n".join(ln for ln in fh.read().splitlines() if not ln.lstrip().startswith("//"))


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _uploads_section():
    play = _read("plays", "file-security.md")
    return _flat(play.split("## Uploads", 1)[1].split("\n## ", 1)[0])


def stored_xss_decision(code):
    """A fixture-bound PROXY of the play's four checks, for the two RV-29 fixtures and edits of them.

    It is not a general implementation of the rule; its triggers are literal:
    - a storage-path string literal naming wwwroot/public/static;
    - `UseStaticFiles` over `UploadStorage.Directory`;
    - `GetExtension`/`ChangeExtension`/`AllowedExtensions` taken as an extension control;
    - any `OnPrepareResponse` taken as attachment on the static response.
    So it misses, for example, a served directory whose name is not web-root-like. It shows the rule's decision
    table on these fixtures; it does not prove how a reviewer applies the play. That needs a review run.

    Returns CONFIRMED only when all four are established; NEEDS_VERIFICATION when the upload lands under a
    web-root-like directory but the hosting or URL mapping is not shown; NONE otherwise."""
    writes_upload = re.search(r"File\.Create\(\s*path\s*\)", code) and "IFormFile" in code
    literals = re.findall(r'"([^"\n]*)"', code)                   # string literals, paired left to right
    web_root_like = any(re.search(r"\b(wwwroot|public|static)\b", s, re.I) for s in literals)
    if not writes_upload or not web_root_like:
        return "NONE"
    serves = re.search(r"app\.UseStaticFiles\(\s*new StaticFileOptions\s*\{(.*?)\}\s*\);", code, re.S)
    hosting = bool(serves) and "PhysicalFileProvider(UploadStorage.Directory)" in serves.group(1)
    url = bool(serves) and "RequestPath = UploadStorage.RequestPath" in serves.group(1)
    if not (hosting and url):
        return "NEEDS_VERIFICATION"
    content = not re.search(r"GetExtension|AllowedExtensions|ChangeExtension", code) \
        and "FileExtensionContentTypeProvider()" in serves.group(1)
    inline_same_origin = "OnPrepareResponse" not in serves.group(1)
    return "CONFIRMED" if content and inline_same_origin else "NONE"


class DomainPlayRoutingTests(unittest.TestCase):
    def test_every_manifest_domain_has_a_play_of_the_same_name(self):
        for d in ALL_DOMAINS:
            with self.subTest(domain=d):
                self.assertTrue(os.path.exists(os.path.join(REPO, "plays", f"{d}.md")), d)

    def test_skill_step_5_makes_every_selected_domain_play_mandatory(self):
        skill = _flat(_read("skills", "security-review", "SKILL.md"))
        step5 = skill.split("5. **Manual semantic analysis.**", 1)[1].split("6. **Potential findings.**", 1)[0]
        self.assertIn("Reading each selected domain's play is not optional.", step5)
        self.assertIn("open and read `plays/<domain>.md` for **every** domain step 1 selected", step5)
        self.assertIn("it never decides whether a listed domain's play is read", step5)
        self.assertIn("`plays/file-security.md`'s \"Uploads\" stored-XSS checks", step5)
        self.assertIn("| File upload/download/paths | `plays/file-security.md` |", _read("skills", "security-review", "SKILL.md"))


class UploadsGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.s = _uploads_section()

    def test_the_four_checks_are_named(self):
        for check in ("1. Hosting --", "2. Public URL --", "3. Content type --", "4. Browser execution on the app's origin --"):
            self.assertIn(check, self.s)
        for detail in ("app.UseStaticFiles(...)", "express.static(dir)", "RequestPath + the stored file name",
                       "X-Content-Type-Options: nosniff does not stop", "no Content-Disposition: attachment on it"):
            self.assertIn(detail, self.s)

    def test_confirm_only_with_all_four_and_never_assume_hosting(self):
        self.assertIn("-> all four established from code in the review scope: CONFIRMED stored XSS, as its own finding.", self.s)
        self.assertIn("do NOT assume the directory is served", self.s)
        self.assertIn("not assumed to exist (plays/finding-validation.md)", self.s)
        self.assertIn("Report NEEDS_VERIFICATION and name the missing hosting evidence", self.s)
        self.assertIn("do not drop the candidate silently either", self.s)
        self.assertIn("never skip them because a path-traversal finding on the same code was already written".lower(),
                      self.s.lower())
        self.assertIn("gets no stored-XSS finding", self.s)
        self.assertIn("report it as its OWN finding", self.s)


class Rv29DecisionTests(unittest.TestCase):
    def test_the_v4_release_fixture_establishes_all_four_checks(self):
        self.assertEqual(stored_xss_decision(_code(V4_FIXTURE)), "CONFIRMED")

    def test_the_v3_fixture_without_hosting_code_is_never_confirmed(self):
        code = _code(V3_FIXTURE)
        self.assertNotIn("UseStaticFiles", code)
        self.assertEqual(stored_xss_decision(code), "NEEDS_VERIFICATION")

    def test_a_failing_check_in_the_code_removes_the_finding(self):
        code = _code(V4_FIXTURE)
        forced = code.replace("var path = Path.Combine(UploadStorage.Directory, file.FileName);",
                              "var path = Path.Combine(UploadStorage.Directory, Path.ChangeExtension(Path.GetRandomFileName(), \".bin\"));")
        self.assertEqual(stored_xss_decision(forced), "NONE")
        attachment = code.replace("ContentTypeProvider = new FileExtensionContentTypeProvider(),",
                                  "ContentTypeProvider = new FileExtensionContentTypeProvider(),\n    OnPrepareResponse = c => "
                                  "c.Context.Response.Headers.ContentDisposition = \"attachment\",")
        self.assertEqual(stored_xss_decision(attachment), "NONE")

    def test_an_upload_outside_any_web_root_gets_no_stored_xss_finding(self):
        code = _code(V4_FIXTURE).replace('"wwwroot", "uploads"', '"private-data", "incoming"')
        code = re.sub(r"Directory\.CreateDirectory\(UploadStorage\.Directory\);\s*app\.UseStaticFiles\(.*?\);", "", code, flags=re.S)
        code = code.replace('RequestPath = "/uploads"', 'Unused = "x"')
        self.assertEqual(stored_xss_decision(code), "NONE")


if __name__ == "__main__":
    unittest.main()
