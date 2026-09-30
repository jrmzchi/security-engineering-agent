"""[V4 release hardening] The NONE gate (none_gate.py, `cli none-gate`) and the signal-pair exception's reporting.

Closes the two Minors recorded in work/v4-release/followup-targeted-none-floor.md:
1. the floor must actually run before a NONE stop (call-order tests below, through the real entry points);
2. what the exception runs and reports must read the same in every document that states it.

What these tests cannot show: that an agent following the Markdown workflow calls the gate. That is disclosed in
none_gate.py and in plays/security-change-detection.md's NONE action.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO)
from tools.context_manifest import cli, none_gate, orchestrator, signal_floor  # noqa: E402
from tools.context_manifest.validator import SCANNER_DOMAIN_MAP, Classification  # noqa: E402

RV18 = os.path.join(REPO, "tests", "fixtures", "csrf_samesite_lax_deceptive.cs")
NONE = Classification(sensitivity="NONE", implicated_domains=frozenset())

AMBIENT = 'services.ConfigureApplicationCookie(o => { o.Cookie.Name = "app"; });\n'
STATE = '[HttpPost("transfer")]\npublic IActionResult Transfer() => Ok();\n'
MARKER = "UNIQUE-FILE-CONTENT-MARKER-7f3a"


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


class _Scope:
    """A temporary scope directory; files are written as given (bytes or text)."""

    def __init__(self, files):
        self.files = files

    def __enter__(self):
        self.root = tempfile.mkdtemp(prefix="none-gate-")
        for name, body in self.files.items():
            path = os.path.join(self.root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(body if isinstance(body, bytes) else body.encode("utf-8"))
        return self.root

    def __exit__(self, *exc):
        shutil.rmtree(self.root, ignore_errors=True)


def _rv18():
    with open(RV18, "rb") as fh:
        return fh.read()


def _cli(args):
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(["none-gate", *args])
    return code, out.getvalue()


class DecideTests(unittest.TestCase):
    def test_both_signals_take_the_exception(self):
        with _Scope({"Startup.cs": _rv18()}) as root:
            d = none_gate.decide(["Startup.cs"], root=root)
        self.assertEqual(d.action, none_gate.TARGETED_EXCEPTION)
        self.assertEqual(d.domains, frozenset({"web-security"}))
        self.assertIn("Startup.cs", d.scope_texts)
        self.assertTrue(any(r.startswith("CSRF-AMBIENT") for r in d.reasons))

    def test_the_pair_may_come_from_two_files(self):
        with _Scope({"Program.cs": AMBIENT, "Controllers/Pay.cs": STATE}) as root:
            d = none_gate.decide(["Program.cs", "Controllers/Pay.cs"], root=root)
        self.assertEqual(d.action, none_gate.TARGETED_EXCEPTION)

    def test_either_half_missing_keeps_the_none_stop(self):
        for name, files in (("ambient only", {"a.cs": AMBIENT}), ("state change only", {"a.cs": STATE}),
                            ("neither", {"README.md": "# Title\nText only.\n"})):
            with self.subTest(case=name), _Scope(files) as root:
                d = none_gate.decide(list(files), root=root)
                self.assertEqual(d.action, none_gate.STOP_NONE)
                self.assertEqual(d.domains, frozenset())

    def test_rv18_with_either_half_removed_stops(self):
        code = _rv18().decode("utf-8")
        for name, text in (("no ambient", code.replace("services.ConfigureApplicationCookie(", "services.Configure(")),
                           ("no state change", code.replace('[HttpGet("delete")]', '[HttpGet("profile")]'))):
            with self.subTest(case=name), _Scope({"a.cs": text}) as root:
                self.assertEqual(none_gate.decide(["a.cs"], root=root).action, none_gate.STOP_NONE)

    def test_nothing_that_cannot_be_checked_is_a_none_stop(self):
        with _Scope({"README.md": "text\n", "sub/x.txt": "x"}) as root:
            cases = {
                "missing file": (["README.md", "gone.cs"], root),
                "a directory": (["sub"], root),
                "no files": ([], root),
                "a bare string": ("README.md", root),
                "not iterable": (42, root),
                "an empty path": ([""], root),
                "a non-string path": ([None], root),
            }
            for name, (paths, r) in cases.items():
                with self.subTest(case=name):
                    d = none_gate.decide(paths, root=r)
                    self.assertEqual(d.action, none_gate.MANUAL_CHECK)
                    self.assertTrue(d.reasons)

    def test_a_file_list_that_raises_is_a_manual_check(self):
        def broken():
            yield "a.cs"
            raise OSError("listing failed")
        self.assertEqual(none_gate.decide(broken()).action, none_gate.MANUAL_CHECK)

    def test_an_unreadable_file_is_a_manual_check(self):
        with _Scope({"a.cs": "x"}) as root, mock.patch("builtins.open", side_effect=PermissionError("denied")):
            d = none_gate.decide(["a.cs"], root=root)
        self.assertEqual(d.action, none_gate.MANUAL_CHECK)
        self.assertIn("PermissionError", " ".join(d.unread))

    def test_readable_files_that_require_a_domain_win_over_unreadable_ones(self):
        with _Scope({"Startup.cs": _rv18()}) as root:
            d = none_gate.decide(["Startup.cs", "gone.cs"], root=root)
        self.assertEqual(d.action, none_gate.TARGETED_EXCEPTION)
        self.assertEqual(len(d.unread), 1)
        self.assertIn("gone.cs", d.unread[0])
        self.assertFalse(any("gone.cs" in r for r in d.reasons))

    def test_utf16_and_utf32_text_does_not_hide_the_pair(self):
        # review Major: these encodings put NULs between ASCII characters
        src = AMBIENT + STATE
        for enc in ("utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be", "utf-8-sig"):
            with self.subTest(encoding=enc), _Scope({"a.cs": src.encode(enc)}) as root:
                self.assertEqual(none_gate.decide(["a.cs"], root=root).action, none_gate.TARGETED_EXCEPTION)
        # Policy round (deliberately conservative): UTF-16/32 is never plain UTF-8, so without the pair it is a
        # MANUAL_CHECK, not a STOP_NONE (it used to be STOP_NONE).
        for enc in ("utf-16", "utf-32"):
            with self.subTest(encoding=enc, half="ambient only"), _Scope({"a.cs": AMBIENT.encode(enc)}) as root:
                self.assertEqual(none_gate.decide(["a.cs"], root=root).action, none_gate.MANUAL_CHECK)

    def test_the_whole_file_is_read(self):
        # review Minor: a signal after a large prefix must still be seen
        with _Scope({"a.cs": "// x\n" * 400000 + AMBIENT + STATE}) as root:
            self.assertEqual(none_gate.decide(["a.cs"], root=root).action, none_gate.TARGETED_EXCEPTION)

    def test_non_utf8_bytes_do_not_hide_the_pair(self):
        with _Scope({"a.cs": b"\xff\xfe\x80 " + AMBIENT.encode() + b"\x81" + STATE.encode()}) as root:
            self.assertEqual(none_gate.decide(["a.cs"], root=root).action, none_gate.TARGETED_EXCEPTION)


class UnicodeTests(unittest.TestCase):
    """[V4 release hardening, policy round] STOP_NONE only for plain UTF-8: every file read, no NUL byte, the whole
    file strict UTF-8, the floor completed with no domain. Anything else is unreliable: MANUAL_CHECK, or
    TARGETED_EXCEPTION when a signal pair is visible anyway (with the unreliable files listed as unread).

    Deliberate, conservative trade-off: UTF-16/32, legacy encodings (Big5, GBK, Shift-JIS, Latin-1) and binary files
    can no longer stop at NONE, even when they hold no signal. A decoder that accepts some bytes is not taken as proof
    that the file's real text was read."""

    STATE_CJK = '[HttpGet("/\u4e22\u5931\u2212\u2714\u2722/delete")]\npublic IActionResult D() => Ok();\n'
    BOMS = {"utf-16-le": b"\xff\xfe", "utf-16-be": b"\xfe\xff", "utf-32-le": b"\xff\xfe\x00\x00",
            "utf-32-be": b"\x00\x00\xfe\xff"}
    UNDECODABLE = b"\x00\xd8\x41\x00" + b"\xd8\x00\x00\x41" + b"\xff\xff\xff\xff\x01"
    # the three constructions the Unicode re-review reproduced through the CLI (an encoding switch mid-line)
    MIDLINE = {
        "a": "// \u8a3b\u89e3\u3001".encode("utf-16-le") + "AddSession();\n[HttpPost]\n\n".encode("utf-8"),
        "b": b"\xff\xfe" + "# \u8a3b\u89e3\u3001".encode("utf-16-le")
             + "from flask import Flask, session\n@app.post('/x')\n\n".encode("utf-8"),
        "c": "from flask import Flask, session".encode("utf-8") + '\u3030\n@app.post("/x")\n'.encode("utf-16-le"),
    }

    def decide(self, files):
        with _Scope(files) as root:
            return none_gate.decide(sorted(files), root=root)

    def one(self, data):
        return self.decide({"a.cs": data})

    def assert_unreliable(self, d, *names):
        self.assertNotEqual(d.action, none_gate.STOP_NONE)
        for n in names:
            self.assertTrue(any(u.startswith(f"{n}: cannot be decoded reliably") for u in d.unread), d.unread)

    # --- the invariant itself -------------------------------------------------------------------------------------

    def test_plain_utf8_problem_is_the_whole_rule(self):
        ok = [b"", b"plain\n", "\ufeffBOM\n".encode("utf-8"), "\u4e2d\u6587 \U0001f600\n".encode("utf-8")]
        bad = [b"a\x00b", b"\xff\xfe" + "x".encode("utf-16-le"), "caf\u00e9".encode("latin-1"), b"\x80",
               "\u4e2d".encode("cp950"), b"\xed\xa0\x80",  # an encoded surrogate: not valid UTF-8
               b"\x89PNG\r\n\x1a\n\x00\x00"]
        for data in ok:
            with self.subTest(ok=data[:10]):
                self.assertIsNone(none_gate.plain_utf8_problem(data))
        for data in bad:
            with self.subTest(bad=data[:10]):
                self.assertIsNotNone(none_gate.plain_utf8_problem(data))

    def test_stop_none_implies_every_file_is_plain_utf8(self):
        inputs = [b"", b"x\n", AMBIENT.encode(), STATE.encode(), "\u4e22\n".encode(), b"\x00", b"x\x00y",
                  "x".encode("utf-16-le"), "x".encode("utf-32"), "caf\u00e9".encode("latin-1"), b"\xc3", self.UNDECODABLE,
                  AMBIENT.encode("utf-16-le"), STATE.encode("gbk")] + list(self.MIDLINE.values())
        for a in inputs:
            for b in (None, b"plain\n", "x".encode("utf-16-be")):
                files = {"a.cs": a} if b is None else {"a.cs": a, "b.cs": b}
                with self.subTest(a=a[:12], b=b):
                    d = self.decide(files)
                    if d.action == none_gate.STOP_NONE:
                        self.assertTrue(all(none_gate.plain_utf8_problem(x) is None for x in files.values()))
                        self.assertEqual(d.unread, ())

    # --- UTF-8 ----------------------------------------------------------------------------------------------------

    def test_utf8_negative_stops_and_positive_fires(self):
        self.assertEqual(self.one("// \u4e2d\u6587\n" + AMBIENT).action, none_gate.STOP_NONE)
        d = self.one((AMBIENT + self.STATE_CJK).encode("utf-8"))
        self.assertEqual((d.action, d.unread), (none_gate.TARGETED_EXCEPTION, ()))

    def test_invalid_utf8_without_nul_is_unreliable(self):
        for name, data in (("lone continuation byte", b"x = 1\n\x80\n"), ("truncated sequence", b"s = '\xe4\xb8'\n"),
                           ("latin-1", "caf\u00e9\n".encode("latin-1"))):
            with self.subTest(case=name):
                d = self.one(data)
                self.assertEqual(d.action, none_gate.MANUAL_CHECK)
                self.assert_unreliable(d, "a.cs")

    # --- UTF-16/32 and BOMs ---------------------------------------------------------------------------------------

    def test_wide_text_with_the_pair_takes_the_exception_and_is_listed_unread(self):
        src = AMBIENT + self.STATE_CJK
        for enc, bom in self.BOMS.items():
            for prefix in (b"", bom):
                with self.subTest(encoding=enc, bom=bool(prefix)):
                    d = self.one(prefix + src.encode(enc))
                    self.assertEqual(d.action, none_gate.TARGETED_EXCEPTION)
                    self.assert_unreliable(d, "a.cs")

    def test_wide_text_without_the_pair_is_a_manual_check_not_a_stop(self):
        # deliberate: these were STOP_NONE before the policy round
        for enc, bom in self.BOMS.items():
            for prefix in (b"", bom):
                for name, src in (("state only", self.STATE_CJK), ("ambient only", AMBIENT),
                                  ("text only", "// \u4e2d\u6587 \u4e22\u2212\n")):
                    with self.subTest(encoding=enc, bom=bool(prefix), case=name):
                        d = self.one(prefix + src.encode(enc))
                        self.assertEqual(d.action, none_gate.MANUAL_CHECK)
                        self.assert_unreliable(d, "a.cs")

    def test_a_bom_that_disagrees_with_the_content_is_never_a_stop(self):
        src = AMBIENT + STATE
        for name, data in (("LE BOM, UTF-16 BE", b"\xff\xfe" + src.encode("utf-16-be")),
                           ("BE BOM, UTF-16 LE", b"\xfe\xff" + src.encode("utf-16-le")),
                           ("UTF-16 LE BOM, UTF-32 LE", b"\xff\xfe" + src.encode("utf-32-le")),
                           ("UTF-32 LE BOM, UTF-16 BE", b"\xff\xfe\x00\x00" + src.encode("utf-16-be")),
                           ("BOM, no pair", b"\xfe\xff" + AMBIENT.encode("utf-16-le"))):
            with self.subTest(case=name):
                self.assert_unreliable(self.one(data), "a.cs")

    # --- mixed encodings, the reproduced cases --------------------------------------------------------------------

    def test_the_three_reproduced_midline_cases_are_never_a_stop(self):
        for name, data in self.MIDLINE.items():
            with self.subTest(case=name):
                d = self.one(data)
                self.assertIn(d.action, (none_gate.MANUAL_CHECK, none_gate.TARGETED_EXCEPTION))
                self.assert_unreliable(d, "a.cs")

    def test_same_line_mixed_encodings_are_never_a_stop(self):
        for name, data in (("UTF-8 then UTF-16 LE on one line", b"x = 1; " + "y = 2\n".encode("utf-16-le")),
                           ("UTF-16 BE then UTF-8", "a\u3001".encode("utf-16-be") + b"b\n"),
                           ("UTF-8 then UTF-32", b"z " + "w\n".encode("utf-32-le"))):
            with self.subTest(case=name):
                self.assert_unreliable(self.one(data), "a.cs")

    # --- binary and multi-file ------------------------------------------------------------------------------------

    def test_binary_files_are_unreliable(self):
        for name, data in (("PNG-like", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(range(256)) * 4),
                           ("undecodable", self.UNDECODABLE), ("all NUL", b"\x00" * 64)):
            with self.subTest(case=name):
                d = self.one(data)
                self.assertEqual(d.action, none_gate.MANUAL_CHECK)
                self.assert_unreliable(d, "a.cs")

    def test_one_unreliable_file_among_plain_ones_blocks_the_stop(self):
        d = self.decide({"a.css": "body { color: #333; }\n", "b.cs": "// fine\n", "c.cs": "x\n".encode("utf-16-le")})
        self.assertEqual(d.action, none_gate.MANUAL_CHECK)
        self.assertEqual(len(d.unread), 1)
        self.assert_unreliable(d, "c.cs")

    def test_a_visible_pair_still_takes_the_exception_despite_an_unreliable_file(self):
        d = self.decide({"Program.cs": AMBIENT + STATE, "logo.png": b"\x89PNG\r\n\x1a\n\x00\x00"})
        self.assertEqual(d.action, none_gate.TARGETED_EXCEPTION)
        self.assert_unreliable(d, "logo.png")

    def test_a_large_unreliable_file_is_bounded_and_unreliable(self):
        big = b"\x00" * (none_gate._WIDE_LIMIT + 4)
        self.assert_unreliable(self.one(big), "a.cs")
        d = self.one(AMBIENT.encode() + STATE.encode() + big)
        self.assertEqual(d.action, none_gate.TARGETED_EXCEPTION)

    # --- CLI ------------------------------------------------------------------------------------------------------

    def test_the_cli_exit_and_output(self):
        with _Scope({"plain.css": "a { }\n", "w.cs": b"\xff\xfe" + (AMBIENT + self.STATE_CJK).encode("utf-16-le"),
                     "m.py": self.MIDLINE["a"], "l.cs": "caf\u00e9\n".encode("latin-1")}) as root:
            code, out = _cli(["--root", root, "plain.css"])
            self.assertEqual((code, out.splitlines()[:2]), (0, ["NONE_GATE", "STOP_NONE"]))
            code, out = _cli(["--root", root, "w.cs"])
            self.assertEqual((code, out.splitlines()[1]), (1, "TARGETED_EXCEPTION web-security"))
            self.assertTrue(any(ln.startswith("unread: w.cs: cannot be decoded reliably") for ln in out.splitlines()))
            for f in ("m.py", "l.cs"):
                code, out = _cli(["--root", root, "plain.css", f])
                self.assertEqual((code, out.splitlines()[1]), (2, "MANUAL_CHECK"))
                self.assertTrue(any(ln.startswith(f"unread: {f}: cannot be decoded reliably") for ln in out.splitlines()))
                self.assertNotIn("STOP_NONE", out)


