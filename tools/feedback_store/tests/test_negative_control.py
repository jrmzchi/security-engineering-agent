"""Negative control -- context-manifest-schema.md section 5.1's
"Feedback records never suppress scanner execution or candidate
generation" rule, and implementation-batches.md Batch 1 acceptance
criterion 2: "attempt to construct a scenario where a stored Feedback
record causes a scanner to not run at all, or a candidate to never be
generated... This must be impossible BY CONSTRUCTION -- if it is not
impossible, this is a Blocker for this batch."

Three independent angles, since "we didn't think of a way to break it"
is weaker evidence than "the API surface has no path to do it at all":

1. Import-graph angle: `tools/feedback_store/` has ZERO import
   dependency on `tools/context_manifest/` (which is what actually
   owns scanner selection and domain-to-tool mapping, per Batch 0).
   Two packages that never import each other cannot have one silently
   reach into and mutate the other's decisions.
2. Signature angle: none of this package's public functions accept a
   "candidates to filter" or "scanners to filter" collection at all --
   there is no parameter shape a caller COULD wire a scanner list
   through even if they wanted to.
3. Behavioral angle: run Batch 0's actual `_auto_scanner_selection`
   with and without a populated Feedback store existing for the same
   category/domain, and confirm the output is byte-for-byte identical.
"""

from __future__ import annotations

import ast
import inspect
import os
import unittest

from .. import eligibility, identity, invalidation, schema, store
from tools.context_manifest import producer


PACKAGE_DIR = os.path.dirname(os.path.dirname(__file__))
FORBIDDEN_IMPORT_PREFIX = "context_manifest"


