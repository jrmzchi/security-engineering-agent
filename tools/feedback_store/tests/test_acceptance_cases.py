"""context-manifest-schema.md section 5.2's six discriminable acceptance
cases, run against tests/fixtures/cross_file_object_authz_safe/ and
tests/fixtures/cross_file_sql_safe//cross_file_sql_unsafe/ -- the
already-existing V3 fixtures those sections name, not new ones.

Per explicit instruction ("使用既有fixture,不要用fixture自己的註解當作
結果證據。每案實際讀取程式與重建path"): every case below reads the
ACTUAL current fixture file content at test time and asserts the
specific line this case's scenario depends on is still there --
so if a fixture is ever edited, this suite fails loudly rather than
silently keeping stale assumptions. Fixture files themselves are never
modified by this test (they are real, shared V3 fixtures used
elsewhere too) -- a "LATER change" scenario is simulated by an
in-memory altered copy of the read text, not a write to disk.

[DISCLOSED, found while implementing this batch] `implementation-
batches.md`'s Batch 1 acceptance criteria and `measurement-plan.md`
section 5 both still say "five discriminable cases" -- but
`context-manifest-schema.md` section 5.2 was "revised a third time"
and now specifies SIX (Case 6, the same-file/different-symbol check,
was added after a third independent-review round specifically because
an implementation satisfying only Cases 1-5 with file-path-only
`reachabilityPath` comparison would still pass all of them while
failing Case 6). This suite implements all six, per that section's own
"Acceptance bar: all six cases must resolve as described" -- the more
recently revised, authoritative source, not the two documents that
have not caught up to it. Flagged for the user to consider a one-line
correction to those two documents; not corrected unilaterally here
since it is a cross-document consistency fix outside this batch's own
code, beyond what's needed to actually implement the requirement
correctly.
"""

from __future__ import annotations

import os
import unittest

from .. import eligibility, identity, schema

FIXTURES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures"))


def _read(relative_path: str) -> str:
    with open(os.path.join(FIXTURES_ROOT, *relative_path.split("/")), encoding="utf-8") as f:
        return f.read()


AUTHZ_SAFE = "cross_file_object_authz_safe"
SQL_SAFE = "cross_file_sql_safe"
SQL_UNSAFE = "cross_file_sql_unsafe"