class CallOrderTests(unittest.TestCase):
    """The real entries (decide, and `cli none-gate` on top of it) call the floor before any NONE stop."""

    def test_decide_runs_the_floor_on_the_texts_before_stopping(self):
        with _Scope({"README.md": "text\n"}) as root, \
                mock.patch.object(none_gate.signal_floor, "required_domains",
                                  wraps=signal_floor.required_domains) as spy:
            d = none_gate.decide(["README.md"], root=root)
        self.assertEqual(d.action, none_gate.STOP_NONE)
        spy.assert_called_once_with({"README.md": "text\n"})

    def test_the_cli_runs_the_floor_before_exit_0(self):
        with _Scope({"README.md": "text\n"}) as root, \
                mock.patch.object(none_gate.signal_floor, "required_domains",
                                  wraps=signal_floor.required_domains) as spy:
            code, out = _cli(["--root", root, "README.md"])
        self.assertEqual((code, out.splitlines()[:2]), (0, ["NONE_GATE", "STOP_NONE"]))
        self.assertEqual(spy.call_count, 1)

    def test_the_floor_result_alone_decides(self):
        forced = signal_floor.SignalFloor(domains=frozenset({"web-security"}), reasons=("forced",))
        with _Scope({"README.md": "text\n"}) as root, \
                mock.patch.object(none_gate.signal_floor, "required_domains", return_value=forced):
            self.assertEqual(none_gate.decide(["README.md"], root=root).action, none_gate.TARGETED_EXCEPTION)
            self.assertEqual(_cli(["--root", root, "README.md"])[0], 1)

    def test_a_floor_that_raises_is_never_a_none_stop(self):
        with _Scope({"README.md": "text\n"}) as root, \
                mock.patch.object(none_gate.signal_floor, "required_domains", side_effect=RuntimeError("boom")):
            d = none_gate.decide(["README.md"], root=root)
            code, out = _cli(["--root", root, "README.md"])
        self.assertEqual(d.action, none_gate.MANUAL_CHECK)
        self.assertEqual(code, 2)
        self.assertIn("MANUAL_CHECK", out)

    def test_a_crash_inside_the_gate_is_exit_2_not_0(self):
        with mock.patch.object(none_gate, "decide", side_effect=RuntimeError("bug")), redirect_stdout(io.StringIO()), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(cli.main(["none-gate", "README.md"]), 2)


