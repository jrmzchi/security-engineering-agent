"""Explicit mutation tests -- for each wrong implementation named in
the batch instructions, construct that WRONG version by hand and prove
it gives the wrong answer on a case this package's REAL implementation
gets right. This is what makes the real implementation's own passing
tests meaningful (discriminating), rather than merely
self-consistent -- a suite that only tests the real code in isolation
cannot tell you whether an equally-plausible-looking but wrong
alternative would also have passed.
"""

from __future__ import annotations

import os
import unittest

from .. import eligibility, identity, paths, schema, store


def _chain():
    return [
        {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
        {"path": "a/Service.cs", "qualifiedSymbol": "Service.Get"},
        {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
    ]


def _record(**overrides):
    kwargs = dict(
        record_id="r1", category="BOLA/IDOR",
        suspicion_pattern="p", safety_pattern="s",
        reachability_path=_chain(),
        rejection_reason="reason",
        evidence={"path": "a/Repository.cs", "observation": "o"},
        scope="scope", trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


class SinkOnlyMutationTests(unittest.TestCase):
    """"只比較sink" -- a buggy identity check comparing ONLY
    evidence.path, ignoring category and reachabilityPath entirely."""

    @staticmethod
    def _buggy_sink_only_identity(candidate_evidence_path, record):
        return paths.same_path(candidate_evidence_path, record["evidence"]["path"])

    def test_buggy_version_wrongly_matches_different_category_same_sink(self):
        record = _record()
        # Same sink, DIFFERENT category (Case 3's shape) -- the buggy
        # version wrongly says "match."
        self.assertTrue(self._buggy_sink_only_identity("a/Repository.cs", record))
        # The real implementation correctly says "different occurrence."
        real = identity.check_occurrence_identity(
            candidate_category="tenant isolation bypass",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=_chain(),
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertFalse(real.same_occurrence)

    def test_buggy_version_wrongly_matches_new_caller_case_5(self):
        record = _record()
        new_path = [{"path": "a/NewJob.cs", "qualifiedSymbol": "NewJob.Handle"}, {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"}]
        self.assertTrue(self._buggy_sink_only_identity("a/Repository.cs", record))  # wrongly matches
        real = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR", candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=new_path, candidate_trace_confidence="HIGH", record=record,
        )
        self.assertFalse(real.same_occurrence)  # correctly does not match ("新caller被舊record吸收" avoided)


class BasenameOnlyMutationTests(unittest.TestCase):
    """"只比較basename" -- comparing only os.path.basename instead of
    the full repository-relative path."""

    def test_buggy_basename_comparison_collides_across_directories(self):
        buggy_match = os.path.basename("fixtures/group_a/UserRepository.cs") == os.path.basename(
            "fixtures/group_b/UserRepository.cs"
        )
        self.assertTrue(buggy_match)  # two UNRELATED files, wrongly "same"
        real_match = paths.same_path("fixtures/group_a/UserRepository.cs", "fixtures/group_b/UserRepository.cs")
        self.assertFalse(real_match)


class IgnoreSymbolMutationTests(unittest.TestCase):
    """"忽略symbol" -- comparing only the file-path components of
    reachabilityPath, ignoring symbol entirely (schema section 5.1's
    Case 6)."""

    def test_buggy_file_path_only_comparison_passes_case_6_which_must_fail(self):
        record_chain = _chain()
        case6_chain = [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.ExportAction"},
            {"path": "a/Service.cs", "qualifiedSymbol": "Service.GetForExport"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        buggy_match = [e["path"] for e in record_chain] == [e["path"] for e in case6_chain]
        self.assertTrue(buggy_match)  # wrongly "same" (files match, symbols ignored)
        real_match = paths.same_reachability_path(record_chain, case6_chain)
        self.assertFalse(real_match)


class UnorderedSetMutationTests(unittest.TestCase):
    """"把path當unordered set" -- comparing reachabilityPath as a
    set/multiset instead of an ordered sequence."""

    def test_buggy_set_comparison_ignores_hop_order(self):
        chain = _chain()
        reversed_chain = list(reversed(chain))

        def _as_frozenset(c):
            return frozenset((e["path"], e["qualifiedSymbol"]) for e in c)

        buggy_match = _as_frozenset(chain) == _as_frozenset(reversed_chain)
        self.assertTrue(buggy_match)  # wrongly "same" -- order ignored
        real_match = paths.same_reachability_path(chain, reversed_chain)
        self.assertFalse(real_match)


class IgnoreCategoryMutationTests(unittest.TestCase):
    """"忽略category" -- identity check that never compares category at
    all."""

    def test_buggy_version_without_category_check_wrongly_matches_case_3(self):
        record = _record()
        buggy_same_occurrence = (
            paths.same_path("a/Repository.cs", record["evidence"]["path"])
            and paths.same_reachability_path(_chain(), record["candidateShape"]["reachabilityPath"])
        )
        self.assertTrue(buggy_same_occurrence)  # if this were the WHOLE check, "SQL injection" vs
        # "BOLA/IDOR" at a coincidentally-identical path/chain would wrongly match. The real check
        # additionally requires category equality:
        real = identity.check_occurrence_identity(
            candidate_category="SQL injection",  # different from record's "BOLA/IDOR"
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=_chain(),
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertFalse(real.same_occurrence)
        self.assertIn(identity.CATEGORY_MISMATCH, real.reasons)


class MissingHopMutationTests(unittest.TestCase):
    """"少一hop仍判相同" -- a buggy comparison that only checks whether
    every entry in the SHORTER chain appears somewhere in the longer
    one (a subset check), rather than requiring equal length and exact
    position."""

    def test_buggy_subset_comparison_wrongly_matches_a_shorter_chain(self):
        full_chain = _chain()
        missing_middle_hop = [full_chain[0], full_chain[2]]  # Controller -> Repository directly

        def _buggy_subset_match(shorter, longer):
            return all(any(e["path"] == o["path"] and e["qualifiedSymbol"] == o["qualifiedSymbol"] for o in longer) for e in shorter)

        self.assertTrue(_buggy_subset_match(missing_middle_hop, full_chain))  # wrongly "same"
        real_match = paths.same_reachability_path(missing_middle_hop, full_chain)
        self.assertFalse(real_match)


class DependenciesOnlySinkMutationTests(unittest.TestCase):
    """"dependencies只包含sink" -- a buggy dependency derivation that
    only names the terminal sink, dropping every intermediate hop --
    this would make check (c) blind to Case 4's upstream-control-
    removed scenario."""

    def test_buggy_sink_only_dependencies_misses_intermediate_hop_change(self):
        chain = _chain()
        buggy_deps = [chain[-1]["path"]]  # sink only -- "a/Repository.cs"
        changed_files = ["a/Service.cs"]  # the intermediate hop changed

        def _check_c(deps, changed):
            return not any(paths.same_path(d, c) for d in deps for c in changed)

        self.assertTrue(_check_c(buggy_deps, changed_files))  # wrongly says "no dependency changed"

        real_deps = schema.derive_minimum_dependencies(chain)
        self.assertFalse(_check_c(real_deps, changed_files))  # correctly detects the change


class StaleRecordReuseMutationTests(unittest.TestCase):
    """"STALE record仍可reuse" -- a buggy decide_reuse that forgets the
    STALE short-circuit and runs straight into (a)-(d)."""

    def test_buggy_version_would_reuse_a_stale_record(self):
        record = _record()
        record["status"] = "STALE"

        def _buggy_decide_reuse_ignoring_stale(record):
            id_result = identity.check_occurrence_identity(
                candidate_category=record["candidateShape"]["category"],
                candidate_evidence_path=record["evidence"]["path"],
                candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
                candidate_trace_confidence="HIGH",
                record=record,
            )
            return id_result.same_occurrence  # ignores STALE entirely

        self.assertTrue(_buggy_decide_reuse_ignoring_stale(record))  # wrongly reusable

        real = eligibility.decide_reuse(
            record=record,
            candidate_category=record["candidateShape"]["category"],
            candidate_evidence_path=record["evidence"]["path"],
            candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=True,
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in _chain()},
        )
        self.assertFalse(real.reusable)
        self.assertIn(eligibility.REASON_RECORD_STALE, real.reasons)


class UnknownConditionMutationTests(unittest.TestCase):
    """"UNKNOWN invalidation condition被當成成立" (treated as
    satisfied/passed rather than failing closed) -- a buggy check (b)
    that only fails on an EXPLICIT True, treating None (unknown) as a
    pass."""

    def test_buggy_check_b_treats_unknown_as_passing(self):
        record = _record(invalidation_conditions=["dependency version bump"])

        def _buggy_check_b(conditions, known_states):
            return not any(known_states.get(c) is True for c in conditions)  # None -> "not true" -> passes

        self.assertTrue(_buggy_check_b(record["invalidationConditions"], {}))  # wrongly passes on UNKNOWN

        real = eligibility.decide_reuse(
            record=record,
            candidate_category=record["candidateShape"]["category"],
            candidate_evidence_path=record["evidence"]["path"],
            candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=True,
            known_condition_states={},  # condition's state is unknown
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in _chain()},
        )
        self.assertFalse(real.reusable)
        self.assertIn(eligibility.REASON_INVALIDATION_CONDITION_UNKNOWN, real.reasons)


class SafetyPatternNotRecheckedMutationTests(unittest.TestCase):
    """"safetyPattern不重查" -- a buggy decide_reuse that ignores
    `pattern_and_scope_match` entirely and always treats check (a) as
    passed."""

    def test_buggy_version_reuses_despite_pattern_no_longer_holding(self):
        record = _record()

        def _buggy_check_a(_verdict):
            return None  # never fails, regardless of the actual verdict

        self.assertIsNone(_buggy_check_a(False))  # "no failure reported" -- wrongly treated as passing

        real = eligibility.decide_reuse(
            record=record,
            candidate_category=record["candidateShape"]["category"],
            candidate_evidence_path=record["evidence"]["path"],
            candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=False,  # re-inspection found the pattern no longer holds
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in _chain()},
        )
        self.assertFalse(real.reusable)
        self.assertIn(eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, real.reasons)


class UnqualifiedSymbolCollisionMutationTests(unittest.TestCase):
    """"symbol 撞名" -- [ADDED, per a round-1 independent review Major]
    the exact counterexample the reviewer constructed: two different
    methods sharing a bare name (e.g. an authorized `ReportView.get`
    and an unauthorized `ExportView.get`, both named `get`, both
    calling the same repository method) would produce IDENTICAL
    {path, symbol} hops under a bare-name convention and be wrongly
    treated as the same occurrence."""

    def test_bare_symbol_convention_would_have_collided(self):
        authorized_chain = [{"path": "app/views.py", "qualifiedSymbol": "get"}, {"path": "app/repo.py", "qualifiedSymbol": "find_by_id"}]
        unauthorized_chain = [{"path": "app/views.py", "qualifiedSymbol": "get"}, {"path": "app/repo.py", "qualifiedSymbol": "find_by_id"}]
        # Under a bare-name convention these two chains are indistinguishable:
        self.assertTrue(paths.same_reachability_path(authorized_chain, unauthorized_chain))

    def test_schema_now_refuses_to_build_a_record_with_bare_symbols_at_all(self):
        # This closes the gap BY CONSTRUCTION: a record built with bare
        # symbols like this can no longer even be created, so the
        # collision above can never reach a stored Feedback record.
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(
                record_id="r1", category="BOLA/IDOR",
                suspicion_pattern="p", safety_pattern="s",
                reachability_path=[{"path": "app/views.py", "qualifiedSymbol": "get"}, {"path": "app/repo.py", "qualifiedSymbol": "find_by_id"}],
                rejection_reason="r",
                evidence={"path": "app/repo.py", "observation": "o"},
                scope="scope", trace_confidence="HIGH",
                last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
            )


class QualifiedSymbolBareComparisonMutationTests(unittest.TestCase):
    """[ADDED, per explicit instruction for the qualifiedSymbol
    redesign's required test matrix]: "regression to bare-symbol
    comparison" -- a buggy comparator that reduces each qualifiedSymbol
    down to the bare trailing identifier (after the last qualification
    marker, before any signature) instead of comparing the full string.
    This is the exact Case 6 counterexample restated against the CURRENT
    qualified shapes (not the old unqualified "Get"/"Get" shape
    `UnqualifiedSymbolCollisionMutationTests` above already covers,
    which schema.py now refuses to even construct)."""

    @staticmethod
    def _bare_trailing_name(qualified_symbol: str) -> str:
        # Strip any signature, then keep only the text after the last
        # qualification marker -- e.g. "ReportView.Get" -> "Get".
        without_signature = qualified_symbol.split("(", 1)[0]
        for marker in (".", "::", "#", "->"):
            if marker in without_signature:
                without_signature = without_signature.rsplit(marker, 1)[-1]
        return without_signature

    def test_buggy_bare_comparison_wrongly_matches_different_classes(self):
        authorized = [
            {"path": "app/views.py", "qualifiedSymbol": "app.views.ReportView.get"},
            {"path": "app/repo.py", "qualifiedSymbol": "app.repo.Repository.find_by_id"},
        ]
        unauthorized = [
            {"path": "app/views.py", "qualifiedSymbol": "app.views.ExportView.get"},
            {"path": "app/repo.py", "qualifiedSymbol": "app.repo.Repository.find_by_id"},
        ]

        def _buggy_bare_symbol_match(a, b):
            if len(a) != len(b):
                return False
            return all(
                paths.same_path(ea["path"], eb["path"])
                and self._bare_trailing_name(ea["qualifiedSymbol"]) == self._bare_trailing_name(eb["qualifiedSymbol"])
                for ea, eb in zip(a, b)
            )

        self.assertTrue(_buggy_bare_symbol_match(authorized, unauthorized))  # wrongly "same"
        real_match = paths.same_reachability_path(authorized, unauthorized)
        self.assertFalse(real_match)


class QualifiedSymbolIgnoredSignatureMutationTests(unittest.TestCase):
    """"ignored signature" -- a buggy comparator that strips the
    parenthesized parameter signature before comparing, but keeps the
    full namespace/type qualifier. This is exactly the C# overload
    collision the redesign was instructed to close: two overloads of
    the same method, in the same class, differing only by parameter
    type."""

    @staticmethod
    def _strip_signature(qualified_symbol: str) -> str:
        return qualified_symbol.split("(", 1)[0]

    def test_buggy_signature_stripped_comparison_wrongly_matches_overloads(self):
        int_overload = [
            {"path": "a/ReportController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportController.Get(int)"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "MyApp.Data.Repository.FindById"},
        ]
        string_overload = [
            {"path": "a/ReportController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportController.Get(string)"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "MyApp.Data.Repository.FindById"},
        ]

        def _buggy_signature_stripped_match(a, b):
            if len(a) != len(b):
                return False
            return all(
                paths.same_path(ea["path"], eb["path"])
                and self._strip_signature(ea["qualifiedSymbol"]) == self._strip_signature(eb["qualifiedSymbol"])
                for ea, eb in zip(a, b)
            )

        self.assertTrue(_buggy_signature_stripped_match(int_overload, string_overload))  # wrongly "same"
        real_match = paths.same_reachability_path(int_overload, string_overload)
        self.assertFalse(real_match)


class QualifiedSymbolIgnoredLexicalContainerMutationTests(unittest.TestCase):
    """"ignored-lexical-container" -- a buggy comparator that keeps the
    trailing method name (and signature, if any) but drops the
    enclosing namespace/type qualifier before comparing. This is the
    Python two-classes-same-method collision: two different classes
    each declaring a method of the same name, at the same file path."""

    @staticmethod
    def _drop_container(qualified_symbol: str) -> str:
        # Keep only the last "container.method" segment's method part
        # plus any signature -- e.g. "app.views.ClassA.get_report" ->
        # "get_report", "app.views.ClassA.get_report(int)" -> "get_report(int)".
        if "(" in qualified_symbol:
            head, _, sig = qualified_symbol.partition("(")
            return head.rsplit(".", 1)[-1] + "(" + sig
        return qualified_symbol.rsplit(".", 1)[-1]

    def test_buggy_container_dropped_comparison_wrongly_matches_different_classes(self):
        class_a = [
            {"path": "app/views.py", "qualifiedSymbol": "app.views.ClassA.get_report"},
            {"path": "app/repo.py", "qualifiedSymbol": "app.repo.Repository.find_by_id"},
        ]
        class_b = [
            {"path": "app/views.py", "qualifiedSymbol": "app.views.ClassB.get_report"},
            {"path": "app/repo.py", "qualifiedSymbol": "app.repo.Repository.find_by_id"},
        ]

        def _buggy_container_dropped_match(a, b):
            if len(a) != len(b):
                return False
            return all(
                paths.same_path(ea["path"], eb["path"])
                and self._drop_container(ea["qualifiedSymbol"]) == self._drop_container(eb["qualifiedSymbol"])
                for ea, eb in zip(a, b)
            )

        self.assertTrue(_buggy_container_dropped_match(class_a, class_b))  # wrongly "same"
        real_match = paths.same_reachability_path(class_a, class_b)
        self.assertFalse(real_match)


class LineRangeAsIdentityMutationTests(unittest.TestCase):
    """"lineRange-as-identity" -- a buggy comparator that additionally
    requires `lineRange` to match, treating evidence-location metadata
    as if it were part of occurrence identity. This is the opposite
    direction of wrong from the other three mutations above: it makes
    the check TOO strict, wrongly reporting "different occurrence" for
    a pure line shift (e.g. a comment added above an unchanged hop)
    that must never by itself change the identity result."""

    @staticmethod
    def _buggy_lineRange_sensitive_match(a, b) -> bool:
        if len(a) != len(b):
            return False
        for ea, eb in zip(a, b):
            if not paths.same_path(ea["path"], eb["path"]):
                return False
            if ea.get("qualifiedSymbol") != eb.get("qualifiedSymbol"):
                return False
            if ea.get("lineRange") != eb.get("lineRange"):  # the bug: lineRange included
                return False
        return True

    def test_buggy_lineRange_sensitive_comparison_wrongly_mismatches_a_pure_line_shift(self):
        original = [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 10, "end": 12}},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById", "lineRange": {"start": 40, "end": 44}},
        ]
        shifted = [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 15, "end": 17}},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById", "lineRange": {"start": 40, "end": 44}},
        ]
        self.assertFalse(self._buggy_lineRange_sensitive_match(original, shifted))  # wrongly "different"
        real_match = paths.same_reachability_path(original, shifted)
        self.assertTrue(real_match)  # the real implementation correctly ignores lineRange


class NewCallerAbsorbedMutationTests(unittest.TestCase):
    """"新caller被舊record吸收" -- restated as its own dedicated test
    (Case 5's own shape, tested here from the "what if identity were
    sink-only" angle specifically, distinct from SinkOnlyMutationTests
    above which is about category, not about absorbing a whole new
    reachability path)."""

    def test_new_caller_not_absorbed_by_old_record(self):
        record = _record()
        new_path = [{"path": "a/NewJob.cs", "qualifiedSymbol": "NewJob.Handle"}, {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"}]

        def _buggy_sink_only_reuse_check(record, candidate_path):
            return paths.same_path(candidate_path[-1]["path"], record["evidence"]["path"])

        self.assertTrue(_buggy_sink_only_reuse_check(record, new_path))  # wrongly "absorbed"

        real = identity.check_occurrence_identity(
            candidate_category=record["candidateShape"]["category"],
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=new_path,
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertFalse(real.same_occurrence)


if __name__ == "__main__":
    unittest.main()
