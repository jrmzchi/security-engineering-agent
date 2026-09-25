from __future__ import annotations

import unittest

from .. import schema


def _valid_kwargs(**overrides):
    base = dict(
        record_id="r1",
        category="BOLA/IDOR",
        suspicion_pattern="object reference from caller-supplied ID, no visible check",
        safety_pattern="ownership check enforced before returning result",
        reachability_path=[
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ],
        rejection_reason="ownership check present",
        evidence={"path": "a/Repository.cs", "observation": "no check at sink, enforced upstream"},
        scope="applies to Controller.Get -> Repository.FindById specifically",
        trace_confidence="HIGH",
        last_validation={"timestamp": "2026-09-23T00:00:00Z", "commit": "abc123", "validatedBy": "human"},
    )
    base.update(overrides)
    return base


class NewRejectionRecordTests(unittest.TestCase):
    def test_builds_valid_record(self):
        rec = schema.new_rejection_record(**_valid_kwargs())
        self.assertEqual(rec["recordType"], schema.RECORD_TYPE_REJECTION)
        self.assertEqual(rec["dependencies"], ["a/Controller.cs", "a/Repository.cs"])

    def test_rejects_non_high_trace_confidence(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(trace_confidence="MEDIUM"))
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(trace_confidence="LOW"))

    def test_rejects_invalid_confidence_value(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(trace_confidence="CERTAIN"))

    def test_rejects_empty_reachability_path(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(reachability_path=[]))

    def test_rejects_hop_missing_qualified_symbol(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(reachability_path=[{"path": "a/Controller.cs"}]))

    def test_rejects_absolute_path_in_reachability_path(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(
                reachability_path=[{"path": "/etc/passwd", "qualifiedSymbol": "Some.Symbol"}]
            ))

    def test_rejects_dotdot_in_evidence_path(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(
                evidence={"path": "a/../b/Repository.cs", "observation": "x"}
            ))

    def test_dependencies_auto_derived_when_omitted(self):
        rec = schema.new_rejection_record(**_valid_kwargs(dependencies=None))
        self.assertEqual(set(rec["dependencies"]), {"a/Controller.cs", "a/Repository.cs"})

    def test_caller_supplied_dependencies_must_be_superset(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(dependencies=["a/Controller.cs"]))  # missing Repository.cs

    def test_caller_supplied_dependencies_may_add_extra_files(self):
        rec = schema.new_rejection_record(**_valid_kwargs(
            dependencies=["a/Controller.cs", "a/Repository.cs", "config/feature-flags.json"]
        ))
        self.assertIn("config/feature-flags.json", rec["dependencies"])

    def test_rejects_jev_as_validated_by(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(
                last_validation={"timestamp": "t", "commit": "c", "validatedBy": "jev"}
            ))
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(
                last_validation={"timestamp": "t", "commit": "c", "validatedBy": "Jev"}
            ))

    def test_rejects_missing_last_validation(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(last_validation=None))

    def test_rejects_negative_reuse_count(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(reuse_count=-1))

    def test_rejects_bool_as_reuse_count(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(**_valid_kwargs(reuse_count=True))

    def test_rejects_unqualified_symbol(self):
        """[ADDED, per a round-1 independent review Major] a bare
        symbol like "Get" cannot distinguish two different methods
        that happen to share a name -- e.g. an authorized ReportView.Get
        and an unauthorized ExportView.Get, both calling the same
        repository method, would produce IDENTICAL {path, symbol} hops
        and be wrongly treated as the same occurrence. Reject any
        unqualified symbol at construction time -- this makes that
        specific counterexample impossible to even represent, not just
        detected later."""
        for bad_symbol in (
            "Get", "GetReport", "FindById", "x", "GetReport(int)",
            "GetReport(System.Int32)", "Get(List<System.String>)", "get(a::b)",
        ):
            # "GetReport(int)" [ADDED, per the qualifiedSymbol redesign]:
            # an arity suffix alone, with no enclosing namespace/type,
            # still cannot distinguish two different classes that each
            # declare a same-named overload -- the exact C# collision
            # this redesign closes.
            # "GetReport(System.Int32)" / "Get(List<System.String>)" /
            # "get(a::b)" [ADDED, per a Round 3 independent review
            # Minor]: a qualification marker embedded ONLY inside the
            # parameter signature, with no real namespace/type before
            # the method name, used to pass this check -- it looks for
            # markers anywhere in the whole string. These three all have
            # a marker character present, but none of them actually
            # names an enclosing type.
            with self.assertRaises(schema.SchemaError):
                schema.new_rejection_record(**_valid_kwargs(
                    reachability_path=[
                        {"path": "a/Controller.cs", "qualifiedSymbol": bad_symbol},
                        {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
                    ]
                ))

    def test_accepts_qualified_symbol_shapes(self):
        """[UPDATED, per the qualifiedSymbol redesign]: a bare name plus
        only an arity suffix -- e.g. "GetReport(int)" with no enclosing
        type -- is no longer accepted here. It cannot distinguish two
        different classes that each declare a `GetReport(int)` method,
        which is exactly the C# overload-collision counterexample this
        redesign exists to close. Every accepted shape below carries a
        real namespace/type qualifier in addition to any signature."""
        for good_symbol in (
            "ReportService.GetReport",
            "ReportService.GetReport(int)",
            "Namespace::Class::Method",
            "Handler#call",
        ):
            rec = schema.new_rejection_record(**_valid_kwargs(
                reachability_path=[
                    {"path": "a/Controller.cs", "qualifiedSymbol": good_symbol},
                    {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
                ]
            ))
            self.assertIsInstance(rec, dict)

    def test_rejects_empty_string_fields(self):
        for field in ("category", "suspicion_pattern", "safety_pattern", "rejection_reason", "scope"):
            with self.assertRaises(schema.SchemaError):
                schema.new_rejection_record(**_valid_kwargs(**{field: "   "}))

    def test_rejects_empty_or_whitespace_qualifiedSymbol(self):
        """[ADDED, per the qualifiedSymbol redesign's required test
        matrix]: an empty or whitespace-only qualifiedSymbol must refuse
        record creation just like a missing key does -- it can never
        uniquely identify anything."""
        for blank in ("", "   ", "\t"):
            with self.subTest(value=blank):
                with self.assertRaises(schema.SchemaError):
                    schema.new_rejection_record(**_valid_kwargs(
                        reachability_path=[
                            {"path": "a/Controller.cs", "qualifiedSymbol": blank},
                            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
                        ]
                    ))

    def test_rejects_non_string_qualifiedSymbol(self):
        for bad_value in (None, 123, True, ["Controller", "Get"]):
            with self.subTest(value=bad_value):
                with self.assertRaises(schema.SchemaError):
                    schema.new_rejection_record(**_valid_kwargs(
                        reachability_path=[
                            {"path": "a/Controller.cs", "qualifiedSymbol": bad_value},
                            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
                        ]
                    ))


class LegacyRecordAuditValidationTests(unittest.TestCase):
    """[ADDED, per explicit instruction for the schema-version-2
    migration]: `validate_legacy_rejection_record_for_audit` is
    deliberately lenient -- it accepts the old bare-`symbol` shape for
    audit-only display -- but must still reject a record that isn't
    even internally well-formed, and must never be confused with the
    strict version-2 validator."""

    def _legacy_record(self):
        return {
            "recordType": schema.RECORD_TYPE_REJECTION,
            "recordId": "legacy1",
            "candidateShape": {
                "category": "BOLA/IDOR",
                "reachabilityPath": [
                    {"path": "a/Controller.cs", "symbol": "Get"},
                    {"path": "a/Repository.cs", "symbol": "FindById"},
                ],
            },
            "rejectionReason": "ownership check present",
            "evidence": {"path": "a/Repository.cs", "observation": "o"},
            "scope": "this path only",
        }

    def test_accepts_the_old_bare_symbol_shape(self):
        schema.validate_legacy_rejection_record_for_audit(self._legacy_record())  # must not raise

    def test_strict_validator_refuses_the_same_legacy_record(self):
        """Proves the two validators are genuinely different -- the
        lenient one accepting a shape does not mean the strict one
        would too."""
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(self._legacy_record())

    def test_legacy_validator_still_rejects_a_genuinely_malformed_record(self):
        broken = self._legacy_record()
        del broken["candidateShape"]
        with self.assertRaises(schema.SchemaError):
            schema.validate_legacy_rejection_record_for_audit(broken)

    def test_legacy_validator_rejects_wrong_record_type(self):
        wrong_type = self._legacy_record()
        wrong_type["recordType"] = schema.RECORD_TYPE_MISS
        with self.assertRaises(schema.SchemaError):
            schema.validate_legacy_rejection_record_for_audit(wrong_type)


class SchemaVersionConstantsTests(unittest.TestCase):
    """[ADDED, per explicit instruction]: guards against silently
    "bumping the version number and pretending migration is done" --
    the two version constants must actually be distinct, and neither
    schema.py nor store.py may expose any function whose name suggests
    an automatic upgrade/migration path from v1 to v2 (the only route
    back to reusable is a genuine full re-derivation, never a guess)."""

    def test_schema_version_and_legacy_version_are_distinct(self):
        self.assertNotEqual(schema.SCHEMA_VERSION, schema.LEGACY_SCHEMA_VERSION)
        self.assertEqual(schema.SCHEMA_VERSION, 2)
        self.assertEqual(schema.LEGACY_SCHEMA_VERSION, 1)

    def test_no_automatic_upgrade_function_exists(self):
        forbidden_substrings = ("upgrade", "migrate", "auto_convert")
        import inspect
        from .. import store as store_module
        for module in (schema, store_module):
            for name, _ in inspect.getmembers(module, inspect.isfunction):
                lowered = name.lower()
                for bad in forbidden_substrings:
                    self.assertNotIn(
                        bad, lowered,
                        f"{module.__name__}.{name} looks like an auto-upgrade path -- "
                        "the only legitimate route from a legacy record to a reusable "
                        "v2 one is a fresh, full independent re-derivation.",
                    )


class SecretDetectionTests(unittest.TestCase):
    def test_aws_key_shaped_string_refused(self):
        with self.assertRaises(schema.LikelySecretError):
            schema.new_rejection_record(**_valid_kwargs(
                rejection_reason="uses AKIAABCDEFGHIJKLMNOP as a test key"
            ))

    def test_pem_private_key_refused(self):
        with self.assertRaises(schema.LikelySecretError):
            schema.new_rejection_record(**_valid_kwargs(
                scope="see -----BEGIN RSA PRIVATE KEY----- block in config"
            ))

    def test_inline_secret_assignment_refused(self):
        with self.assertRaises(schema.LikelySecretError):
            schema.new_rejection_record(**_valid_kwargs(
                rejection_reason='password: "hunter2hunter2hunter2"'
            ))

    def test_snake_case_secret_shapes_now_caught(self):
        """[ADDED, per a round-1 independent review Minor]: `\\b` is
        relative to `\\w`, which includes `_` -- so `\\bsecret\\b`
        could NEVER match inside "client_secret" (no word boundary
        exists anywhere inside an all-word-character string). This
        missed the exact snake_case shape most real secrets use."""
        for shape in (
            'client_secret="Zx9Qw8Er7Ty6Ui5Op4"',
            "db_password=P@ssw0rd12345",
            "access_token: ghp_abcdefghijklmnopqrst",
        ):
            with self.subTest(shape=shape):
                with self.assertRaises(schema.LikelySecretError):
                    schema.new_rejection_record(**_valid_kwargs(rejection_reason=shape))

    def test_json_quoted_key_shape_now_caught(self):
        """[ADDED, per a round-2 independent review Nit]: the keyword's
        own closing quote in `"api_key": "..."` previously blocked the
        pattern from ever reaching the `[:=]` character."""
        with self.assertRaises(schema.LikelySecretError):
            schema.new_rejection_record(**_valid_kwargs(
                rejection_reason='config has "api_key": "sk_live_abcdefghijklmnop"'
            ))

    def test_miss_record_evidence_is_scanned_for_secrets(self):
        """[ADDED, per a round-1 independent review Minor]: the
        previous version only checked `evidence is not None` for miss
        records, never actually scanning its string content -- the
        same secret-shaped text new_rejection_record refuses passed
        through unchecked here."""
        with self.assertRaises(schema.LikelySecretError):
            schema.new_miss_record(
                record_id="m1", layer="routing", observed_miss="x", expected_finding="y",
                prior_layers_passed=[],
                evidence={"path": "a", "observation": 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'},
                remediation="r", scope="s", human_confirmed_by="h", created_at="t",
            )
        # Also catches it nested inside a list of evidence entries.
        with self.assertRaises(schema.LikelySecretError):
            schema.new_miss_record(
                record_id="m2", layer="routing", observed_miss="x", expected_finding="y",
                prior_layers_passed=[],
                evidence=[{"path": "a", "observation": "fine"}, {"path": "b", "observation": "AKIAABCDEFGHIJKLMNOP"}],
                remediation="r", scope="s", human_confirmed_by="h", created_at="t",
            )

    def test_qualifiedSymbol_field_itself_is_scanned_for_secrets(self):
        """[ADDED, per the qualifiedSymbol redesign's "preserve Round 2
        fixes" checklist]: secret detection must still cover the
        `qualifiedSymbol` field itself, now that it carries a different
        string shape (namespace/type/signature) than the old bare
        `symbol` field did -- confirms `_check_no_secret` is still
        actually wired into `_validate_reachability_path`, not just
        assumed to still apply because other fields are covered."""
        with self.assertRaises(schema.LikelySecretError):
            schema.new_rejection_record(**_valid_kwargs(
                reachability_path=[
                    {"path": "a/Controller.cs", "qualifiedSymbol": 'Controller.Get(client_secret="Zx9Qw8Er7Ty6Ui5Op4")'},
                    {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
                ]
            ))

    def test_ordinary_prose_not_flagged(self):
        rec = schema.new_rejection_record(**_valid_kwargs(
            rejection_reason="query is bound via command.Parameters.AddWithValue, not string-interpolated"
        ))
        self.assertIsInstance(rec, dict)


class ValidateRejectionRecordTests(unittest.TestCase):
    def test_accepts_a_valid_record(self):
        rec = schema.new_rejection_record(**_valid_kwargs())
        schema.validate_rejection_record(rec)  # must not raise

    def test_rejects_wrong_record_type(self):
        rec = schema.new_rejection_record(**_valid_kwargs())
        rec["recordType"] = "something_else"
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(rec)

    def test_rejects_missing_field(self):
        rec = schema.new_rejection_record(**_valid_kwargs())
        del rec["dependencies"]
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(rec)

    def test_rejects_dependencies_not_superset_of_reachability_path_when_hand_edited(self):
        rec = schema.new_rejection_record(**_valid_kwargs())
        rec["dependencies"] = ["a/Controller.cs"]  # hand-edited to drop Repository.cs
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(rec)

    def test_rejects_hand_edited_jev_validated_by(self):
        rec = schema.new_rejection_record(**_valid_kwargs())
        rec["lastValidation"]["validatedBy"] = "jev"
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(rec)


class MissRecordTests(unittest.TestCase):
    def _valid_kwargs(self, **overrides):
        base = dict(
            record_id="m1",
            layer="routing",
            observed_miss="SQL injection via a new endpoint",
            expected_finding="CONFIRMED HIGH SQL injection",
            prior_layers_passed=[],
            evidence={"path": "a/Controller.cs", "observation": "endpoint never routed to code-review domain"},
            remediation="fix classification table for this endpoint shape",
            scope="this endpoint shape only",
            human_confirmed_by="example-reviewer",
            created_at="2026-09-23T00:00:00Z",
        )
        base.update(overrides)
        return base

    def test_builds_valid_miss_record(self):
        rec = schema.new_miss_record(**self._valid_kwargs())
        self.assertEqual(rec["recordType"], schema.RECORD_TYPE_MISS)

    def test_rejects_invalid_layer(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_miss_record(**self._valid_kwargs(layer="not_a_layer"))

    def test_rejects_layer_in_its_own_prior_layers_passed(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_miss_record(**self._valid_kwargs(layer="reasoning", prior_layers_passed=["routing", "reasoning"]))

    def test_rejects_missing_evidence(self):
        with self.assertRaises(schema.SchemaError):
            schema.new_miss_record(**self._valid_kwargs(evidence=None))

    def test_validate_miss_record_accepts_valid(self):
        rec = schema.new_miss_record(**self._valid_kwargs())
        schema.validate_miss_record(rec)


if __name__ == "__main__":
    unittest.main()
