"""Tests for the Round 6 close-out and the reconciled tail (sections
六–九) of the Round 5 close-out instruction:

* complete secret validation in `validate_rejection_record`
  (invalidationConditions, unknown top-level and nested fields);
* a closed Unicode comparison key (`NFC(NFD(x).casefold())`) with the
  reviewer-named character classes, at every layer, both directions,
  plus idempotence;
* bare-string guards on `affected_categories`/`affected_path_prefixes`;
* deadline checked after a SUCCESSFUL stale-lock removal too.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unicodedata
import unittest
import unittest.mock

from .. import eligibility, identity, invalidation, paths, schema, store

SECRET = 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'


def _rec(record_id="r1", path="src/R.cs", **overrides):
    kwargs = dict(
        record_id=record_id, category="BOLA/IDOR", suspicion_pattern="p", safety_pattern="s",
        reachability_path=[{"path": path, "qualifiedSymbol": "MyApp.R.Find(int)"}],
        rejection_reason="r", evidence={"path": path, "observation": "o"}, scope="scope",
        trace_confidence="HIGH", last_validation={"timestamp": "t", "commit": None, "validatedBy": "human"},
    )
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = self._tmp.name
        os.makedirs(os.path.join(self.repo_root, ".security"))
        self.path = os.path.join(self.repo_root, ".security", "feedback.json")

    def tearDown(self):
        self._tmp.cleanup()


# ------------------------------------------------------------ 必修 1: secrets


class CompleteSecretValidationTests(TempRepo):
    def _assert_refused_everywhere(self, record):
        with self.assertRaises(schema.LikelySecretError):
            schema.validate_rejection_record(record)
        s = store.empty_store()
        with self.assertRaises(schema.LikelySecretError):
            store.append_rejection_record(s, record)
        self.assertEqual(s["rejectionRecords"], {})
        s["rejectionRecords"][record["recordId"]] = record  # force past append
        with self.assertRaises(store.StoreError):
            store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        self.assertFalse(os.path.exists(self.path))
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        self.assertFalse(store.load(self.path, repo_root=self.repo_root).ok)
        os.remove(self.path)

    def test_builder_output_passes_validator(self):
        rec = _rec(invalidation_conditions=["EF Core version bump", "feature flag X"])
        schema.validate_rejection_record(rec)  # must not raise

    def test_builder_and_validator_agree_on_secret_in_invalidation_conditions(self):
        with self.assertRaises(schema.LikelySecretError):
            _rec(invalidation_conditions=[SECRET])
        rec = _rec()
        rec["invalidationConditions"] = ["fine", SECRET]
        self._assert_refused_everywhere(rec)

    def test_secret_in_unknown_top_level_field_is_refused(self):
        for shape in (
            SECRET,
            {"note": SECRET},
            [{"a": [SECRET]}],
            {"deep": {"deeper": [1, {"x": SECRET}]}},
        ):
            with self.subTest(shape=shape):
                rec = _rec()
                rec["unknownExtension"] = shape
                self._assert_refused_everywhere(rec)

    def test_secret_in_extra_last_validation_field_is_refused(self):
        rec = _rec()
        rec["lastValidation"]["note"] = SECRET
        self._assert_refused_everywhere(rec)
        rec = _rec()
        rec["lastValidation"]["tags"] = ["ok", {"k": "AKIAABCDEFGHIJKLMNOP"}]
        self._assert_refused_everywhere(rec)

    def test_unknown_fields_without_secrets_are_accepted_and_round_trip(self):
        # The decision is "accept unknown fields but scan them", not
        # "reject unknown fields" -- prove the accept half too.
        rec = _rec()
        rec["unknownExtension"] = {"note": "harmless", "list": [1, "two"]}
        rec["lastValidation"]["reviewer"] = "someone"
        schema.validate_rejection_record(rec)
        s = store.empty_store()
        store.append_rejection_record(s, rec)
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        loaded = store.load(self.path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)
        self.assertEqual(loaded.store["rejectionRecords"]["r1"]["unknownExtension"]["note"], "harmless")

    def test_mapping_keys_are_scanned_too(self):
        # [FLIPPED, Batch 2 preflight]: this test used to pin the
        # "values only" limitation; that gap is now closed and a secret
        # used as a dict KEY is refused, with a message that names the
        # field path but never echoes the key.
        rec = _rec()
        rec["unknownExtension"] = {SECRET: "value"}
        with self.assertRaises(schema.LikelySecretError) as ctx:
            schema.validate_rejection_record(rec)
        self.assertNotIn("Zx9Qw8Er7Ty6Ui5Op4", str(ctx.exception))
        self.assertNotIn("VALUES only", schema._check_no_secret_recursive.__doc__ or "")


# ------------------------------------------------------------ 必修 2: Unicode closure

# Reviewer-named classes: (a) ǰ (U+01F0) + dot below vs J + dot below +
# caron; (b) Greek letter with diacritics in mixed case and mixed
# normalization; (c) a previously-passing plain NFC/NFD pair. The
# Unicode-bearing segment is a DIRECTORY so the same pair also
# exercises central invalidation's prefix matching.
#
# Deliberately NOT included: a pair that merely reorders two combining
# marks of the SAME combining class (e.g. ι + tonos + dialytika vs
# ι + dialytika + tonos). Canonical ordering only reorders marks of
# DIFFERENT classes, so those two are genuinely distinct under Unicode
# canonical equivalence -- a first draft of this test used one and
# wrongly expected them to compare equal.
J_CARON_DOT_A = "src/ǰ̣/R.cs"           # ǰ + U+0323
J_CARON_DOT_B = "src/J̣̌/R.cs"          # J + U+0323 + U+030C
GREEK_A = "src/ΐ/R.cs"                        # ΐ precomposed (iota dialytika tonos)
GREEK_B = "src/Ϊ́/R.cs"            # Ι (capital iota) + dialytika + tonos, decomposed
CAFE_NFC = unicodedata.normalize("NFC", "src/café/Report.cs")
CAFE_NFD = unicodedata.normalize("NFD", CAFE_NFC)

PAIRS = {
    "j_caron_dot": (J_CARON_DOT_A, J_CARON_DOT_B),
    "greek_iota_dialytika_tonos": (GREEK_A, GREEK_B),
    "cafe_nfc_nfd": (CAFE_NFC, CAFE_NFD),
}


class UnicodeClosureTests(unittest.TestCase):
    def test_pairs_really_differ_as_code_points(self):
        for name, (a, b) in PAIRS.items():
            with self.subTest(pair=name):
                self.assertNotEqual(a, b)

    def test_round5_form_would_have_split_the_first_pair(self):
        # The exact defect: NFC(x).casefold() gives two different keys
        # for a pair Unicode D145 calls equal. Proves this test is
        # discriminating, not tautological.
        old = lambda s: unicodedata.normalize("NFC", s).casefold()
        self.assertNotEqual(old(J_CARON_DOT_A), old(J_CARON_DOT_B))
        self.assertEqual(paths.canonical(J_CARON_DOT_A), paths.canonical(J_CARON_DOT_B))

    def test_canonical_equal_and_idempotent_for_every_pair(self):
        for name, (a, b) in PAIRS.items():
            with self.subTest(pair=name):
                self.assertEqual(paths.canonical(a), paths.canonical(b))
                for x in (a, b):
                    c = paths.canonical(x)
                    self.assertEqual(paths.canonical(c), c)  # idempotence
                self.assertTrue(paths.same_path(a, b))
                self.assertTrue(paths.same_path(b, a))

    def test_storage_keeps_the_original_form(self):
        for name, (a, b) in PAIRS.items():
            with self.subTest(pair=name):
                self.assertEqual(paths.validate(a), a)
                self.assertEqual(paths.validate(b), b)
                rec = _rec(path=a)
                self.assertEqual(rec["evidence"]["path"], a)
                self.assertEqual(rec["dependencies"], [a])

    def test_distinct_names_stay_distinct(self):
        self.assertFalse(paths.same_path("src/á.cs", "src/é.cs"))
        self.assertFalse(paths.same_path(CAFE_NFC, "src/cafe/Report.cs"))  # accent is not dropped
        # Same-class combining marks in a different order are NOT
        # canonically equivalent; the key must not merge them either.
        self.assertFalse(paths.same_path("src/ί̈.cs", "src/ΐ.cs"))

    def _decide(self, record, cand, changed):
        return eligibility.decide_reuse(
            record=record, candidate_category="BOLA/IDOR", candidate_evidence_path=cand,
            candidate_reachability_path=[{"path": cand, "qualifiedSymbol": "MyApp.R.Find(int)"}],
            candidate_trace_confidence="HIGH", pattern_and_scope_match=True, known_condition_states={},
            changed_files=changed, hop_controls_confirmed={eligibility.hop_key(cand, "MyApp.R.Find(int)"): True},
        )

    def test_every_layer_both_directions_for_every_pair(self):
        for name, (a, b) in PAIRS.items():
            for stored, other in ((a, b), (b, a)):
                with self.subTest(pair=name, stored=stored[:12]):
                    rec = _rec(path=stored)
                    # identity
                    r = identity.check_occurrence_identity(
                        candidate_category="BOLA/IDOR", candidate_evidence_path=other,
                        candidate_reachability_path=[{"path": other, "qualifiedSymbol": "MyApp.R.Find(int)"}],
                        candidate_trace_confidence="HIGH", record=rec,
                    )
                    self.assertTrue(r.same_occurrence, r.reasons)
                    # reuse: sink changed in the other spelling -> not reusable
                    d = self._decide(rec, other, [other])
                    self.assertFalse(d.reusable)
                    self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, d.reasons)
                    # reuse: nothing changed -> reusable (hop_key agrees across forms)
                    self.assertTrue(self._decide(rec, other, []).reusable)
                    # direct invalidation
                    self.assertEqual([f.record_id for f in invalidation.find_directly_stale({"r1": rec}, [other])], ["r1"])
                    # central invalidation, directory prefix in the other spelling
                    prefix_other = other.rsplit("/", 1)[0]
                    self.assertEqual(
                        [f.record_id for f in invalidation.find_central_component_stale(
                            {"r1": rec}, central_component_file="x", affected_path_prefixes=[prefix_other])],
                        ["r1"],
                    )


# ------------------------------------------------------------ 六: bare strings


class CollectionBareStringGuardTests(unittest.TestCase):
    def _records(self):
        return {"r1": _rec(path="src/auth/Handler.cs")}

    def test_bare_string_prefix_is_rejected_not_split(self):
        with self.assertRaises(TypeError):
            invalidation.find_central_component_stale(self._records(), central_component_file="x", affected_path_prefixes="src")
        with self.assertRaises(TypeError):
            invalidation.find_central_component_stale(self._records(), central_component_file="x", affected_path_prefixes=b"src")

    def test_bare_string_category_is_rejected_not_substring_matched(self):
        with self.assertRaises(TypeError):
            invalidation.find_central_component_stale(self._records(), central_component_file="x", affected_categories="authorization")
        with self.assertRaises(TypeError):
            invalidation.find_central_component_stale(self._records(), central_component_file="x", affected_categories=["BOLA/IDOR", None])
        with self.assertRaises(TypeError):
            invalidation.find_central_component_stale(self._records(), central_component_file="x", affected_categories=[""])

    def test_proper_collections_still_work(self):
        recs = self._records()
        self.assertEqual([f.record_id for f in invalidation.find_central_component_stale(recs, central_component_file="x", affected_path_prefixes=["src/auth"])], ["r1"])
        self.assertEqual([f.record_id for f in invalidation.find_central_component_stale(recs, central_component_file="x", affected_categories=("BOLA/IDOR",))], ["r1"])
        self.assertEqual(invalidation.find_central_component_stale(recs, central_component_file="x", affected_categories={"other"}), [])


# ------------------------------------------------------------ 七: lock deadline


class StaleLockRecreatedTests(unittest.TestCase):
    def test_successful_removal_path_still_respects_deadline(self):
        """A stale lock that is recreated (with an old mtime) after every
        successful removal used to loop forever, because only the
        failed-removal branch checked the deadline."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "feedback.json")
            lock = store._lock_path_for(path)
            stale = __import__("time").time() - (store.LOCK_STALE_SECONDS + 5)

            def _recreate_stale():
                open(lock, "w").close()
                os.utime(lock, (stale, stale))

            _recreate_stale()
            real_remove = os.remove

            def _remove_then_recreate(p):
                real_remove(p)
                if p == lock:
                    _recreate_stale()

            real_open = os.open

            def _always_exists(p, flags, *a, **k):
                if p == lock:
                    raise FileExistsError(p)
                return real_open(p, flags, *a, **k)

            started = __import__("time").monotonic()
            with unittest.mock.patch("os.remove", side_effect=_remove_then_recreate), \
                 unittest.mock.patch("os.open", side_effect=_always_exists):
                with self.assertRaises(store.LockTimeoutError) as ctx:
                    store._acquire_lock(path, timeout=0.3)
            self.assertLess(__import__("time").monotonic() - started, 3.0)
            self.assertIn("kept reappearing", str(ctx.exception))
            try:
                real_remove(lock)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