CASE1_REACHABILITY_PATH = [
    {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportsController.cs", "qualifiedSymbol": "ReportsController.GetReport"},
    {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportService.cs", "qualifiedSymbol": "ReportService.GetReport"},
    {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs", "qualifiedSymbol": "ReportRepository.FindById"},
]
OWNERSHIP_CHECK_LINE = "report.OwnerUserId != currentUserId"


def _build_case1_record(**overrides) -> dict:
    kwargs = dict(
        record_id="case1",
        category="BOLA/IDOR",
        suspicion_pattern="object reference taken from a caller-supplied ID with no visible ownership check at the sink itself",
        safety_pattern="ReportService.GetReport enforces report.OwnerUserId == currentUserId before returning the result",
        reachability_path=CASE1_REACHABILITY_PATH,
        rejection_reason="cross-file ownership check present in ReportService.GetReport",
        evidence={"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs", "observation": "FindById itself has no ownership check; enforced by its caller"},
        scope="applies to ReportsController.GetReport -> ReportService.GetReport -> ReportRepository.FindById specifically",
        trace_confidence="HIGH",
        last_validation={"timestamp": "2026-09-23T00:00:00Z", "commit": "abc123", "validatedBy": "code_reviewer_subagent"},
    )
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


class FixtureGroundTruthTests(unittest.TestCase):
    """Confirms the fixture text these cases depend on actually exists,
    read fresh -- not assumed from a prior session's memory."""

    def test_authz_safe_ownership_check_present(self):
        text = _read(f"{AUTHZ_SAFE}/ReportService.cs")
        self.assertIn(OWNERSHIP_CHECK_LINE, text)

    def test_authz_safe_symbol_chain_present(self):
        controller = _read(f"{AUTHZ_SAFE}/ReportsController.cs")
        service = _read(f"{AUTHZ_SAFE}/ReportService.cs")
        repository = _read(f"{AUTHZ_SAFE}/ReportRepository.cs")
        self.assertIn("public IActionResult GetReport(int reportId)", controller)
        self.assertIn("_reportService.GetReport(reportId, currentUserId)", controller)
        self.assertIn("public Models.Report? GetReport(int reportId, int currentUserId)", service)
        self.assertIn("public Models.Report? FindById(int reportId)", repository)

    def test_sql_safe_parameterization_present(self):
        text = _read(f"{SQL_SAFE}/UserRepository.cs")
        self.assertIn("command.Parameters.AddWithValue(\"@query\", query)", text)

    def test_sql_unsafe_interpolation_present(self):
        text = _read(f"{SQL_UNSAFE}/UserRepository.cs")
        self.assertIn('$"SELECT Id, Name, Email FROM Users WHERE Name LIKE \'%{query}%\'"', text)


class Case1SafelyReusableTests(unittest.TestCase):
    """Case 1: a later, unrelated review re-examines the same
    repository; nothing changed. Expected: (a)/(b)/(c)/(d) all hold ->
    reused."""

    def test_reusable_when_nothing_changed(self):
        record = _build_case1_record()
        current_service_text = _read(f"{AUTHZ_SAFE}/ReportService.cs")
        pattern_still_holds = OWNERSHIP_CHECK_LINE in current_service_text  # the caller's own re-inspection
        decision = eligibility.decide_reuse(
            record=record,
            candidate_category="BOLA/IDOR",
            candidate_evidence_path=f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs",
            candidate_reachability_path=CASE1_REACHABILITY_PATH,
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=pattern_still_holds,
            known_condition_states={},
            changed_files=[],  # unrelated review -- nothing in this fixture group changed
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in CASE1_REACHABILITY_PATH},
        )
        self.assertTrue(decision.reusable)


class Case2StaleSinkChangeTests(unittest.TestCase):
    """Case 2: a SEPARATE record for cross_file_sql_safe/UserRepository.cs's
    FindByNameLike. A later edit reintroduces string concatenation for
    one parameter, in the SINK's own code. Expected: (a) fails on
    direct re-inspection of the sink -> NOT reused."""

    SQL_REACHABILITY_PATH = [
        {"path": f"tests/fixtures/{SQL_SAFE}/UserSearchService.cs", "qualifiedSymbol": "UserSearchService.SearchUsers"},
        {"path": f"tests/fixtures/{SQL_SAFE}/UserRepository.cs", "qualifiedSymbol": "UserRepository.FindByNameLike"},
    ]

    def _record(self):
        return schema.new_rejection_record(
            record_id="case2",
            category="SQL injection",
            suspicion_pattern="user input reaches a raw SQL string build",
            safety_pattern="query bound via command.Parameters.AddWithValue, not string-interpolated",
            reachability_path=self.SQL_REACHABILITY_PATH,
            rejection_reason="parameterized query, not vulnerable",
            evidence={"path": f"tests/fixtures/{SQL_SAFE}/UserRepository.cs", "observation": "query bound as SqlParameter"},
            scope="applies to UserSearchService.SearchUsers -> UserRepository.FindByNameLike specifically",
            trace_confidence="HIGH",
            last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
        )

    def test_sink_local_regression_forces_full_rederivation(self):
        original_text = _read(f"{SQL_SAFE}/UserRepository.cs")
        self.assertIn('command.Parameters.AddWithValue("@query", query)', original_text)
        # Simulate "a LATER maintenance edit reintroduces string
        # concatenation" -- an in-memory altered copy, fixture on disk
        # untouched.
        edited_text = original_text.replace(
            'using var command = new SqlCommand(\n            "SELECT Id, Name, Email FROM Users WHERE Name LIKE \'%\' + @query + \'%\'",\n            connection);\n        command.Parameters.AddWithValue("@query", query);',
            'using var command = new SqlCommand(\n            $"SELECT Id, Name, Email FROM Users WHERE Name LIKE \'%\' + {query} + \'%\'",\n            connection);',
        )
        self.assertNotEqual(original_text, edited_text, "the in-memory edit must actually change something")
        pattern_still_holds = "command.Parameters.AddWithValue" in edited_text
        self.assertFalse(pattern_still_holds)

        decision = eligibility.decide_reuse(
            record=self._record(),
            candidate_category="SQL injection",
            candidate_evidence_path=f"tests/fixtures/{SQL_SAFE}/UserRepository.cs",
            candidate_reachability_path=self.SQL_REACHABILITY_PATH,
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=pattern_still_holds,
            known_condition_states={},
            changed_files=[f"tests/fixtures/{SQL_SAFE}/UserRepository.cs"],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in self.SQL_REACHABILITY_PATH},
        )
        self.assertFalse(decision.reusable)
        self.assertIn(eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, decision.reasons)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, decision.reasons)