class CliTests(unittest.TestCase):
    def test_exit_codes_and_first_lines(self):
        with _Scope({"Startup.cs": _rv18(), "README.md": "text\n"}) as root:
            self.assertEqual(_cli(["--root", root, "README.md"])[0], 0)
            code, out = _cli(["--root", root, "Startup.cs"])
            self.assertEqual((code, out.splitlines()[1]), (1, "TARGETED_EXCEPTION web-security"))
            self.assertEqual(_cli(["--root", root, "gone.cs"])[0], 2)
        self.assertEqual(_cli([])[0], 2)
        self.assertEqual(_cli(["--root"])[0], 2)
        self.assertEqual(_cli(["-h"])[0], 2)          # no help screen that exits 0

    def test_unread_files_get_their_own_lines(self):
        with _Scope({"Startup.cs": _rv18()}) as root:
            code, out = _cli(["--root", root, "Startup.cs", "gone.cs"])
            self.assertEqual(code, 1)
            self.assertIn("unread: gone.cs: not found or not a regular file", out.splitlines())
            self.assertFalse(any(ln.startswith("reason:") and "gone.cs" in ln for ln in out.splitlines()))
            code, out = _cli(["--root", root, "gone.cs"])
            self.assertEqual(code, 2)
            self.assertIn("unread: gone.cs: not found or not a regular file", out.splitlines())

    def test_no_file_content_is_printed(self):
        text = AMBIENT + STATE + "// " + MARKER + "\n"
        with _Scope({"a.cs": text}) as root:
            code, out = _cli(["--root", root, "a.cs"])
        self.assertEqual(code, 1)
        self.assertNotIn(MARKER, out)
        self.assertNotIn("ConfigureApplicationCookie", out)

    def test_the_documented_command_is_the_registered_one(self):
        self.assertIn("none-gate", cli._COMMANDS)


