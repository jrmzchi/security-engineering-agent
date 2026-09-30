"""Batch 2 independent-review fixes that live on the Feedback-store side
or in the shared neutral heuristic:

  #1  `tools/secret_heuristic.find_secret_paths` must never put a
      secret-shaped mapping key into ANY path it yields -- its own or a
      descendant's -- and the record validators' error text must never
      contain the key or value text.
  extra finding: U+200B in a path segment -- pinned as CURRENT behaviour
      (accepted) with no policy decided here; see paths.normalize.

Assertions are written so a failure message never prints the fixture
secret either (`assertFalse(SECRET in text, "<where>")`).
"""

from __future__ import annotations

import unittest

from ... import secret_heuristic
from .. import paths, schema
from .test_batch2_preflight import SECRET, SECRET_TAIL, _miss, _rec

SECRET2 = 'api_key="Qq1Ww2Ee3Rr4Tt5Yy6"'
SECRET2_TAIL = "Qq1Ww2Ee3Rr4Tt5Yy6"
R = secret_heuristic.REDACTED_KEY


def _leaks(text: str) -> bool:
    return any(s in text for s in (SECRET, SECRET_TAIL, SECRET2, SECRET2_TAIL))


class FindSecretPathsTests(unittest.TestCase):
    def _paths(self, value, root="state"):
        hits = list(secret_heuristic.find_secret_paths(value, root))
        for path, _kind in hits:
            self.assertFalse(_leaks(path), "a yielded path contains secret text")
        return hits

    def test_secret_key_with_nested_mapping(self):
        hits = self._paths({SECRET: {"inner": SECRET2}})
        self.assertEqual(hits, [(f"state.{R}", "key"), (f"state.{R}.inner", "value")])

    def test_secret_key_with_list(self):
        hits = self._paths({SECRET: [SECRET2, {"x": SECRET2}]})
        self.assertEqual(hits, [(f"state.{R}", "key"), (f"state.{R}[0]", "value"), (f"state.{R}[1].x", "value")])

    def test_multi_level_secret_keys(self):
        hits = self._paths({"a": {SECRET: {SECRET2: "plain"}}})
        self.assertEqual(hits, [(f"state.a.{R}", "key"), (f"state.a.{R}.{R}", "key")])

    def test_key_and_value_both_secret(self):
        hits = self._paths({SECRET: SECRET2})
        self.assertEqual(hits, [(f"state.{R}", "key"), (f"state.{R}", "value")])

    def test_root_level_secret_key_without_prefix(self):
        hits = list(secret_heuristic.find_secret_paths({SECRET: {"inner": SECRET2}}))
        self.assertEqual(hits, [(R, "key"), (f"{R}.inner", "value")])

    def test_ordinary_keys_still_named(self):
        # Only secret-shaped keys are replaced; an ordinary key keeps its name (useful diagnostics).
        hits = self._paths({"diff_summary": {"note": SECRET}})
        self.assertEqual(hits, [("state.diff_summary.note", "value")])


class ValidatorErrorTextTests(unittest.TestCase):
    def _assert_refused_clean(self, fn):
        with self.assertRaises(schema.SchemaError) as ctx:
            fn()
        self.assertFalse(_leaks(str(ctx.exception)), "validator error text contains secret text")

    def test_rejection_record_shapes(self):
        shapes = (
            {SECRET: {"inner": SECRET2}},
            {SECRET: [SECRET2]},
            {"a": {SECRET: {SECRET2: "v"}}},
            {SECRET: SECRET2},
            {"a": [{"b": SECRET2}]},
        )
        for extra in shapes:
            with self.subTest(n=shapes.index(extra)):
                rec = _rec()
                rec["unknownExtension"] = extra
                self._assert_refused_clean(lambda: schema.validate_rejection_record(rec))

    def test_miss_record_shape(self):
        m = _miss()
        m["extra"] = {SECRET: {"inner": [SECRET2]}}
        self._assert_refused_clean(lambda: schema.validate_miss_record(m))


class FormatCharacterPathSegmentTests(unittest.TestCase):
    """U+200B is Unicode category Cf, not White_Space, so the
    whitespace-only-segment rule does not cover it. This test used to pin
    its ACCEPTANCE while the policy was open; the V4 release decided the
    policy (paths.py: any Cf character is rejected), so it now pins the
    rejection. The wider matrix is in test_release_fixes.py."""

    def test_zero_width_space_segment_is_rejected(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.normalize("src/\u200b/R.cs")

    def test_ordinary_whitespace_segment_still_rejected(self):
        with self.assertRaises(paths.InvalidPathError):
            paths.normalize("src/ /R.cs")  # NBSP IS White_Space


if __name__ == "__main__":
    unittest.main()
