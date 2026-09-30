"""Injected fake Jev clients for the deterministic test layer -- no
network, no token consumed, fully reproducible. V4 Batch 2.

`answer_payload()` builds a syntactically valid /v1/systemone response
for a given request from explicit decisions (which domains are "yes",
which budget, ...), so a test states its scenario in manifest terms and
the fake does the JSON plumbing. Every field can then be corrupted by
the test to exercise the adapter's strictness.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from .. import jev_client
from ..domains import ALL_DOMAINS


def answer_payload(
    request,
    *,
    yes_domains: Iterable[str],
    review_budget: str,
    budget_factor: str = "none",
    sensitivity: Optional[str] = None,
    priorities: Optional[Mapping[str, float]] = None,
    reuse_yes: Iterable[str] = (),
    confidence: float = 0.97,
    model: str = "jev-1.13.0",
    usage: Optional[Mapping[str, Any]] = None,
    extra_answers: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    yes = set(yes_domains)
    reuse = set(reuse_yes)
    priorities = dict(priorities or {})
    answers: Dict[str, Any] = {}
    for key, q in request.questions.items():
        if key == "sensitivity":
            answers[key] = _choice(q["criteria"], sensitivity, confidence)
        elif key.startswith("domain_"):
            d = key[len("domain_"):]
            answers[key] = {"type": "noul", "noul": 0.93 if d in yes else 0.04}
        elif key.startswith("priority_"):
            d = key[len("priority_"):]
            score = float(priorities.get(d, 1.0))
            answers[key] = _score(q["criteria"], score)
        elif key == "review_budget":
            answers[key] = _choice(q["criteria"], review_budget, confidence)
        elif key == "budget_factor":
            answers[key] = _choice(q["criteria"], budget_factor, confidence)
        elif key.startswith("reuse_"):
            rid = key[len("reuse_"):]
            answers[key] = {"type": "noul", "noul": 0.91 if rid in reuse else 0.06}
        else:
            raise AssertionError(f"fake does not know question {key!r}")
    if extra_answers:
        answers.update(extra_answers)
    return {
        "model": model,
        "answers": answers,
        "usage": dict(usage) if usage is not None else {"input_tokens": 512, "output_tokens": 48},
    }


def _choice(criteria: Mapping[str, Any], chosen: str, confidence: float) -> Dict[str, Any]:
    options = list(criteria)
    assert chosen in options, (chosen, options)
    n = len(options)
    top = (confidence * (n - 1) + 1) / n if n > 1 else 1.0  # inverse of the docs' confidence formula
    rest = (1.0 - top) / (n - 1) if n > 1 else 0.0
    probabilities = {o: (top if o == chosen else rest) for o in options}
    return {"type": "choice", "choice": chosen, "confidence": confidence, "probabilities": probabilities}


def _score(levels, score: float) -> Dict[str, Any]:
    n = len(levels)
    lo = int(score)
    hi = min(lo + 1, n - 1)
    frac = score - lo
    probabilities = {str(i): 0.0 for i in range(n)}
    probabilities[str(lo)] += 1.0 - frac
    probabilities[str(hi)] += frac
    return {
        "type": "score",
        "score": score,
        "confidence": 1.0 - frac if hi != lo else 1.0,
        "legend": {str(i): lv for i, lv in enumerate(levels)},
        "probabilities": probabilities,
    }


class FakeJevClient:
    """Returns a scripted ClientResult (or computes one from the request
    via `responder(state, questions) -> ClientResult`), and records
    whether/how it was called."""

    def __init__(self, result=None, *, responder=None, raise_exc: Optional[BaseException] = None):
        self._result = result
        self._responder = responder
        self._raise = raise_exc
        self.calls = []

    def system_one(self, state, questions):
        self.calls.append((state, dict(questions)))
        if self._raise is not None:
            raise self._raise
        if self._responder is not None:
            return self._responder(state, questions)
        return self._result


def ok(payload) -> jev_client.ClientResult:
    return jev_client.ClientResult(outcome=jev_client.OK, payload=payload, status=200, request_id="req-fake")


class CountingFactory:
    """client_factory that records how many clients were built and with
    what (never the token value -- only that one was supplied)."""

    def __init__(self, client):
        self.client = client
        self.built = 0
        self.token_was_nonempty = None

    def __call__(self, token):
        self.built += 1
        self.token_was_nonempty = bool(token)
        return self.client