class Case3DifferentOccurrenceTests(unittest.TestCase):
    """Case 3: the SAME Case-1 record exists. A genuinely different
    candidate arises at cross_file_sql_unsafe/'s UserRepository.
    FindByNameLike -- different category, different full path.
    Expected: never compared at all (identity fails on sink AND
    category); the SQL candidate resolves independently."""

    def test_not_excluded_by_an_unrelated_record(self):
        case1_record = _build_case1_record()
        sql_path = [
            {"path": f"tests/fixtures/{SQL_UNSAFE}/UserSearchService.cs", "qualifiedSymbol": "UserSearchService.SearchUsers"},
            {"path": f"tests/fixtures/{SQL_UNSAFE}/UserRepository.cs", "qualifiedSymbol": "UserRepository.FindByNameLike"},
        ]
        id_result = identity.check_occurrence_identity(
            candidate_category="SQL injection",
            candidate_evidence_path=f"tests/fixtures/{SQL_UNSAFE}/UserRepository.cs",
            candidate_reachability_path=sql_path,
            candidate_trace_confidence="HIGH",
            record=case1_record,
        )
        self.assertFalse(id_result.same_occurrence)
        self.assertIn(identity.CATEGORY_MISMATCH, id_result.reasons)
        self.assertIn(identity.SINK_MISMATCH, id_result.reasons)
        # The SQL candidate must resolve on its own merits, independent
        # of Case 1's record -- confirmed via the actual fixture text
        # (already hand-traced to CONFIRMED HIGH during V3 Slim Golden
        # Baseline closeout, re-confirmed here by reading it fresh).
        unsafe_text = _read(f"{SQL_UNSAFE}/UserRepository.cs")
        self.assertIn('$"SELECT Id, Name, Email FROM Users WHERE Name LIKE \'%{query}%\'"', unsafe_text)


class Case4UpstreamControlRemovedTests(unittest.TestCase):
    """Case 4: the SAME Case-1 record exists. A LATER change removes
    the ownership check from ReportService.GetReport (an intermediate
    hop, not the sink). Expected: (c) AND (d) both independently
    catch it."""

    def test_intermediate_hop_regression_forces_full_rederivation(self):
        record = _build_case1_record()
        original_text = _read(f"{AUTHZ_SAFE}/ReportService.cs")
        edited_text = original_text.replace(
            "        if (report is null || report.OwnerUserId != currentUserId)\n        {\n            return null;\n        }\n        return report;",
            "        return report;",
        )
        self.assertNotEqual(original_text, edited_text)
        self.assertNotIn(OWNERSHIP_CHECK_LINE, edited_text)

        hop_confirmed = {eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in CASE1_REACHABILITY_PATH}
        # (d): re-inspecting the SPECIFIC ReportService.cs hop finds the
        # control gone.
        hop_confirmed[eligibility.hop_key(f"tests/fixtures/{AUTHZ_SAFE}/ReportService.cs", "ReportService.GetReport")] = False

        decision = eligibility.decide_reuse(
            record=record,
            candidate_category="BOLA/IDOR",
            candidate_evidence_path=f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs",
            candidate_reachability_path=CASE1_REACHABILITY_PATH,
            candidate_trace_confidence="HIGH",
            # [CORRECTED, per a round-1 independent review Minor: this
            # was previously commented "sink itself unchanged" as if
            # that were why (a) should pass -- but schema section
            # 5.1(a) re-inspects the WHOLE reachabilityPath, not the
            # sink alone, so a fully faithful (a) re-check would also
            # fail here (the changed hop's own safetyPattern text
            # names ReportService.GetReport specifically). This is
            # deliberately held True anyway, per the schema doc's own
            # framing of this case: "a restatement of Case 2's shape
            # phrased to confirm (c)/(d) also independently catch it,
            # not only (a) -- multiple checks agreeing is expected
            # here, not a sign one of them is redundant."]
            pattern_and_scope_match=True,
            known_condition_states={},
            # (c): ReportService.cs is a dependency (derived from
            # reachabilityPath) and it changed.
            changed_files=[f"tests/fixtures/{AUTHZ_SAFE}/ReportService.cs"],
            hop_controls_confirmed=hop_confirmed,
        )
        self.assertFalse(decision.reusable)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, decision.reasons)
        self.assertIn(eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED, decision.reasons)


