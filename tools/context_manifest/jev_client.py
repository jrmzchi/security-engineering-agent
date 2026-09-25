"""Jev (TypeSafe System One) HTTP client -- transport ONLY. V4 Batch 2.

Contract source (verified 2026-09-23 against the official TypeSafe API
docs, read-only):
  POST {base_url}/v1/systemone           Authorization: Bearer <key>
  body: {"state": <str|object|array>, "model": "jev-latest", "questions": {...}}
  200:  {"model": str, "answers": {<id>: <answer>}, "usage": {"input_tokens", "output_tokens"}}
  401 missing/invalid key; 422 request validation; 429 rate limit;
  529 overloaded; response header x-typesafe-request-id.
  Official Python SDK default HTTP timeout: 10.0 s; its default retry
  policy retries {408,429,500-504,599} with backoff (max_retries=2).

Why standard library (urllib) and not `typesafe-sdk` -- a local
implementation decision, recorded per instruction: this kit's runtime
packages are standard-library-only by design (tools/README.md); the SDK
pulls in `httpx2` (and a response-model layer), a new supply-chain
surface for one POST. The SDK's own exception taxonomy is mirrored here
by HTTP status so the outcome mapping is the same as it would be with
the SDK. Cost of the choice: no automatic retries -- deliberately, per
the batch instruction's "first version: no automatic retry"; a single
attempt. If retries are ever added, they must be count- AND
deadline-bounded like the SDK's RetryPolicy.

What the timeout does and does NOT bound [CORRECTED, Batch 2
independent review #4 -- earlier text called this "one bounded call"]:
`timeout_seconds` is passed to `urllib.request.urlopen(timeout=...)`,
which sets a PER-SOCKET-OPERATION timeout (connect, and each individual
send/recv) -- not a wall-clock deadline for the whole call. A server
that keeps sending a byte just inside the timeout can hold one call
open indefinitely; DNS resolution (`getaddrinfo`) is not covered by it
at all; and the response body is read without a size cap. Accepted for
this first version against one fixed, trusted HTTPS endpoint; a true
total deadline would need a watchdog thread or an async client and is
not implemented.

This module does NOT: decide fallback, know about manifests or floors,
read the repository, or read the token from anywhere itself -- the
token is handed in by the orchestrator. It never raises for a failed
call: every failure is a typed `ClientResult` the orchestrator maps to
one of the six fixed outcomes. The token never appears in any result,
message, or repr.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Tuple

DEFAULT_BASE_URL = "https://api.typesafe.ai"
SYSTEMONE_PATH = "/v1/systemone"
DEFAULT_MODEL = "jev-latest"
DEFAULT_TIMEOUT_SECONDS = 10.0  # matches the official SDK's default; per socket operation, not a total deadline
REQUEST_ID_HEADER = "x-typesafe-request-id"

# Typed transport outcomes -- the orchestrator maps these onto the fixed
# six-value jevOutcome enum; this module never speaks that enum itself.
OK = "ok"
AUTH_REJECTED = "auth_rejected"      # 401 / 403 only -- a confirmed authn/authz rejection
TIMEOUT = "timeout"                  # the configured timeout elapsed
HTTP_ERROR = "http_error"            # any other non-2xx (422, 429, 5xx, 529, ...)
TRANSPORT_ERROR = "transport_error"  # no HTTP response at all (DNS, refused, TLS, unexpected exception)
INVALID_JSON = "invalid_json"        # 2xx but the body is not a JSON object

# A raw transport function: (url, headers, body_bytes, timeout) ->
# (status, headers_mapping, body_bytes). Injected in tests; the default
# is urllib. Raising is allowed -- system_one() catches everything.
Transport = Callable[[str, Mapping[str, str], bytes, float], Tuple[int, Mapping[str, str], bytes]]


class ClientConfigError(ValueError):
    """A construction-time problem (bad token shape, bad timeout) -- the
    only thing this module ever raises, and only from __init__."""


@dataclass(frozen=True)
class ClientResult:
    outcome: str
    payload: Optional[Mapping[str, Any]] = None
    status: Optional[int] = None
    detail: str = ""          # human-readable, never contains the token or the response body
    request_id: Optional[str] = None


def _urllib_transport(url: str, headers: Mapping[str, str], body: bytes, timeout: float):
    request = urllib.request.Request(url, data=body, method="POST")
    for name, value in headers.items():
        request.add_header(name, value)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 -- fixed https base URL
        return response.status, dict(response.headers.items()), response.read()


class JevClient:
    def __init__(
        self,
        *,
        token: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Optional[Transport] = None,
    ) -> None:
        if not isinstance(token, str):
            raise ClientConfigError("token must be a string")
        token = token.strip()
        if not token or any(ord(c) < 32 or ord(c) == 127 for c in token):
            raise ClientConfigError("token must be a non-empty string without control characters")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ClientConfigError("timeout_seconds must be a positive number")
        if not isinstance(base_url, str) or not base_url.startswith("https://"):
            raise ClientConfigError("base_url must be an https:// URL")
        if not isinstance(model, str) or not model.strip():
            raise ClientConfigError("model must be a non-empty string")
        self._token = token
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self._transport = transport or _urllib_transport

    def __repr__(self) -> str:  # never leak the token via repr/logging
        return f"JevClient(model={self.model!r}, base_url={self.base_url!r}, timeout_seconds={self.timeout_seconds!r})"

    def system_one(self, state: Any, questions: Mapping[str, Mapping[str, Any]]) -> ClientResult:
        """One POST to /v1/systemone (single attempt; the timeout is per
        socket operation, see the module docstring). Never raises."""
        body = json.dumps({"state": state, "model": self.model, "questions": dict(questions)}, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = self.base_url + SYSTEMONE_PATH
        try:
            status, resp_headers, resp_body = self._transport(url, headers, body, self.timeout_seconds)
        except urllib.error.HTTPError as exc:
            return self._from_http_status(exc.code, dict(exc.headers.items()) if exc.headers else {})
        except (socket.timeout, TimeoutError):
            return ClientResult(outcome=TIMEOUT, detail=f"request exceeded the configured timeout of {self.timeout_seconds}s")
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                return ClientResult(outcome=TIMEOUT, detail=f"request exceeded the configured timeout of {self.timeout_seconds}s")
            return ClientResult(outcome=TRANSPORT_ERROR, detail=f"no HTTP response: {type(reason).__name__ if reason is not None else 'URLError'}")
        except Exception as exc:  # noqa: BLE001 -- a client must never raise into the review
            return ClientResult(outcome=TRANSPORT_ERROR, detail=f"unexpected transport exception: {type(exc).__name__}")

        request_id = _header(resp_headers, REQUEST_ID_HEADER)
        if not (200 <= status < 300):
            return self._from_http_status(status, resp_headers)
        try:
            payload = json.loads(resp_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            # ValueError covers JSONDecodeError and the int-digit limit.
            return ClientResult(outcome=INVALID_JSON, status=status, request_id=request_id,
                                detail=f"2xx body is not valid JSON ({type(exc).__name__})")
        except RecursionError:
            return ClientResult(outcome=INVALID_JSON, status=status, request_id=request_id,
                                detail="2xx body nested too deeply to parse")
        if not isinstance(payload, dict):
            return ClientResult(outcome=INVALID_JSON, status=status, request_id=request_id,
                                detail=f"2xx body is JSON but not an object ({type(payload).__name__})")
        return ClientResult(outcome=OK, payload=payload, status=status, request_id=request_id)

    @staticmethod
    def _from_http_status(status: int, headers: Mapping[str, str]) -> ClientResult:
        request_id = _header(headers, REQUEST_ID_HEADER)
        if status in (401, 403):
            return ClientResult(outcome=AUTH_REJECTED, status=status, request_id=request_id,
                                detail=f"HTTP {status}: authentication/authorization rejected by the API")
        return ClientResult(outcome=HTTP_ERROR, status=status, request_id=request_id, detail=f"HTTP {status}")


def _header(headers: Mapping[str, str], name: str) -> Optional[str]:
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None
