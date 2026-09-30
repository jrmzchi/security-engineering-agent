from __future__ import annotations

import unittest

from .. import paths


class NormalizeTests(unittest.TestCase):
    def test_backslash_to_forward_slash(self):
        self.assertEqual(paths.normalize("a\\b\\c.cs"), "a/b/c.cs")

    def test_collapses_redundant_slashes_and_dot(self):
        self.assertEqual(paths.normalize("a//b/./c.cs"), "a/b/c.cs")

    def test_rejects_non_string(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.normalize(None)

    def test_rejects_empty(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.normalize("")


class ValidateTests(unittest.TestCase):
    def test_ordinary_relative_path_ok(self):
        self.assertEqual(paths.validate("tests/fixtures/foo/Bar.cs"), "tests/fixtures/foo/Bar.cs")

    def test_rejects_posix_absolute(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.validate("/etc/passwd")

    def test_rejects_windows_drive_absolute(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.validate("C:\\Windows\\System32\\config")
        with self.assertRaises(paths.InvalidPathError):
            paths.validate("C:/Windows/System32/config")

    def test_rejects_unc_path(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.validate("\\\\server\\share\\file.cs")

    def test_rejects_dotdot_even_if_it_would_stay_inside(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.validate("a/b/../c.cs")
        with self.assertRaises(paths.InvalidPathError):
            paths.validate("../outside.cs")

    def test_backslash_form_normalizes_before_validating(self):
        self.assertEqual(paths.validate("a\\b\\c.cs"), "a/b/c.cs")

    def test_rejects_paths_that_normalize_to_empty(self):
        """[ADDED, per a round-2 independent review Minor]: "." and
        "./" normalize to "" -- an empty path names no file and must
        never silently stand in for "the whole repository.\""""
        for empty_shape in (".", "./", "././"):
            with self.subTest(value=empty_shape):
                with self.assertRaises(paths.InvalidPathError):
                    paths.validate(empty_shape)


class SamePathTests(unittest.TestCase):
    def test_separator_equivalence(self):
        self.assertTrue(paths.same_path("a/b/c.cs", "a\\b\\c.cs"))

    def test_case_insensitive_by_design(self):
        """[CHANGED, per explicit instruction closing a Round 4
        independent review Minor]: comparison is case-INSENSITIVE, on
        every platform, through the one shared `canonical()` rule --
        the previous case-sensitive choice was fail-closed only for
        identity and fail-OPEN for staleness detection (a record stored
        as `src/r.cs` never saw `git diff`'s `src/R.cs` as the same
        file changing). See the module docstring for the full trade."""
        self.assertTrue(paths.same_path("a/B.cs", "a/b.cs"))
        self.assertTrue(paths.same_path("Src/File.cs", "src/file.cs"))
        self.assertEqual(paths.canonical("Src\\File.cs"), "src/file.cs")

    def test_canonical_still_rejects_malformed_paths(self):
        for bad in ("/etc/passwd", "C:/x.cs", "a/../b.cs", ".", ""):
            with self.subTest(value=bad):
                with self.assertRaises(paths.InvalidPathError):
                    paths.canonical(bad)

    def test_validate_preserves_original_case_for_storage(self):
        # Only COMPARISON folds case; what gets stored keeps the
        # spelling the caller gave.
        self.assertEqual(paths.validate("Src/File.cs"), "Src/File.cs")

    def test_different_paths_not_same(self):
        self.assertFalse(paths.same_path("a/b.cs", "a/c.cs"))


class SameReachabilityPathTests(unittest.TestCase):
    def _chain(self):
        return [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Get"},
            {"path": "a/Service.cs", "qualifiedSymbol": "Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "FindById"},
        ]

    def test_identical_chain_matches(self):
        self.assertTrue(paths.same_reachability_path(self._chain(), self._chain()))

    def test_different_length_does_not_match(self):
        short = self._chain()[:2]
        self.assertFalse(paths.same_reachability_path(self._chain(), short))

    def test_different_order_does_not_match(self):
        # unordered-set comparison would wrongly treat this as equal --
        # this must fail.
        reversed_chain = list(reversed(self._chain()))
        self.assertFalse(paths.same_reachability_path(self._chain(), reversed_chain))

    def test_symbol_mismatch_at_same_file_does_not_match(self):
        chain = self._chain()
        other = self._chain()
        other[1]["qualifiedSymbol"] = "GetForExport"
        self.assertFalse(paths.same_reachability_path(chain, other))

    def test_ignoring_symbol_would_wrongly_match_file_path_only(self):
        # This test documents the exact mutation this module must
        # catch (schema section 5.1 Case 6): a naive comparison of
        # only the `path` component, ignoring `qualifiedSymbol`, would
        # say these two chains match. same_reachability_path must not.
        chain = self._chain()
        other = self._chain()
        other[0]["qualifiedSymbol"] = "DifferentAction"
        other[1]["qualifiedSymbol"] = "GetReportForExport"
        self.assertFalse(paths.same_reachability_path(chain, other))
        # A file-path-only (ignore-symbol) comparison, done by hand
        # here to prove it's a DIFFERENT, wrong answer:
        file_paths_only_match = [e["path"] for e in chain] == [e["path"] for e in other]
        self.assertTrue(file_paths_only_match)  # same files...
        # ...but same_reachability_path correctly says NOT the same
        # occurrence, because the symbols differ.


if __name__ == "__main__":
    unittest.main()
