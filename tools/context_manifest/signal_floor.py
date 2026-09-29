"""Deterministic domain floor from explicit code signals (QUICK / STANDARD / TARGETED).

Item 0 -- the classification that decides `domains` outside DEEP -- is a reasoning pass performed by the reviewing
agent (context-manifest-schema.md section 3, item 0), not by code. This module is a FLOOR under it, never a ceiling:
every rule is a named pair of explicit signals that must BOTH appear in the review scope, and a rule can only ADD a
domain. Nothing here removes a domain, and a scope that matches no rule adds nothing, so this never turns into
"every review loads every play".

It applies in every non-DEEP mode and at every sensitivity, NONE included (user decision, 2026-09-29): when both
signals are present, web-security is a required domain even for a TARGETED change classified NONE.

The one rule today mirrors DEEP's own applicability rule for CSRF (domains.py, `_web_ruled_out`: web-security stays
applicable unless `never_uses_cookie_or_ambient_auth_for_state_change` is positively confirmed):

  CSRF-AMBIENT -> web-security
    (a) the scope establishes an ambient browser credential -- one the browser attaches by itself: cookie
        authentication, a server session cookie, or Windows Integrated Authentication; and
    (b) the scope declares a state-changing endpoint -- a POST / PUT / PATCH / DELETE handler, or a GET handler whose
        route names a state-changing action (delete, remove, update, ...).

Whether a control holds (antiforgery tokens, SameSite, a custom header) is NOT judged here; that is the review's job
under plays/web-security.md's CSRF section. The floor only guarantees that the review looks.

The patterns are a PROXY. They are literal, per stack, and listed below. They can miss an ambient credential or a
state-changing endpoint written some other way, and can fire where no CSRF concern exists; the latter only means one
more play is read. A miss leaves the domain to item 0, exactly as before this module existed.

Known misses (independent review, recorded, not added this round because they would change the pinned fire set):
- Django: its session is recognized, but no Django state-change pattern exists yet, so that half never pairs.
- Other ways to write a state-changing endpoint:
  - `[HttpGet]` with the route on a separate `[Route]`, `[HttpGet(Name=...)]`, `[AcceptVerbs]`;
  - Razor Pages `OnPost...`, `MapMethods`;
  - Express `app.all`, `app.route(...).post`, and routers not named `app`/`router`;
  - FastAPI `Cookie`, a multi-line Flask import of `session`, lower-case Flask `methods`;
  - a route verb glued to another word (`accountDelete`).

Known false fires:
- the signals inside comments;
- read-only routes that start with a verb (`updates`, `enabled-...`);
- an external-login `AddCookie` in a bearer-token API.

A caller that passes `scanner_selection` to produce_manifest() must account for a domain this floor adds. The
built-in validator requires each domain's scanners, so a selection computed from item 0's domains alone makes
production fail loudly instead of silently dropping the domain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet, Mapping, Tuple

_STATE_VERBS = r"(?:delete|remove|update|create|reset|transfer|approve|revoke|disable|enable|logout|signout|deactivate|cancel)"

AMBIENT_CREDENTIAL = (
    # ASP.NET Core
    re.compile(r"\bConfigureApplicationCookie\s*\("),
    re.compile(r"\.AddCookie\s*\("),
    re.compile(r"\bCookieAuthenticationDefaults\b"),
    re.compile(r"\bAdd(?:Default)?Identity\s*<"),
    re.compile(r"\b(?:AddSession|UseSession)\s*\("),
    re.compile(r"\bAddNegotiate\s*\("),
    re.compile(r"\bNegotiateDefaults\b"),
    # Node
    re.compile(r"""require\(\s*['"](?:express-session|cookie-session)['"]\s*\)"""),
    re.compile(r"""from\s+['"](?:express-session|cookie-session)['"]"""),
    # Python
    re.compile(r"\bSESSION_COOKIE_[A-Z_]+\b"),
    re.compile(r"\bfrom\s+flask\s+import\b[^\n]*\bsession\b"),
    re.compile(r"\bdjango\.contrib\.sessions\b"),
)

STATE_CHANGING_ENDPOINT = (
    # ASP.NET Core
    re.compile(r"\[Http(?:Post|Put|Patch|Delete)\b"),
    re.compile(r"\.Map(?:Post|Put|Patch|Delete)\s*\("),
    re.compile(r'\[HttpGet\(\s*"[^"]*\b' + _STATE_VERBS, re.I),
    re.compile(r'\.MapGet\(\s*"[^"]*\b' + _STATE_VERBS, re.I),
    # Node (Express-style routers)
    re.compile(r"\b(?:app|router)\.(?:post|put|patch|delete)\s*\("),
    re.compile(r"""\b(?:app|router)\.get\(\s*['"][^'"]*\b""" + _STATE_VERBS, re.I),
    # Python (Flask-style)
    re.compile(r"""methods\s*=\s*[\[(][^\])]*['"](?:POST|PUT|PATCH|DELETE)['"]"""),
    re.compile(r"@\w+\.(?:post|put|patch|delete)\s*\("),
    re.compile(r"""@\w+\.(?:route|get)\(\s*['"][^'"]*\b""" + _STATE_VERBS, re.I),
)


@dataclass(frozen=True)
class SignalFloor:
    domains: FrozenSet[str]
    reasons: Tuple[str, ...]


def _hits(patterns, scope_texts):
    return sorted({name for name, text in scope_texts.items() for p in patterns if p.search(text)})


def required_domains(scope_texts: Mapping[str, str]) -> SignalFloor:
    """The domains the scope's explicit signals require, with one reason per rule that fired.

    `scope_texts` maps a file name (used only in the reasons) to that file's text. Signals may come from different
    files of the same scope: the credential set-up and the endpoint often live apart."""
    if not isinstance(scope_texts, Mapping):
        raise TypeError("scope_texts must be a mapping of file name -> text")
    for name, text in scope_texts.items():
        if not isinstance(name, str) or not isinstance(text, str):
            raise TypeError("scope_texts must map str -> str")
    domains, reasons = set(), []
    ambient = _hits(AMBIENT_CREDENTIAL, scope_texts)
    state = _hits(STATE_CHANGING_ENDPOINT, scope_texts)
    if ambient and state:
        domains.add("web-security")
        reasons.append(f"CSRF-AMBIENT: ambient browser credential in {ambient}; state-changing endpoint in {state}")
    return SignalFloor(domains=frozenset(domains), reasons=tuple(reasons))
