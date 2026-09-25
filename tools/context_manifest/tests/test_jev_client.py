"""jev_client.py -- transport-only behaviour with an injected transport.
No network, no token consumed."""

from __future__ import annotations

import json
import socket
import unittest
import urllib.error

from .. import jev_client

FAKE_TOKEN = "fake-test-token-not-a-real-credential"


def _transport(status=200, body=b'{"model":"jev-1.13.0","answers":{},"usage":{}}', headers=None, raise_exc=None):
    seen = {}

    def t(url, hdrs, payload, timeout):
        seen["url"] = url
        seen["headers"] = dict(hdrs)
        seen["body"] = payload
        seen["timeout"] = timeout
        if raise_exc is not None:
            raise raise_exc
        return status, dict(headers or {}), body

    return t, seen


class ConstructionTests(unittest.TestCase):
    def test_rejects_bad_tokens_and_config(self):
        for bad in ("", "   ", "abc\ndef", "tab\tkey", None, 5):
            with self.subTest(token=bad):
                with self.assertRaises(jev_client.ClientConfigError):
                    jev_client.JevClient(token=bad)
        with self.assertRaises(jev_client.ClientConfigError):
            jev_client.JevClient(token=FAKE_TOKEN, timeout_seconds=0)
        with self.assertRaises(jev_client.ClientConfigError):
            jev_client.JevClient(token=FAKE_TOKEN, timeout_seconds=True)
        with self.assertRaises(jev_client.ClientConfigError):
            jev_client.JevClient(token=FAKE_TOKEN, base_url="http://api.typesafe.ai")

    def test_repr_never_contains_token(self):
        c = jev_client.JevClient(token=FAKE_TOKEN)
        self.assertNotIn(FAKE_TOKEN, repr(c))
        self.assertNotIn(FAKE_TOKEN, str(c))

    def test_defaults_match_verified_contract(self):
        c = jev_client.JevClient(token=FAKE_TOKEN)
        self.assertEqual(c.base_url, "https://api.typesafe.ai")
        self.assertEqual(c.model, "jev-latest")
        self.assertEqual(c.timeout_seconds, 10.0)


class RequestShapeTests(unittest.TestCase):
    def test_request_is_bearer_post_to_v1_systemone_with_contract_body(self):
        t, seen = _transport()
        c = jev_client.JevClient(token=FAKE_TOKEN, transport=t, timeout_seconds=3.5)
        r = c.system_one({"a": 1}, {"q": {"type": "noul", "instructions": "x"}})
        self.assertEqual(r.outcome, jev_client.OK)
        self.assertEqual(seen["url"], "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(seen["headers"]["Authorization"], f"Bearer {FAKE_TOKEN}")
        self.assertEqual(seen["timeout"], 3.5)
        body = json.loads(seen["body"].decode("utf-8"))
        self.assertEqual(set(body), {"state", "model", "questions"})
        self.assertEqual(body["model"], "jev-latest")
        self.assertEqual(body["state"], {"a": 1})

    def test_request_id_header_is_captured(self):
        t, _ = _transport(headers={"X-TypeSafe-Request-Id": "abc123"})
        r = jev_client.JevClient(token=FAKE_TOKEN, transport=t).system_one("s", {"q": {"type": "noul"}})
        self.assertEqual(r.request_id, "abc123")


class OutcomeClassificationTests(unittest.TestCase):
    def _run(self, **kw):
        t, _ = _transport(**kw)
        return jev_client.JevClient(token=FAKE_TOKEN, transport=t).system_one("s", {"q": {"type": "noul"}})

    def test_401_and_403_are_auth_rejected_only(self):
        for status in (401, 403):
            with self.subTest(status=status):
                r = self._run(status=status, body=b"{}")
                self.assertEqual(r.outcome, jev_client.AUTH_REJECTED)
                self.assertEqual(r.status, status)

    def test_other_http_errors_are_http_error_not_auth(self):
        for status in (400, 404, 422, 429, 500, 502, 503, 529):
            with self.subTest(status=status):
                r = self._run(status=status, body=b'{"error":"x"}')
                self.assertEqual(r.outcome, jev_client.HTTP_ERROR)
                self.assertEqual(r.status, status)

    def test_http_error_via_urllib_exception_path(self):
        exc = urllib.error.HTTPError("https://api.typesafe.ai/v1/systemone", 401, "Unauthorized", None, None)
        r = self._run(raise_exc=exc)
        self.assertEqual(r.outcome, jev_client.AUTH_REJECTED)
        exc529 = urllib.error.HTTPError("https://api.typesafe.ai/v1/systemone", 529, "Overloaded", None, None)
        self.assertEqual(self._run(raise_exc=exc529).outcome, jev_client.HTTP_ERROR)

    def test_timeouts_are_timeout(self):
        for exc in (socket.timeout("t"), TimeoutError("t"), urllib.error.URLError(socket.timeout("t"))):
            with self.subTest(exc=type(exc).__name__):
                r = self._run(raise_exc=exc)
                self.assertEqual(r.outcome, jev_client.TIMEOUT)

    def test_connection_failures_and_unexpected_exceptions_are_transport_error(self):
        for exc in (urllib.error.URLError(ConnectionRefusedError()), OSError("boom"), RuntimeError("weird")):
            with self.subTest(exc=type(exc).__name__):
                r = self._run(raise_exc=exc)
                self.assertEqual(r.outcome, jev_client.TRANSPORT_ERROR)

    def test_non_json_and_non_object_bodies_are_invalid_json(self):
        for body in (b"not json", b"```json\n{}\n```", b"[1,2]", b'"str"', b"\xff\xfe", b"{" , b"[" + b"1" * 6000 + b"]"):
            with self.subTest(body=body[:12]):
                r = self._run(status=200, body=body)
                self.assertEqual(r.outcome, jev_client.INVALID_JSON)

    def test_details_never_contain_token_or_body(self):
        t, _ = _transport(status=500, body=b'{"leak":"' + FAKE_TOKEN.encode() + b'"}')
        r = jev_client.JevClient(token=FAKE_TOKEN, transport=t).system_one("s", {"q": {"type": "noul"}})
        self.assertNotIn(FAKE_TOKEN, r.detail)
        self.assertNotIn("leak", r.detail)
        r2 = self._run(status=200, body=b"secret-looking body " + FAKE_TOKEN.encode())
        self.assertNotIn(FAKE_TOKEN, r2.detail)

    def test_never_raises(self):
        class Weird(Exception):
            pass
        self.assertEqual(self._run(raise_exc=Weird()).outcome, jev_client.TRANSPORT_ERROR)


if __name__ == "__main__":
    unittest.main()