class Case5NewCallerNewPathTests(unittest.TestCase):
    """Case 5: the SAME Case-1 record exists, ReportService.GetReport's
    ownership check remains completely intact. A NEW file (background
    export job) calls ReportRepository.FindById directly, bypassing
    ReportService entirely. Expected: the reachabilityPath precondition
    rejects this BEFORE (a)-(d) ever run."""

    def test_new_path_never_compared_against_old_record(self):
        record = _build_case1_record()
        # ReportService.cs's control is untouched -- confirm this
        # directly, so the test cannot pass by accident if it were
        # actually broken too.
        self.assertIn(OWNERSHIP_CHECK_LINE, _read(f"{AUTHZ_SAFE}/ReportService.cs"))

        new_path = [
            {"path": f"tests/fixtures/{AUTHZ_SAFE}/BackgroundExportJob.cs", "qualifiedSymbol": "BackgroundExportJob.Handle"},
            {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs", "qualifiedSymbol": "ReportRepository.FindById"},
        ]
        decision = eligibility.decide_reuse(
            record=record,
            candidate_category="BOLA/IDOR",
            candidate_evidence_path=f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs",
            candidate_reachability_path=new_path,
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=None,  # would never even be consulted
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={},
        )
        self.assertFalse(decision.reusable)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, decision.reasons)
        # (a)-(d)'s own reason codes must NOT appear -- they never ran.
        for r in (eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, eligibility.REASON_DEPENDENCY_CHANGED,
                  eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED):
            self.assertNotIn(r, decision.reasons)


class Case6SameFilesDifferentSymbolTests(unittest.TestCase):
    """Case 6: a NEW method ReportService.GetReportForExport is added,
    calling ReportRepository.FindById directly with no ownership check,
    from a NEW controller action. Every FILE in the chain matches Case
    1's, but every SYMBOL except the terminal sink differs. Expected:
    condition (iii)'s exact {path, symbol} match fails -> DIFFERENT
    occurrence -- specifically the case a file-path-only comparison
    would wrongly pass."""

    def test_same_files_different_symbols_is_a_different_occurrence(self):
        record = _build_case1_record()
        new_symbol_path = [
            {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportsController.cs", "qualifiedSymbol": "ReportsController.ExportReport"},
            {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportService.cs", "qualifiedSymbol": "ReportService.GetReportForExport"},
            {"path": f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs", "qualifiedSymbol": "ReportRepository.FindById"},
        ]
        id_result = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path=f"tests/fixtures/{AUTHZ_SAFE}/ReportRepository.cs",
            candidate_reachability_path=new_symbol_path,
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertFalse(id_result.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, id_result.reasons)

        # Prove this is EXACTLY the case a file-path-only (ignoring
        # symbol) comparison would wrongly pass:
        record_files = [e["path"] for e in record["candidateShape"]["reachabilityPath"]]
        candidate_files = [e["path"] for e in new_symbol_path]
        self.assertEqual(record_files, candidate_files)  # same files...
        record_symbols = [e["qualifiedSymbol"] for e in record["candidateShape"]["reachabilityPath"]]
        candidate_symbols = [e["qualifiedSymbol"] for e in new_symbol_path]
        self.assertNotEqual(record_symbols, candidate_symbols)  # ...but different symbols


if __name__ == "__main__":
    unittest.main()
