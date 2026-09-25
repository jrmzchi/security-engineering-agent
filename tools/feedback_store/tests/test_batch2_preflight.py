"""V4 Batch 2 preflight -- the Batch 1 deferred data-boundary items the
user instructed be closed before any external producer is wired in:

1. the recursive secret scan covers mapping KEYS (not only values), at
   every nesting level, for rejection and miss records alike, and never
   echoes the offending value;
2. a lone surrogate never escapes `write()` as a raw UnicodeEncodeError
   -- refused at validation, and again at the serialization boundary
   with no partial file, an untouched store, and clean lock/temp state;
3. whitespace-only path segments are rejected everywhere, while file
   names that merely contain a space still work;
4. a bare string / bytes `invalidation_conditions` is refused instead of
   being split into characters.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest

from .. import eligibility, identity, invalidation, paths, schema, store

SECRET = 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'
SECRET_TAIL = "Zx9Qw8Er7Ty6Ui5Op4"
LONE_SURROGATE = "src/caf\udce9.cs"  # what surrogateescape yields for a non-UTF-8 byte


def _rec(record_id="r1", path="src/R.cs", **overrides):
    kwargs = dict(
        record_id=record_id, category="BOLA/IDOR", suspicion_pattern="p", safety_pattern="s",
        reachability_path=[{"path": path, "qualifiedSymbol": "MyApp.R.Find(int)"}],
        rejection_reason="r", evidence={"path": path, "observation": "o"}, scope="scope",
        trace_confidence="HIGH", last_validation={"timestamp": "t", "commit": None, "validatedBy": "human"},
    )
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


def _miss(**overrides):
    kwargs = dict(
        record_id="m1", layer="routing", observed_miss="missed IDOR", expected_finding="CONFIRMED HIGH BOLA/IDOR",
        prior_layers_passed=[], evidence={"path": "src/C.cs", "observation": "never routed"},
        remediation="fix routing", scope="this shape", human_confirmed_by="reviewer", created_at="2026-09-23T00:00:00Z",
    )
    kwargs.update(overrides)
    return schema.new_miss_record(**kwargs)


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = self._tmp.name
        self.security_dir = os.path.join(self.repo_root, ".security")
        os.makedirs(self.security_dir)
        self.path = os.path.join(self.security_dir, "feedback.json")

    def tearDown(self):
        self._tmp.cleanup()


# ------------------------------------------------------------------ 1. keys


class SecretMappingKeyScanTests(TempRepo):
    def _assert_refused_without_echo(self, fn):
        with self.assertRaises(schema.LikelySecretError) as ctx:
            fn()
        self.assertNotIn(SECRET_TAIL, str(ctx.exception))
        self.assertNotIn(SECRET, str(ctx.exception))

    def test_top_level_key_in_rejection_record(self):
        rec = _rec()
        rec[SECRET] = "x"
        self._assert_refused_without_echo(lambda: schema.validate_rejection_record(rec))

    def test_nested_keys_in_mapping_list_tuple(self):
        shapes = [
            {"unknownExtension": {SECRET: 1}},
            {"unknownExtension": [{"ok": 1}, {SECRET: 2}]},
            {"unknownExtension": ({"deep": [{"deeper": {SECRET: 3}}]},)},
            {"lastValidation_extra": {"note": {SECRET: "v"}}},
        ]
        for extra in shapes:
            with self.subTest(shape=list(extra)[0]):
                rec = _rec()
                rec.update(extra)
                self._assert_refused_without_echo(lambda: schema.validate_rejection_record(rec))

    def test_non_string_keys_are_handled_safely(self):
        rec = _rec()
        rec["unknownExtension"] = {1: "one", (2, 3): "tuple", None: "none", 4.5: "float"}
        schema.validate_rejection_record(rec)  # must not raise -- non-string keys are not text

    def test_same_rule_for_miss_records(self):
        m = _miss()
        m["extra"] = {SECRET: "v"}
        self._assert_refused_without_echo(lambda: schema.validate_miss_record(m))
        self._assert_refused_without_echo(lambda: _miss(evidence={"observation": "o", SECRET: 1}))
        self._assert_refused_without_echo(lambda: _miss(evidence=[{"observation": "o"}, {SECRET: 1, "observation": "p"}]))

    def test_key_secret_refused_at_every_entry_point(self):
        rec = _rec()
        rec["unknownExtension"] = {SECRET: "v"}
        s = store.empty_store()
        self._assert_refused_without_echo(lambda: store.append_rejection_record(s, rec))
        s["rejectionRecords"]["r1"] = rec
        with self.assertRaises(store.StoreError) as ctx:
            store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        self.assertNotIn(SECRET_TAIL, str(ctx.exception))
        self.assertFalse(os.path.exists(self.path))
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertNotIn(SECRET_TAIL, result.reason)

    def test_value_scan_still_works(self):
        rec = _rec()
        rec["unknownExtension"] = {"k": SECRET}
        self._assert_refused_without_echo(lambda: schema.validate_rejection_record(rec))

    def test_ordinary_keys_pass(self):
        rec = _rec()
        rec["unknownExtension"] = {"password_policy_reviewed": True, "api_key_rotation_days": 90}
        schema.validate_rejection_record(rec)  # keyword-shaped keys without a value pattern are fine


# ------------------------------------------------------------------ 2. surrogates


class LoneSurrogateTests(TempRepo):
    def test_validator_refuses_lone_surrogate_without_echo(self):
        for mutate in (
            lambda r: r["candidateShape"].__setitem__("category", LONE_SURROGATE),
            lambda r: r.__setitem__("scope", LONE_SURROGATE),
            lambda r: r.__setitem__("unknownExtension", {"k": LONE_SURROGATE}),
            lambda r: r.__setitem__("unknownExtension", {LONE_SURROGATE: 1}),
        ):
            with self.subTest():
                rec = _rec()
                mutate(rec)
                with self.assertRaises(schema.SchemaError) as ctx:
                    schema.validate_rejection_record(rec)
                self.assertNotIn("\udce9", str(ctx.exception))
                self.assertIn("UTF-8", str(ctx.exception))
        with self.assertRaises(schema.SchemaError):
            _miss(observed_miss=LONE_SURROGATE)

    def test_write_refuses_at_serialization_boundary_leaving_disk_and_store_intact(self):
        s = store.empty_store()
        store.append_rejection_record(s, _rec())
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit="c1")
        with open(self.path, "rb") as f:
            before_bytes = f.read()
        loaded = store.load(self.path, repo_root=self.repo_root)
        # Bypass validation on purpose to reach the serialization boundary
        # itself: a top-level key the validators do not inspect.
        loaded.store["storeNote"] = LONE_SURROGATE
        before_store = copy.deepcopy(loaded.store)
        with self.assertRaises(store.StoreError) as ctx:
            store.write(self.path, loaded.store, repo_root=self.repo_root, expected_on_disk_hash=loaded.on_disk_hash, git_commit="c2")
        self.assertNotIn("\udce9", str(ctx.exception))
        self.assertIsInstance(ctx.exception, store.StoreError)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before_bytes)  # no partial write, file unchanged
        self.assertEqual(loaded.store, before_store)  # in-memory store unchanged
        leftovers = [n for n in os.listdir(self.security_dir) if n != "feedback.json"]
        self.assertEqual(leftovers, [], "no temp file and no lock file may remain")

    def test_valid_non_ascii_still_round_trips(self):
        s = store.empty_store()
        store.append_rejection_record(s, _rec(path="src/café/R.cs"))
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        loaded = store.load(self.path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)
        self.assertEqual(loaded.store["rejectionRecords"]["r1"]["evidence"]["path"], "src/café/R.cs")


# ------------------------------------------------------------------ 3. blank segments


class WhitespacePathSegmentTests(unittest.TestCase):
    def test_whole_path_whitespace_rejected(self):
        for bad in (" ", "   ", "\t", " / "):
            with self.subTest(value=bad):
                with self.assertRaises(paths.InvalidPathError):
                    paths.validate(bad)
                with self.assertRaises(paths.InvalidPathError):
                    paths.canonical(bad)

    def test_middle_segment_whitespace_rejected(self):
        for bad in ("src/ /R.cs", "src/\t/R.cs", " /R.cs", "src/ "):
            with self.subTest(value=bad):
                with self.assertRaises(paths.InvalidPathError):
                    paths.validate(bad)

    def test_file_name_containing_a_space_is_accepted(self):
        self.assertEqual(paths.validate("src/My File.cs"), "src/My File.cs")
        self.assertEqual(paths.validate("my dir/Report Service.cs"), "my dir/Report Service.cs")
        self.assertTrue(paths.same_path("src/My File.cs", "src/my file.cs"))

    def test_identity_reuse_and_invalidation_agree(self):
        # Schema refuses to build a record with a blank segment ...
        with self.assertRaises(schema.SchemaError):
            _rec(path="src/ /R.cs")
        # ... identity fails closed on a blank candidate path ...
        rec = _rec()
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR", candidate_evidence_path=" ",
            candidate_reachability_path=[{"path": " ", "qualifiedSymbol": "MyApp.R.Find(int)"}],
            candidate_trace_confidence="HIGH", record=rec,
        )
        self.assertFalse(r.same_occurrence)
        # ... reuse check (c) raises on the caller's blank changed_files entry (caller bug) ...
        with self.assertRaises(paths.InvalidPathError):
            eligibility._check_c_dependencies(rec["dependencies"], [" "])
        # ... and invalidation raises on the caller's argument the same way, but reports a
        # record whose OWN dependency went blank as malformed rather than crashing.
        with self.assertRaises(paths.InvalidPathError):
            invalidation.find_directly_stale({"r1": rec}, [" "])
        broken = copy.deepcopy(rec)
        broken["dependencies"] = [" "]
        findings = invalidation.find_directly_stale({"r1": broken}, ["src/R.cs"])
        self.assertEqual([f.reason for f in findings], [invalidation.REASON_RECORD_MALFORMED])


# ------------------------------------------------------------------ 4. conditions


class InvalidationConditionsTypeTests(unittest.TestCase):
    def test_bare_string_and_bytes_refused(self):
        for bad in ("flagX", b"flagX", ""):
            with self.subTest(value=bad):
                with self.assertRaises(schema.SchemaError):
                    _rec(invalidation_conditions=bad)

    def test_collections_still_accepted(self):
        for ok in (["flagX"], ("flagX", "flagY"), {"flagX"}):
            with self.subTest(value=type(ok).__name__):
                rec = _rec(invalidation_conditions=ok)
                self.assertEqual(sorted(rec["invalidationConditions"]), sorted(ok))


if __name__ == "__main__":
    unittest.main()