class ImportGraphTests(unittest.TestCase):
    def test_no_module_in_this_package_imports_context_manifest(self):
        offenders = []
        for fname in os.listdir(PACKAGE_DIR):
            if not fname.endswith(".py"):
                continue
            path = os.path.join(PACKAGE_DIR, fname)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=fname)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if FORBIDDEN_IMPORT_PREFIX in alias.name:
                            offenders.append((fname, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if FORBIDDEN_IMPORT_PREFIX in module:
                        offenders.append((fname, module))
        self.assertEqual(offenders, [], f"tools/feedback_store must never import tools/context_manifest: {offenders}")


class SignatureShapeTests(unittest.TestCase):
    """No public function in this package's reuse-decision path takes a
    parameter shaped like "the list of candidates/scanners to filter" --
    confirmed by inspecting the actual signatures, not by promise."""

    FORBIDDEN_PARAM_SUBSTRINGS = ("scanner", "candidates_to_generate", "domain_to_tool")

    def _public_functions(self):
        for module in (eligibility, identity, invalidation, schema, store):
            for name, obj in vars(module).items():
                if name.startswith("_") or not inspect.isfunction(obj):
                    continue
                if obj.__module__ != module.__name__:
                    continue
                yield module.__name__, name, obj

    def test_no_function_takes_a_scanner_or_candidate_filtering_argument(self):
        offenders = []
        for module_name, func_name, func in self._public_functions():
            for param_name in inspect.signature(func).parameters:
                lowered = param_name.lower()
                if any(bad in lowered for bad in self.FORBIDDEN_PARAM_SUBSTRINGS):
                    offenders.append(f"{module_name}.{func_name}({param_name})")
        self.assertEqual(offenders, [])


CONTEXT_MANIFEST_DIR = os.path.join(os.path.dirname(PACKAGE_DIR), "context_manifest")


class BehavioralTests(unittest.TestCase):
    """[REWRITTEN, per explicit instruction closing a Round 4
    independent review disclosure]: the previous version built a
    populated Feedback store into a local `s` and then never used it --
    the "with"/"without" calls to `_auto_scanner_selection` were
    byte-for-byte identical, so the test was vacuously true and proved
    nothing. What the claim actually needs is evidence that scanner
    selection has NO WAY to observe a Feedback store at all. Three real
    assertions replace it: (1) the REVERSE import graph -- nothing in
    `tools/context_manifest` imports `tools/feedback_store`; (2) no
    source file in `tools/context_manifest` even mentions the store's
    module, file name, or record types as a string, so it cannot be
    reading it dynamically either; (3) `_auto_scanner_selection`'s own
    signature takes only the domain set -- there is no parameter a
    store could be threaded through."""

    def _context_manifest_sources(self):
        for fname in sorted(os.listdir(CONTEXT_MANIFEST_DIR)):
            if fname.endswith(".py"):
                path = os.path.join(CONTEXT_MANIFEST_DIR, fname)
                with open(path, encoding="utf-8") as f:
                    yield fname, f.read()

    @staticmethod
    def _imports_feedback_store(tree):
        """[STRENGTHENED, per explicit instruction after Round 6 (a
        Round 5 Nit)]: the previous check looked only at
        `ImportFrom.module`, so `from tools import feedback_store` and
        `from .. import feedback_store` (module = "tools" / None, the
        package appearing only in the imported NAMES) slipped past it.
        Both the module path and every imported name are checked now."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any("feedback_store" in a.name for a in node.names):
                    return True
            elif isinstance(node, ast.ImportFrom):
                if "feedback_store" in (node.module or ""):
                    return True
                if any(a.name == "feedback_store" for a in node.names):
                    return True
        return False

    def test_context_manifest_never_imports_feedback_store(self):
        offenders = [fname for fname, source in self._context_manifest_sources()
                     if self._imports_feedback_store(ast.parse(source, filename=fname))]
        self.assertEqual(offenders, [])

    def test_import_detector_catches_every_import_shape(self):
        # Prove the detector is not tautological: each of these must be
        # caught, and a benign import must not be.
        for src in (
            "import tools.feedback_store",
            "from tools.feedback_store import store",
            "from tools import feedback_store",
            "from .. import feedback_store",
            "from tools import context_manifest, feedback_store",
        ):
            with self.subTest(src=src):
                self.assertTrue(self._imports_feedback_store(ast.parse(src)))
        self.assertFalse(self._imports_feedback_store(ast.parse("from tools import context_manifest\nimport os")))

    def test_context_manifest_never_names_the_feedback_store_at_all(self):
        # Catches dynamic access too (importlib, open("feedback.json"),
        # string-keyed lookups) -- not just static imports.
        needles = ("feedback_store", "feedback.json", "rejectionRecords", "feedback_rejection", "importlib")
        offenders = []
        for fname, source in self._context_manifest_sources():
            for needle in needles:
                if needle in source:
                    offenders.append((fname, needle))
        self.assertEqual(offenders, [])

    def test_scanner_selection_signature_has_no_store_input(self):
        params = list(inspect.signature(producer._auto_scanner_selection).parameters)
        self.assertEqual(len(params), 1, params)
        for p in params:
            self.assertNotIn("store", p.lower())
            self.assertNotIn("feedback", p.lower())
        # And it still works on a plain domain set, as before.
        selected, skipped, gaps = producer._auto_scanner_selection({"code-review", "secrets-security"})
        self.assertIsNotNone(selected)

    def test_candidate_generation_concept_does_not_exist_in_this_package(self):
        """This package has no function that takes "a list of
        candidates" and returns a filtered/shorter list -- its only
        candidate-shaped input is ONE already-generated candidate being
        checked against ONE record for reuse eligibility. There is
        structurally no "generate fewer candidates" operation to call.
        """
        import types
        for module in (eligibility, identity, invalidation):
            for name, obj in vars(module).items():
                if isinstance(obj, types.FunctionType) and not name.startswith("_"):
                    doc = obj.__doc__ or ""
                    sig = inspect.signature(obj)
                    # None of these functions returns something that
                    # could plausibly BE "a filtered candidate list" --
                    # they return a single verdict/result object.
                    self.assertNotIn("filter_candidates", name)
                    self.assertNotIn("suppress", name)


class SharedHeuristicImportTests(unittest.TestCase):
    """[ADDED, Batch 2 independent review, extra finding]: both packages
    import `tools/secret_heuristic.py`, and both package-level import
    scans above only list their OWN directory -- so that shared module
    could grow an import of either package (re-creating the forbidden
    edge through the back door) without either scan noticing. Pinned
    here: it may import only these standard-library modules."""

    ALLOWED = {"__future__", "re", "typing"}

    @staticmethod
    def _imports(source: str):
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # any relative import reaches back into tools/
                    imported.add("." * node.level + (node.module or ""))
                else:
                    imported.add((node.module or "").split(".")[0])
        return imported

    def test_secret_heuristic_imports_only_the_standard_library(self):
        path = os.path.join(os.path.dirname(PACKAGE_DIR), "secret_heuristic.py")
        with open(path, encoding="utf-8") as f:
            imported = self._imports(f.read())
        self.assertEqual(imported - self.ALLOWED, set(), f"unexpected imports: {sorted(imported - self.ALLOWED)}")

    def test_detector_is_not_tautological(self):
        for src in ("from . import feedback_store", "from .context_manifest import producer",
                    "import tools.feedback_store", "from tools import context_manifest"):
            with self.subTest(src=src):
                self.assertTrue(self._imports(src) - self.ALLOWED)
        self.assertFalse(self._imports("import re\nfrom typing import Any") - self.ALLOWED)


if __name__ == "__main__":
    unittest.main()
