"""DEEP domain applicability -- context-manifest-schema.md section 3a.

This module is the DEEP-mode domain floor only. It is never used for
TARGETED/QUICK/STANDARD domain selection -- that path is item 0's
diff-scoped reasoning pass (context-manifest-schema.md section 3, item
0), performed by the reviewing agent itself, not by this module. This
module operates on repo-wide architecture facts (the same shape
plays/project-security-baseline.md already produces: Value / Confidence
/ Source / Evidence / Freshness), never on a diff.

Three groups, per the schema doc:

  Group 1 -- unconditionally applicable to DEEP (code-review,
             configuration-security, dependency-security): these are
             DEEP's own mandatory activities, not conditional domains.
  Group 2 -- applicable by default, excluded only by a POSITIVE,
             HIGH-confidence, component-wide confirmation that the
             underlying concern has no context to apply in at all
             (authentication, authorization, secrets-security).
  Group 3 -- applicable unless EVERY item in the domain's authoritative
             play Scope section is positively ruled out (web-security,
             api-security, data-security, file-security). The per-item
             rule table below is this module's own reading of
             context-manifest-schema.md's worked examples (Case 1/1b/2/3)
             projected onto every one of the four plays' current Scope
             items -- it is not a restatement of a table that lives
             anywhere else; the plays' Scope sections remain the sole
             authoritative source of WHICH items exist (see
             scope_coverage.py, which parses them live and fails if this
             table's item labels drift from them).

Insufficient evidence (UNKNOWN confidence, or a source not in
SOURCE_POSITIVE) is never sufficient to rule an item or a Group 2 domain
out -- the default is always "applicable" (fail open toward more
scrutiny, never toward less).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping, Optional, Sequence

CONFIDENCE_LEVELS = ("UNKNOWN", "LOW", "MEDIUM", "HIGH")
SOURCE_POSITIVE = frozenset({"USER_CONFIRMED", "CODE_EVIDENCE", "CONFIG_EVIDENCE"})

ALL_DOMAINS = (
    "code-review",
    "configuration-security",
    "dependency-security",
    "authentication",
    "authorization",
    "secrets-security",
    "web-security",
    "api-security",
    "data-security",
    "file-security",
)

GROUP_1 = frozenset({"code-review", "configuration-security", "dependency-security"})
GROUP_2 = frozenset({"authentication", "authorization", "secrets-security"})
GROUP_3 = frozenset({"web-security", "api-security", "data-security", "file-security"})

assert GROUP_1 | GROUP_2 | GROUP_3 == frozenset(ALL_DOMAINS)
assert not (GROUP_1 & GROUP_2) and not (GROUP_1 & GROUP_3) and not (GROUP_2 & GROUP_3)


@dataclass(frozen=True)
class Fact:
    """One baseline fact -- same 4 fields as plays/project-security-baseline.md.

    `value` is the raw fact value; for every fact this module reads,
    the relevant question is "is this fact positively, reliably
    confirmed" (see is_positive), never the raw value alone -- a
    UNKNOWN-confidence or INFERRED-source fact never counts as a
    positive confirmation of anything, regardless of what `value` says.
    """

    value: object = None
    confidence: str = "UNKNOWN"
    source: str = "NONE"

    def __post_init__(self) -> None:
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"invalid confidence: {self.confidence!r}")

    def is_positive(self, expected=True) -> bool:
        """True iff this fact HIGH-confidence, positive-source confirms `expected`."""
        return (
            self.confidence == "HIGH"
            and self.source in SOURCE_POSITIVE
            and self.value == expected
        )


UNKNOWN_FACT = Fact()


def get(facts: Mapping[str, Fact], key: str) -> Fact:
    return facts.get(key, UNKNOWN_FACT)


def fact_from_baseline_entry(entry: Optional[Mapping[str, object]]) -> Fact:
    """Convert one raw `.security/baseline.json` `facts.<key>` entry
    (templates/project-security-baseline.md's shape: value/confidence/
    source, plus an optional `status`) into a Fact for compute_deep_domains.

    [CORRECTED, per a round-7 independent review Minor: this was
    previously self-described as "the freshness gate", implying it
    enforces context-manifest-schema.md section 3a's "No baseline, or a
    stale one" requirement end to end. It does not and cannot: this
    function only prevents ONE specific way to get a stale raw baseline
    entry wrong; nothing in this batch's code stops a caller from
    hand-building a Fact instead of routing through this function, or
    from deriving a fact through reasoning this function never sees
    (see skills/security-review/SKILL.md step 1's DEEP branch and
    section 3a's own note for the full, honest scope of what is and
    isn't covered).] It is a safe conversion HELPER, addressing the gap
    Batch 0's tests/validation/ re-execution found (a stale baseline
    fact could silently exclude a Group 2/3 domain current source
    evidence no longer supports) for the one case it actually reaches.

    - Missing `status` is that template's own representation of
      "current" (it is OMITTED, never set to some "CURRENT" sentinel)
      -- parses value/confidence/source normally, still subject to
      Fact.is_positive()'s own HIGH-confidence/positive-source gate
      exactly as before; this function adds no new leniency there.
    - `status == "STALE"` (plays/project-security-baseline.md's
      "Freshness and invalidation" section) always becomes UNKNOWN_FACT,
      regardless of what value/confidence/source the entry still
      carries -- checked BEFORE those fields are ever read, so a future
      edit that reorders this cannot accidentally let a stale
      HIGH-confidence fact through again.
    - Any OTHER non-null `status` is a value this schema does not
      define -- a corrupted or unrecognized baseline record, not a
      fresh one. Fails closed with a ValueError rather than being
      silently read as current.
    - A missing entry (the key absent from `facts`), or one missing
      value/confidence/source, degrades to Fact's own UNKNOWN defaults
      (confidence="UNKNOWN"), which already fails is_positive() -- the
      existing "insufficient evidence never rules an item out" rule,
      not new behavior.

    Loading/parsing `.security/baseline.json` itself -- including
    rejecting an unrecognized top-level `schemaVersion` before any
    entry is even read -- is the calling agent's own responsibility per
    skills/security-review/SKILL.md step 1; this batch adds no file I/O
    layer, and this function's contract starts at "one already-parsed
    entry dict."
    """
    if entry is None:
        return UNKNOWN_FACT
    if not isinstance(entry, Mapping):
        raise TypeError(f"baseline fact entry must be a mapping, got {entry!r}")
    status = entry.get("status")
    if status is not None:
        if status == "STALE":
            return UNKNOWN_FACT
        raise ValueError(f"unrecognized baseline fact status: {status!r}")
    return Fact(
        value=entry.get("value"),
        confidence=entry.get("confidence", "UNKNOWN"),
        source=entry.get("source", "NONE"),
    )


# ---------------------------------------------------------------------------
# Group 2 -- authentication / authorization / secrets-security
# ---------------------------------------------------------------------------
#
# Fact keys (all booleans, `value=True` meaning the described condition
# holds):
#   invoked_only_by_trusted_or_authenticated_caller  -- fact (i) shared by
#       authentication and authorization: this component is invoked ONLY
#       by a trusted local operator, or an already-authenticated/
#       authorized caller whose identity/authorization was established
#       OUTSIDE this component's own scope.
#   no_identity_distinction_code       -- fact (ii) for authentication:
#       no session/login/identity concept anywhere in this component.
#   no_restricted_object_or_operation  -- fact (ii) for authorization:
#       no object/resource/operation anywhere in scope whose access
#       should ever be restricted by identity/role.
#   no_credential_anywhere_in_scope    -- secrets-security's sole
#       condition, independent of invocation context.


def _group2_excluded(
    facts: Mapping[str, Fact], domain: str
) -> bool:
    if domain == "authentication":
        return get(facts, "invoked_only_by_trusted_or_authenticated_caller").is_positive() and get(
            facts, "no_identity_distinction_code"
        ).is_positive()
    if domain == "authorization":
        return get(facts, "invoked_only_by_trusted_or_authenticated_caller").is_positive() and get(
            facts, "no_restricted_object_or_operation"
        ).is_positive()
    if domain == "secrets-security":
        return get(facts, "no_credential_anywhere_in_scope").is_positive()
    raise ValueError(f"not a Group 2 domain: {domain!r}")


# ---------------------------------------------------------------------------
# Group 3 -- web-security / api-security / data-security / file-security
# ---------------------------------------------------------------------------
#
# Each entry: (item label -- MUST match the play's current Scope section
# text exactly, verified live by scope_coverage.py, not copied here as a
# second source of truth for the item LIST) -> a predicate over facts
# returning True iff that specific item is positively ruled out.


def _web_ruled_out(facts: Mapping[str, Fact]):
    no_html = get(facts, "no_html_or_script_ever_rendered").is_positive()
    no_cookie_state_change = get(facts, "never_uses_cookie_or_ambient_auth_for_state_change").is_positive()
    no_page = get(facts, "no_browser_page_produced").is_positive()
    no_browser_script = get(facts, "no_browser_side_script_shipped").is_positive()
    no_redirect = get(facts, "no_user_influenced_redirect_issued").is_positive()
    no_cors = get(facts, "no_cors_headers_or_cross_origin_registration").is_positive()
    return {
        "XSS (reflected, stored, DOM-based)": no_html,
        "CSRF": no_cookie_state_change,
        "Clickjacking": no_page,
        "Unsafe postMessage": no_browser_script,
        "Open redirect": no_redirect,
        "CORS misconfiguration": no_cors,
        "CSP weaknesses": no_html,
        "Unsafe DOM operations": no_browser_script,
    }


def _api_ruled_out(facts: Mapping[str, Fact]):
    # [DISCLOSED, per independent review Minor]: `no_raw_http_request_framing`
    # is about whether THIS component itself parses raw HTTP request
    # framing. A component that is server-rendered with no API surface,
    # but sits behind a reverse proxy/gateway that does its own HTTP
    # parsing, could positively confirm this fact true (it genuinely
    # doesn't parse framing itself) and rule out "Request smuggling
    # indicators" -- an open scope question (is smuggling this
    # component's concern, or the layer in front of it?), not resolved
    # either way here. No baseline producer populates this fact today,
    # so this is a latent question for whoever writes one, not an
    # active behavior yet.
    no_api_surface = get(facts, "no_api_or_outbound_call_surface").is_positive()
    no_http_framing = get(facts, "no_raw_http_request_framing").is_positive()
    no_deserialize_or_xml = get(facts, "no_deserialization_or_xml_parsing").is_positive()
    return {
        "Authentication": no_api_surface,
        "Object authorization": no_api_surface,
        "Function authorization": no_api_surface,
        "Rate limits": no_api_surface,
        "Resource consumption": no_api_surface,
        "Mass assignment": no_api_surface,
        "Sensitive fields": no_api_surface,
        "Pagination / filtering": no_api_surface,
        "External APIs / webhooks": no_api_surface,
        "Error handling": no_api_surface,
        "Versioning": no_api_surface,
        "SSRF": no_api_surface,
        "Insecure deserialization": no_deserialize_or_xml,
        "XXE": no_deserialize_or_xml,
        # [REGRESSION, per a ninth-round independent review finding]:
        # request smuggling depends on whether this component parses raw
        # HTTP request framing at all -- NOT on whether it also exposes
        # a REST/GraphQL/RPC/webhook API surface. A component can be
        # HTTP-facing (a proxy/gateway) with no API semantics at all;
        # folding this into no_api_or_outbound_call_surface would let a
        # non-discriminating fixture (one with an API surface anyway)
        # accidentally rule this item out too, or would let a fixture
        # with NO api surface but WITH raw HTTP framing wrongly rule it
        # out via the wrong fact.
        "Request smuggling indicators": no_http_framing,
    }


def _data_ruled_out(facts: Mapping[str, Fact]):
    # [FIXED, per re-adjudicating a disclosed Minor during Batch 0's
    # tests/validation/ re-execution]: context-manifest-schema.md's own
    # Case 1 premise states fact (e) as a COMPOUND condition -- "it
    # performs no cryptographic operations AND handles no data the
    # baseline's 'Sensitive data' fact would flag" -- not "no
    # cryptographic operations" alone. An earlier version of this
    # function checked only the crypto half, which meant a target with
    # genuinely sensitive data (e.g. PII) but zero crypto footprint
    # (exactly the shape where "sensitive data with no encryption at
    # all" is itself often the finding) would have its five
    # crypto-primitive items wrongly ruled out. [CORRECTED, per a
    # round-6 independent review Nit: this comment previously claimed
    # it "could cause DEEP applicability to miss data-security" as a
    # settled fact -- a round-5 independent reviewer could not
    # construct any counterexample where the OLD logic actually caused
    # an existing Play's expected finding to be missed (the affected
    # items are, in every constructed case, also reachable through a
    # Group 2 domain). The fix is kept regardless: it is schema-aligned
    # (matches Case 1's own compound premise exactly) and strictly
    # conservative (only ever ADDS data-security back in, never removes
    # it) -- not a mere documentation tension, but not a demonstrated
    # missed-finding either.] Fixed by requiring BOTH facts,
    # matching Case 1's own compound premise exactly, with a dedicated
    # isolation regression case for the sensitive-data half specifically
    # (tests/test_domains.py's _ISOLATION_CASES).
    no_crypto = get(facts, "no_cryptographic_operations").is_positive()
    no_sensitive_data = get(facts, "no_sensitive_data_flagged").is_positive()
    no_crypto_and_no_sensitive_data = no_crypto and no_sensitive_data
    no_random_gen = get(facts, "no_security_relevant_random_generation").is_positive()
    no_tls = get(facts, "no_outbound_tls_connections").is_positive()
    return {
        "Hardcoded encryption keys": no_crypto_and_no_sensitive_data,
        "Weak algorithms": no_crypto_and_no_sensitive_data,
        "Static IV": no_crypto_and_no_sensitive_data,
        "Nonce reuse": no_crypto_and_no_sensitive_data,
        "Improper password hashing": no_crypto_and_no_sensitive_data,
        # [REGRESSION, per a ninth-round independent review finding]:
        # deliberately NOT covered by no_crypto alone -- using a
        # non-CSPRNG source is itself direct evidence a cryptographic
        # operation is happening incorrectly, which a check keyed only
        # on "no cryptographic operations present" would misread as
        # evidence the item doesn't apply. This item is ruled out ONLY
        # by "no security-relevant random value is ever generated here
        # at all", never by "crypto operations are absent" or "the
        # generation is presumably fine".
        "Insecure random generation": no_random_gen,
        "Certificate validation bypass": no_tls,
    }


def _file_ruled_out(facts: Mapping[str, Fact]):
    no_attacker_input = get(facts, "no_attacker_influenced_paths_or_content").is_positive()
    # [REGRESSION, per a ninth-round independent review finding]: kept as
    # TWO independent facts, not one. A temp file in a private,
    # non-shared directory that is still left world-readable or
    # undeleted after use is the specific sub-case a condition keyed on
    # "shared or world-writable location" alone would have missed --
    # BOTH facts must independently hold to rule this item out.
    temp_path_unpredictable = get(facts, "temp_files_none_or_path_unpredictable").is_positive()
    temp_safely_handled = get(facts, "temp_files_none_or_private_and_cleaned_up").is_positive()
    no_temp_file_risk = temp_path_unpredictable and temp_safely_handled
    no_storage_location_risk = get(facts, "storage_location_not_attacker_influenced").is_positive()
    no_archive_ops = get(facts, "no_archive_extraction_or_creation").is_positive()
    return {
        "Uploads": no_attacker_input,
        "Downloads": no_attacker_input,
        "ZIP extraction": no_archive_ops,
        "Archive creation": no_archive_ops,
        "Temporary files": no_temp_file_risk,
        "File deletion": no_attacker_input,
        "Directory traversal": no_attacker_input,
        "Filename generation": no_attacker_input,
        "Extension validation": no_attacker_input,
        "MIME validation": no_attacker_input,
        "Storage location": no_storage_location_risk,
        "Static serving": no_attacker_input,
    }


_GROUP_3_ITEM_RULES = {
    "web-security": _web_ruled_out,
    "api-security": _api_ruled_out,
    "data-security": _data_ruled_out,
    "file-security": _file_ruled_out,
}


@dataclass(frozen=True)
class DomainResult:
    """Full reasoning trace for one DEEP applicability computation.

    `domains` is the only field that would ever reach an actual Context
    Manifest (a flat array, per context-manifest-schema.md section 1 --
    no per-item attribution). `group3_item_status` is exposed
    separately so tests (and, later, a validator's failedChecks message)
    can point at exactly which item kept a domain in or let it out,
    without that detail ever being written into a real manifest.
    """

    domains: FrozenSet[str]
    group3_item_status: Mapping[str, Mapping[str, bool]] = field(default_factory=dict)


def compute_deep_domains(facts: Mapping[str, Fact]) -> DomainResult:
    domains = set(GROUP_1)

    for domain in GROUP_2:
        if not _group2_excluded(facts, domain):
            domains.add(domain)

    group3_item_status: dict = {}
    for domain, rule_fn in _GROUP_3_ITEM_RULES.items():
        ruled_out_by_item = rule_fn(facts)
        group3_item_status[domain] = ruled_out_by_item
        if not all(ruled_out_by_item.values()):
            domains.add(domain)

    # [OPEN, disclosed limitation, per context-manifest-schema.md section
    # 3a]: this algorithm cannot see how the target repository is invoked
    # from OUTSIDE itself. When `externally_invoked_trusted_input_only`
    # is not POSITIVELY confirmed (UNKNOWN, or confirmed false), that is
    # an UNKNOWN, not a confirmed-safe fact -- file-security stays
    # applicable regardless of what the per-item table above concluded,
    # since an unconfirmed external caller could still supply attacker-
    # influenced input this repository's own architecture facts cannot
    # see. This is independent of, and in addition to, the per-item
    # rule table -- it can only ADD file-security back in, never
    # remove it.
    trusted_input_only = get(facts, "externally_invoked_trusted_input_only").is_positive()
    if not trusted_input_only:
        domains.add("file-security")

    return DomainResult(domains=frozenset(domains), group3_item_status=group3_item_status)


def group3_scope_items(domain: str) -> Sequence[str]:
    """The item labels this module's rule table declares for `domain`.

    Used only by scope_coverage.py to detect this table drifting from
    the live-parsed play Scope section -- this function is NOT the
    authoritative item list (the play's own Scope section is); it is
    what this module currently assumes that list is, so a mismatch is
    exactly the drift criterion 7 exists to catch.
    """
    return tuple(_GROUP_3_ITEM_RULES[domain](_EMPTY_FACTS).keys())


_EMPTY_FACTS: Mapping[str, Fact] = {}