class IntegrationTests(unittest.TestCase):
    """The flow end to end: a separate interpreter runs the CLI on a scope, and its decision feeds the manifest step
    exactly as the NONE action says (same texts as scope_texts, TARGETED, NONE classification)."""

    SHIM = ("import sys; sys.path.insert(0, sys.argv.pop(1)); from tools.context_manifest import cli; "
            "sys.exit(cli.main(sys.argv[1:]))")

    def _run(self, root, *files):
        return subprocess.run([sys.executable, "-B", "-c", self.SHIM, REPO, "none-gate", "--root", root, *files],
                              capture_output=True, text=True, timeout=120,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_exception_path_end_to_end(self):
        with _Scope({"Startup.cs": _rv18()}) as root:
            proc = self._run(root, "Startup.cs")
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(proc.stdout.splitlines()[1], "TARGETED_EXCEPTION web-security")
            decision = none_gate.decide(["Startup.cs"], root=root)
        res = orchestrator.produce_manifest(review_mode="TARGETED", classification=NONE,
                                            target_change_files=["Startup.cs"], scope_texts=decision.scope_texts,
                                            token_provider=lambda: None)
        m = res.manifest
        self.assertEqual(m["domains"], ["web-security"])
        self.assertEqual(m["sensitivity"], "NONE")
        self.assertEqual(m["reviewBudget"], "MINIMAL")
        self.assertEqual(m["scannersSelected"], sorted(SCANNER_DOMAIN_MAP["web-security"]))
        self.assertEqual(m["coverageGaps"], [])
        self.assertTrue(m["validity"]["passed"])
        self.assertIn("signalFloor", res.audit)

    def test_stop_path_end_to_end(self):
        with _Scope({"README.md": "# Title\n"}) as root:
            proc = self._run(root, "README.md")
        self.assertEqual((proc.returncode, proc.stdout.splitlines()[1]), (0, "STOP_NONE"), proc.stderr)

    def test_unreadable_scope_end_to_end(self):
        with _Scope({"README.md": "# Title\n"}) as root:
            proc = self._run(root, "README.md", "missing.cs")
        self.assertEqual((proc.returncode, proc.stdout.splitlines()[1]), (2, "MANUAL_CHECK"), proc.stderr)


class DocumentTests(unittest.TestCase):
    """Every document that states the NONE stop requires the gate, and the exception reports the same way."""

    CD = _flat(_read("plays", "security-change-detection.md"))
    WF = _flat(_read("plays", "secure-development-workflow.md"))

    def test_change_detection_is_the_full_rule(self):
        for phrase in ("Run the NONE gate before stopping.",
                       "python -m tools.context_manifest.cli none-gate --root <repository root> <file>...",
                       "Run it from the kit's root (where `tools/` is)",
                       "Each `unread:` line names a file the gate could not read",
                       "the files it covered (and any it could not read)",
                       "Exit 0 with `STOP_NONE`: stop at NONE.",
                       "Exit 1 with `TARGETED_EXCEPTION <domain>`: take the exception above",
                       "do not stop silently. An `unread:` line saying a file \"cannot be decoded reliably\"",
                       "is a file that is not plain UTF-8 text",
                       "The gate gives this only when every file was read, every file is plain UTF-8 text",
                       "Otherwise you may stop at NONE only if you had reliable text for **every** file",
                       "does not count as checked just because you saw no signal in it",
                       "take the exception's web-security review anyway, conservatively, and list the file as not covered",
                       "or a binary file. Do the manual check",
                       "say in one line that the NONE gate did not permit the stop, why, and what the manual check found",
                       "never a reason to skip the gate",
                       "nothing forces an agent to call it",
                       "the scanners the manifest selects for that domain (`scannersSelected`) and no other",
                       "is recorded in `coverageGaps`",
                       "a finding is validated (`plays/finding-validation.md`), goes through `skills/security-gate`, "
                       "and is reported like any other finding",
                       "Say nothing about other domains: the change was not reviewed for them.",
                       "**Except the signal-pair exception, which reports what it checked**"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.CD)

    def test_the_workflow_row_says_the_same(self):
        for phrase in ("run the NONE gate on the change's files",
                       "(from the kit's root: python -m tools.context_manifest.cli none-gate --root <repository "
                       "root> <file>...)",
                       "Only exit 0 with STOP_NONE stops here; exit 1 with TARGETED_EXCEPTION takes the exception; "
                       "anything else means the manual check.",
                       "runs the manifest's scanners for that domain only (an unavailable one goes to coverageGaps), "
                       "validates and gates a finding, and reports one line when there is none",
                       "The signal-pair exception and a NONE gate that did not run each report"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.WF)

    def test_every_other_statement_points_at_the_gate(self):
        for parts, phrase in ((("skills", "security-change-detection", "SKILL.md"),
                               "stops the workflow only after the NONE gate permits it"),
                              (("skills", "security-review", "SKILL.md"),
                               "`scope_texts` are the texts of the files the NONE gate read"),
                              (("skills", "security-review", "SKILL.md"), "no finding is one line limited to that domain"),
                              (("plays", "review-budget.md"), "which the workflow requires before any NONE stop"),
                              (("tools", "context_manifest", "signal_floor.py"),
                               "which the workflow requires before any NONE stop"),
                              (("tools", "README.md"), "`none-gate` is run by the reviewing agent before a NONE stop"),
                              (("AGENTS.md",), "NONE stops only after the NONE gate permits it"),
                              (("CLAUDE.md",), "checked by its NONE gate"),
                              (("integrations", "claude", "agents", "security-change-detection.md"),
                               "cannot run the NONE gate"),
                              (("integrations", "codex", "README.md"),
                               "stops only after its NONE gate permits it"),
                              (("tools", "context_manifest", "none_gate.py"), "This is a disclosed limit, not a "
                               "mechanical guarantee.")):
            with self.subTest(file="/".join(parts)):
                self.assertIn(phrase, _flat(_read(*parts)))

    def test_the_old_unconditional_none_rules_are_qualified_where_they_stand(self):
        # "no scanner, no summary" and "No security theater" must each carry the exception next to them.
        wf_row = self.WF[self.WF.index("NONE -> stop here."):self.WF.index("LOW -> lightweight")]
        self.assertIn("One exception:", wf_row)
        self.assertIn("NONE gate", wf_row)
        theater = self.CD[self.CD.index("## No security theater"):]
        self.assertIn("Except the signal-pair exception", theater)


if __name__ == "__main__":
    unittest.main()
