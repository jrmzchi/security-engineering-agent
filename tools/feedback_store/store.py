"""`.security/feedback.json` file-level container, I/O, and atomic
writes.

Deliberately a SEPARATE file from `.security/baseline.json`/
`.security/attack-surface.json` (per explicit instruction) -- this
isolates the new schema, so a bug or a corrupted write here cannot
touch either of those two already-shipped V3 formats.

Corruption/degradation policy, stated once here rather than
per-call-site: a file that does not exist means "no intelligence to
reuse yet," not an error -- the review proceeds with a fresh, empty
store. A file that exists but cannot be fully trusted (invalid JSON,
an unsupported `schemaVersion`, or even ONE record failing schema
validation) is treated as WHOLLY unusable for reuse this round -- this
module never partially trusts the records that happen to still parse.
Either way, `load()` never raises for "no usable intelligence" -- it
returns a `LoadResult` the caller inspects, so a missing or corrupted
store degrades Evidence Reuse for this run, never blocks or crashes the
security review itself.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Mapping, Optional

from . import schema

WRITER_VERSION = "1.0.0"


class StoreError(ValueError):
    """A store-level operation failed for a reason the caller must
    handle explicitly (never silently swallowed)."""


class DuplicateRecordIdError(StoreError):
    """A record ID collision -- appending must fail explicitly rather
    than silently overwriting a different record under the same ID."""


class ConcurrentModificationError(StoreError):
    """The on-disk file changed since this `FeedbackStore` was loaded
    -- writing now would silently discard whichever change happened in
    between. `[CORRECTED, per a round-1 independent review Major: this
    previously claimed only detection, "it cannot prevent a lost
    update" -- the reviewer reproduced real silent lost updates under
    genuinely simultaneous writers, since the hash-check-then-replace
    sequence alone had a real check-then-act window]` `write()` now
    holds `_acquire_lock()`'s exclusive lockfile around the whole
    check-hash -> serialize -> replace sequence, which SERIALIZES
    concurrent writers rather than merely detecting a race afterward --
    this error now fires when a writer's own snapshot (the hash it
    loaded) is provably stale relative to what's on disk right now, a
    real precondition failure, not a race outcome that depends on
    timing.
    """


class UnsafeStorePathError(StoreError):
    """The `.security/feedback.json` path resolves (via a symlink or
    reparse point) to a location outside the repository root -- refused
    rather than followed."""


class LockTimeoutError(StoreError):
    """Could not acquire the write lock within the timeout -- another
    writer appears to be active. Fails closed: the write is refused,
    not attempted unprotected."""


LOCK_TIMEOUT_SECONDS = 5.0
LOCK_POLL_INTERVAL_SECONDS = 0.05
# [ADDED, per a round-2 independent review Minor]: a writer that
# crashes (killed, powered off) between acquiring the lock and
# releasing it leaves the lockfile behind forever -- every future
# write would otherwise fail closed indefinitely with a misleading
# "another writer appears to be active" message. A lock older than
# this is treated as abandoned and removed automatically. This is a
# disclosed heuristic (no PID/liveness check, just age), not a
# guarantee -- it trades a small window where a very slow legitimate
# writer could theoretically be preempted for the much more likely
# failure mode (a dead writer blocking every future write forever).
LOCK_STALE_SECONDS = 30.0


def _lock_path_for(path: str) -> str:
    return path + ".lock"


def _breaker_path_for(lock_path: str) -> str:
    return lock_path + ".break"


def _break_stale_lock(lock_path: str) -> Optional[bool]:
    """[ADDED, V4 release: closes the stale-lock double-acquisition
    TOCTOU deferred since Round 3.] Removing a stale lock used to be a
    bare `os.remove()` after an age check made outside any lock: two
    waiters that both saw the SAME stale lock could interleave so that
    the first removed it and acquired a fresh lock, and the second --
    still acting on its earlier stale observation -- then removed that
    fresh lock and acquired too. Both then held the lock and one update
    could be silently lost.

    Now the removal happens only while holding an exclusive breaker
    marker (`<lock>.break`, `O_CREAT | O_EXCL`), and the lock's age is
    RE-CHECKED under that marker: a lock that has since been re-created
    (fresh mtime) is left alone. Every other writer only ever creates
    the lock with `O_EXCL`, so between the re-check and the removal no
    one but the marker holder can replace the stale file -- provided
    the stale lock's owner is really gone. An owner that is only
    paused for longer than LOCK_STALE_SECONDS can still release it in
    that window, and a third writer can then create a lock that this
    removal deletes: that is the disclosed "a lock older than the
    threshold is treated as abandoned" heuristic, not a waiter race.

    Returns True if the stale lock was removed, False if it is gone or
    no longer stale (retry the ordinary acquisition), None if it could
    not be removed or another process holds the marker (contention).
    A marker left behind by a crash is never broken automatically: it
    only disables the automatic stale-lock removal, so acquisition then
    times out and fails closed with a manual-removal message.
    """
    breaker = _breaker_path_for(lock_path)
    try:
        fd = os.open(breaker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except OSError:
        return None
    try:
        try:
            age = time.time() - os.path.getmtime(lock_path)
        except OSError:
            return False
        if age <= LOCK_STALE_SECONDS:
            return False
        try:
            os.remove(lock_path)
            return True
        except OSError:
            return None
    finally:
        _release_lock(breaker)


def _acquire_lock(path: str, *, timeout: float = LOCK_TIMEOUT_SECONDS) -> str:
    """[ADDED, per a round-1 independent review Major]: `write()`'s
    original hash-check-then-`os.replace()` sequence had a real
    check-then-act (TOCTOU) window -- two writers that both read the
    same on-disk hash before either one replaced the file could both
    pass the hash check and both successfully write, with one's update
    silently lost (independently reproduced by the reviewer: ~80% of
    truly simultaneous writes in a tight race). An exclusive-create
    lockfile (`O_CREAT | O_EXCL`, atomic on every platform this
    package targets) serializes the whole
    check-hash -> serialize -> replace sequence, closing the window
    instead of merely detecting it after the fact. Retries with a short
    poll until `timeout`, then fails closed (refuses the write) rather
    than proceeding unprotected.
    """
    lock_path = _lock_path_for(path)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return lock_path
        # [CORRECTED, per a Round 3 independent review Minor]: on
        # Windows, `os.open(..., O_CREAT|O_EXCL)` can raise
        # `PermissionError` (WinError 5) instead of `FileExistsError`
        # when another process just deleted this same lockfile and it
        # is still in a brief "delete pending" state (independently
        # reproduced by the reviewer under an 8-thread concurrent
        # load/write stress test: 2 occurrences out of 320 attempts) --
        # the same underlying Windows sharing-violation quirk
        # `_replace_with_retry` already retries around for `os.replace`.
        # Treated identically to `FileExistsError` here: contention, not
        # a real failure, so it goes through the same bounded
        # stale-check/retry/timeout logic below rather than escaping
        # uncaught to a caller that may only be prepared to catch
        # `StoreError`.
        except (FileExistsError, PermissionError) as exc:
            lock_exists = os.path.exists(lock_path)
            try:
                age = time.time() - os.path.getmtime(lock_path)
            except OSError:
                age = 0.0  # lock disappeared between the failed open and stat -- just retry
            # A stale lock is removed only through `_break_stale_lock()`,
            # which re-checks the age under its own exclusive marker; a
            # False result (gone, or re-created fresh by another writer
            # since the stat above) falls through to ordinary contention.
            broken = _break_stale_lock(lock_path) if age > LOCK_STALE_SECONDS else False
            if broken is not False:
                removed = broken is True
                # [CORRECTED, per a Round 3 independent review Minor]:
                # this branch used to `continue` unconditionally, never
                # checking `deadline` -- a stale lock that could not be
                # removed (permissions, or another process recreating
                # it) looped forever, contradicting the documented
                # "fails closed... rather than proceeding unprotected"
                # contract. [CORRECTED again, per a Round 4 Nit]: it
                # also spun with no sleep (~800 iterations in 0.3s), and
                # the comment claimed the retry "does not count against
                # timeout", which stopped being true once the deadline
                # check was added. Now: a SUCCESSFUL removal retries
                # immediately (the lock really is gone); a FAILED one
                # checks the deadline and then polls at the normal
                # interval like any other contention.
                if removed:
                    if time.monotonic() >= deadline:
                        # [ADDED, per explicit instruction (truncated
                        # section 七 of the Round 5 close-out, confirmed
                        # after Round 6; Round 5 Nit)]: the deadline is
                        # checked on the SUCCESSFUL-removal retry too -- a
                        # stale lock recreated with an old mtime on every
                        # iteration used to loop past the deadline forever,
                        # since only the failed-removal branch checked it.
                        raise LockTimeoutError(
                            f"could not acquire write lock {lock_path!r} within {timeout}s -- a stale lock "
                            "kept reappearing after removal. If you are sure no writer is actually running, "
                            "stop whatever is recreating it and retry."
                        )
                    continue
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        f"could not acquire write lock {lock_path!r} within {timeout}s -- a stale lock "
                        f"(older than {LOCK_STALE_SECONDS}s) is present but could not be removed "
                        f"({exc.__class__.__name__}; or its breaker marker {_breaker_path_for(lock_path)!r} "
                        "is held or was left behind). If you are sure no writer is actually running, "
                        "delete these files by hand."
                    )
                time.sleep(LOCK_POLL_INTERVAL_SECONDS)
                continue
            if time.monotonic() >= deadline:
                if not lock_exists:
                    # [CORRECTED, per a Round 4 Nit]: reaching the
                    # deadline because os.open kept raising
                    # PermissionError while NO lockfile exists is a
                    # permissions/IO problem on the directory, not
                    # contention -- the old message blamed a phantom
                    # "other writer" and told the user to delete a file
                    # that was not there.
                    raise LockTimeoutError(
                        f"could not create write lock {lock_path!r} within {timeout}s: no lock file exists, "
                        f"but creating one kept failing with {exc.__class__.__name__} ({exc}). Check the "
                        "directory's permissions; this is not another writer holding the lock."
                    )
                raise LockTimeoutError(
                    f"could not acquire write lock {lock_path!r} within {timeout}s -- another writer "
                    "appears to be active. If you are sure no writer is actually running, this lock "
                    f"file is a leftover from a crashed process -- it is removed automatically once "
                    f"it is older than {LOCK_STALE_SECONDS}s, or you may delete it by hand."
                )
            time.sleep(LOCK_POLL_INTERVAL_SECONDS)


def _release_lock(lock_path: str) -> None:
    try:
        os.remove(lock_path)
    except OSError:
        pass


@dataclass
class LoadResult:
    store: Optional[dict]
    ok: bool
    degraded: bool
    reason: Optional[str] = None
    on_disk_hash: Optional[str] = None
    # [ADDED, per explicit instruction for the schema-version-2
    # migration]: True iff this store's own top-level `schemaVersion`
    # tag is `schema.LEGACY_SCHEMA_VERSION` (1) -- i.e. the WHOLE store
    # was last written before this redesign. identity.py's own
    # per-record legacy-schema guard is the actual enforcement point
    # (it refuses ANY record missing `qualifiedSymbol` regardless of
    # this flag or the store's tag), but callers should still surface
    # `legacy=True` in the review's own notes rather than silently
    # proceeding as if this were an ordinary, fully-reusable store.
    #
    # [CORRECTED, per the qualifiedSymbol redesign's own re-verification
    # requirement]: this field does NOT cover a store whose top-level
    # tag is 2 but that still contains one or more individual
    # legacy-shaped records (the exact "mixed-version store" scenario --
    # see `has_legacy_records` below, which does).
    legacy: bool = False
    # [ADDED, per explicit instruction: "a mixed-version store (some
    # records revalidated to v2, others still legacy) remains safe"]:
    # True iff ANY rejection record actually loaded is legacy-shaped
    # (missing `qualifiedSymbol` on some hop), REGARDLESS of what the
    # store's own top-level `schemaVersion` claims. This exists because
    # `write()` always stamps the top-level tag with the CURRENT
    # `schema.SCHEMA_VERSION` (the writer itself is version-2-capable,
    # which is a true statement about the FILE FORMAT) -- so a store
    # that started as legacy, then had one write pass over it for any
    # reason, ends up tagged "2" at the top level while still holding
    # untouched legacy records inside. `has_legacy_records` is computed
    # fresh from the actual loaded records every time, never from the
    # tag, so it can never go stale the way relying on the tag alone
    # did (see the round of testing that found and fixed this).
    has_legacy_records: bool = False


def empty_store() -> dict:
    return {
        "schemaVersion": schema.SCHEMA_VERSION,
        "updated": None,
        "gitCommit": None,
        "writerVersion": WRITER_VERSION,
        "rejectionRecords": {},
        "missRecords": {},
    }


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_safe(path: str, repo_root: str) -> str:
    """[CORRECTED, per a round-1 independent review Minor: the previous
    version only checked containment when `path` itself already
    existed, on the theory that "a not-yet-created path is safe by
    definition." That reasoning missed that `os.path.realpath` resolves
    symlinks/junctions in any EXISTING ancestor directory even when the
    leaf file does not exist yet -- a `.security` directory that is
    itself a junction/symlink pointing outside the repo, with no
    `feedback.json` inside it yet, passed this check uncaught and
    `write()` would then create the file at the redirected location.
    The containment check now always runs, regardless of whether the
    leaf file exists.]
    """
    real_repo_root = os.path.realpath(repo_root)
    real_path = os.path.realpath(path)
    try:
        contained = os.path.commonpath([real_repo_root, real_path]) == real_repo_root
    except ValueError:
        # Different drives on Windows, or otherwise incomparable --
        # cannot be "inside" the repo root either way. Fail closed.
        contained = False
    if not contained:
        raise UnsafeStorePathError(
            f"{path!r} resolves outside the repository root {repo_root!r} "
            "(via a symlink or reparse point in an ancestor directory) -- refusing to follow it"
        )
    return real_path


def load(path: str, *, repo_root: str) -> LoadResult:
    # [CORRECTED, per a round-2 independent review Minor: the previous
    # order returned "no file, empty store" before ever calling
    # `_resolve_safe` -- a `.security` directory that is ITSELF a
    # symlink/junction pointing outside the repo, with no
    # `feedback.json` inside it yet, was silently treated as "nothing
    # recorded" instead of being flagged, unlike `write()`, which
    # always checks first. The safety check now always runs, even when
    # the file does not exist.]
    _resolve_safe(path, repo_root)

    if not os.path.exists(path):
        return LoadResult(store=empty_store(), ok=True, degraded=False, reason=None, on_disk_hash=None)

    with open(path, "rb") as f:
        raw_bytes = f.read()
    on_disk_hash = _hash_bytes(raw_bytes)

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return LoadResult(store=None, ok=False, degraded=True, reason=f"not valid UTF-8: {exc}", on_disk_hash=on_disk_hash)

    # Three parse-failure classes, most specific first. `JSONDecodeError`
    # is a `ValueError` subclass, so its branch must precede the plain
    # `ValueError` one or it would be unreachable. All three are "an
    # unreadable store" -- never an exception out of load().
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return LoadResult(store=None, ok=False, degraded=True, reason=f"invalid JSON: {exc}", on_disk_hash=on_disk_hash)
    except RecursionError:
        # [ADDED, per a Round 4 independent review disclosure]: a
        # pathologically deep nested document recurses past the
        # interpreter limit -- previously escaped as a raw RecursionError.
        return LoadResult(store=None, ok=False, degraded=True, reason="JSON nested too deeply to parse safely", on_disk_hash=on_disk_hash)
    except ValueError as exc:
        # [ADDED, per explicit instruction closing a Round 5 independent
        # review Minor]: Python 3.11+ refuses to convert an integer
        # literal longer than `sys.get_int_max_str_digits()` (default
        # 4300 digits) and raises a plain `ValueError`, NOT a
        # `JSONDecodeError` -- so a store containing one such literal
        # used to escape load() as an exception. Any other ValueError
        # the parser may raise for the same "well-formed but not safely
        # representable" reasons lands here too; the message carries the
        # parser's own diagnostic rather than a hard-coded special case.
        return LoadResult(store=None, ok=False, degraded=True, reason=f"JSON could not be parsed safely: {exc}", on_disk_hash=on_disk_hash)

    if not isinstance(data, dict):
        return LoadResult(store=None, ok=False, degraded=True, reason="top-level JSON value is not an object", on_disk_hash=on_disk_hash)

    version = data.get("schemaVersion")
    # [CORRECTED, per a round-1 independent review Minor: `version not
    # in (1,)` uses `==`, and in Python `True == 1` and `1.0 == 1` --
    # a hand-edited `"schemaVersion": true` or `1.0` was silently
    # accepted as version 1. Require the exact type AND value.]
    # [EXTENDED, per explicit instruction for the schema-version-2
    # migration]: `schema.LEGACY_SCHEMA_VERSION` (1) is now recognized
    # too -- not "unsupported," but AUDIT-ONLY (`legacy=True` below;
    # see `schema.validate_legacy_rejection_record_for_audit()`'s own
    # docstring for why this is deliberately lenient and never upgrades
    # a record to satisfy version-2's stricter identity rules).
    is_legacy = type(version) is int and version == schema.LEGACY_SCHEMA_VERSION
    if type(version) is not int or (version != schema.SCHEMA_VERSION and not is_legacy):
        return LoadResult(
            store=None, ok=False, degraded=True,
            reason=(
                f"unsupported schemaVersion {version!r} (this reader supports "
                f"{schema.SCHEMA_VERSION!r}, or {schema.LEGACY_SCHEMA_VERSION!r} as audit-only legacy) "
                "-- not guessing at a parse"
            ),
            on_disk_hash=on_disk_hash,
        )

    rejection_records = data.get("rejectionRecords", {})
    miss_records = data.get("missRecords", {})
    if not isinstance(rejection_records, dict) or not isinstance(miss_records, dict):
        return LoadResult(store=None, ok=False, degraded=True, reason="rejectionRecords/missRecords must be objects", on_disk_hash=on_disk_hash)

    # "不得部分相信可解析的片段" -- ANY single record failing
    # validation degrades the WHOLE store, not just that record.
    # [CORRECTED, per a round-1 independent review Minor: a non-mapping
    # record entry (e.g. a bare string) made `record.get(...)` raise
    # AttributeError, which this `except` clause did not catch --
    # violating this module's own "load() never raises" guarantee.
    # Guard the shape before indexing, and widen the catch to every
    # exception type a malformed record could plausibly raise.]
    #
    # [CORRECTED, per the qualifiedSymbol redesign's own re-verification
    # requirement]: which validator applies is now decided PER RECORD,
    # from that record's own shape -- NOT from the store's single
    # top-level `schemaVersion` tag. Reproduced concretely: `write()`
    # always re-stamps the top-level tag to the CURRENT
    # `schema.SCHEMA_VERSION` on every save (the writer itself is
    # version-2-capable; that part is true). A store that started out
    # legacy (tag == 1, every record audit-only) that then had even one
    # ordinary write pass over it -- for any reason, e.g. appending an
    # unrelated fresh v2 record -- came back tagged "2" while its
    # original legacy records were untouched. The OLD single-validator-
    # for-the-whole-store logic then applied the STRICT v2 validator to
    # those still-legacy records and degraded the ENTIRE store on the
    # very next load -- silently destroying both the legacy records AND
    # any genuinely fresh v2 ones alongside them. Deciding per record,
    # from whether THAT record's own reachabilityPath actually has
    # `qualifiedSymbol` on every hop, is immune to the tag drifting out
    # of sync with its contents this way, and is exactly what "a mixed-
    # version store... remains safe" requires.
    # [CORRECTED, per a Round 3 independent review Major]: this used to
    # read `if is_legacy or _record_is_legacy_shaped(record):` -- the
    # `is_legacy or` half meant a store whose TOP-LEVEL tag is 1 forced
    # the lenient audit-only validator onto EVERY record in it, even one
    # that already has a real `qualifiedSymbol` on every hop (fully
    # v2-shaped). That record then skipped every field the strict
    # validator would have required (`dependencies`, `lastValidation`,
    # a real `status` enum, `reuseCount` bounds...), and since it now
    # LOOKS v2-shaped, `identity.py`'s own per-record legacy guard let
    # it through too -- reproduced directly: a hand-built record with
    # every hop's `qualifiedSymbol` set (including the degenerate case
    # of `None`, matched by a candidate that omits the key entirely) in
    # a `schemaVersion: 1` store loaded successfully and was then judged
    # REUSABLE despite its own dependencies having changed and its own
    # `status` being `"stale"` (wrong case, so silently ignored) --
    # completely defeating this store's central safety property. Which
    # validator applies is decided PURELY from the record's own shape
    # now, never from the store's top-level tag -- the tag remains
    # informational only (see `LoadResult.legacy`'s own docstring).
    try:
        has_legacy_records = _validate_all_records(rejection_records, miss_records)
    except (schema.SchemaError, AttributeError, TypeError, KeyError, IndexError, RecursionError) as exc:
        return LoadResult(store=None, ok=False, degraded=True, reason=f"record failed validation: {exc}", on_disk_hash=on_disk_hash)

    return LoadResult(
        store=data, ok=True, degraded=False, reason=None, on_disk_hash=on_disk_hash,
        legacy=is_legacy, has_legacy_records=has_legacy_records,
    )


def _validate_all_records(rejection_records: Mapping, miss_records: Mapping) -> bool:
    """The store-level trust boundary shared by `load()` AND `write()`:
    every rejection record is either legacy-shaped (`qualifiedSymbol`
    key genuinely absent on some hop -- `schema.is_legacy_shaped`, the
    ONE definition) and checked with the lenient audit-only validator,
    or it is a CURRENT record and must pass `schema.validate_rejection_record`
    in full. Every miss record must pass `schema.validate_miss_record`.
    Raises `schema.SchemaError` on the first problem. Returns whether
    any legacy record was seen.

    [CORRECTED, per explicit instruction closing Round 4 independent
    review findings]: (1) the Round 3 version of the legacy check here
    also reclassified a present-but-INVALID `qualifiedSymbol` as
    "legacy", routing a corrupted current record to the lenient
    validator and loading it successfully -- a regression against this
    module's own "one bad record degrades the whole store" policy; the
    legacy test is key-absence only now, so a broken current record
    fails strictly as it should. (2) `write()` never validated at all,
    so a store mutated in memory through the (then-unvalidated)
    append/replace APIs could be persisted with records `load()` would
    refuse -- the same function now guards both directions.
    """
    has_legacy_records = False
    for record_id, record in rejection_records.items():
        if not isinstance(record, Mapping):
            raise schema.SchemaError(f"rejectionRecords[{record_id!r}] must be an object, got {record!r}")
        if record.get("recordId") != record_id:
            raise schema.SchemaError(f"rejectionRecords key {record_id!r} does not match recordId {record.get('recordId')!r}")
        if schema.is_legacy_shaped(record):
            schema.validate_legacy_rejection_record_for_audit(record)
            has_legacy_records = True
        else:
            schema.validate_rejection_record(record)
    for record_id, record in miss_records.items():
        if not isinstance(record, Mapping):
            raise schema.SchemaError(f"missRecords[{record_id!r}] must be an object, got {record!r}")
        if record.get("recordId") != record_id:
            raise schema.SchemaError(f"missRecords key {record_id!r} does not match recordId {record.get('recordId')!r}")
        schema.validate_miss_record(record)
    # [ADDED, V4 release]: append already refuses an id that exists in
    # the other collection; load/write did not, so a hand-edited or
    # merged file could carry one id in both, and the audit trail (which
    # names a reused record by id alone) would be ambiguous. Refused here,
    # so load() degrades the whole store (every candidate gets full
    # validation) and write() refuses to persist it.
    shared = sorted(set(rejection_records) & set(miss_records))
    if shared:
        raise schema.SchemaError(f"record id(s) {shared!r} appear in both rejectionRecords and missRecords")
    return has_legacy_records


def append_rejection_record(store: dict, record: dict) -> None:
    """[STRENGTHENED, per explicit instruction closing a Round 4
    independent review finding promoted to Major]: only a CURRENT
    record that passes `schema.validate_rejection_record` may be
    appended -- this API used to accept any dict, which meant an
    unvalidated in-memory record could reach `eligibility.decide_reuse`
    (and be persisted by `write()`) without ever crossing `load()`'s
    validation. A legacy-shaped record can only ever ENTER a store by
    being loaded from an old file, never appended. Raises
    `schema.SchemaError` -- a caller-side bug, loud."""
    if schema.is_legacy_shaped(record):
        raise schema.SchemaError("cannot append a legacy-shaped (no qualifiedSymbol) record -- re-derive it as a current record")
    schema.validate_rejection_record(record)
    record_id = record["recordId"]
    if record_id in store["rejectionRecords"]:
        raise DuplicateRecordIdError(f"rejection record id {record_id!r} already exists")
    if record_id in store["missRecords"]:
        raise DuplicateRecordIdError(f"record id {record_id!r} already exists as a miss record")
    # Commit a deep copy, not the caller's own object: validation above
    # is only meaningful if the caller cannot mutate what the store
    # holds afterwards through the reference it kept (Round 5 mutator
    # discipline: validated content is what gets committed, exactly).
    store["rejectionRecords"][record_id] = copy.deepcopy(record)


def append_miss_record(store: dict, record: dict) -> None:
    schema.validate_miss_record(record)
    record_id = record["recordId"]
    if record_id in store["missRecords"]:
        raise DuplicateRecordIdError(f"miss record id {record_id!r} already exists")
    if record_id in store["rejectionRecords"]:
        raise DuplicateRecordIdError(f"record id {record_id!r} already exists as a rejection record")
    store["missRecords"][record_id] = copy.deepcopy(record)


def replace_rejection_record(store: dict, record_id: str, new_record: dict) -> None:
    """Intentional update path (Selective Revalidation) -- distinct
    from `append_rejection_record`'s collision-refusing behavior, so an
    accidental duplicate ID can never silently take this path instead.
    Applies the same strict validation as `append_rejection_record`
    (Round 4 trust-boundary fix; see that function).
    """
    if schema.is_legacy_shaped(new_record):
        raise schema.SchemaError("cannot install a legacy-shaped (no qualifiedSymbol) record as a replacement -- re-derive it as a current record")
    schema.validate_rejection_record(new_record)
    if record_id not in store["rejectionRecords"]:
        raise StoreError(f"cannot replace rejection record {record_id!r}: it does not exist")
    if new_record["recordId"] != record_id:
        raise StoreError(f"replacement record's recordId {new_record['recordId']!r} does not match {record_id!r}")
    # The record being replaced MAY be legacy-shaped: a full
    # re-derivation producing a fresh current record is exactly the one
    # legitimate way a legacy occurrence becomes reusable again. Only
    # the NEW record is held to the strict validator.
    store["rejectionRecords"][record_id] = copy.deepcopy(new_record)


def _mutate_rejection_record_atomically(store: dict, record_id: str, mutate) -> dict:
    """[ADDED, per explicit instruction closing Round 5 independent
    review findings]: the one way any in-place mutator changes a stored
    rejection record -- copy -> mutate -> validate -> commit. The
    caller's `mutate(candidate)` runs on a DEEP COPY; the applicable
    validator runs on that copy (strict for a current record, the
    lenient audit-only one for a legacy record -- a legacy record must
    never be sent through the strict validator, and stays non-reusable
    regardless); only if validation passes is the stored record
    replaced. On failure the store is unchanged, byte for byte -- the
    Round 5 reviewer showed `mark_stale(reason="")` used to write
    `status`/`staleReason` into the live record first and only fail
    later inside `write()`, taking every other pending change in that
    same write down with it.
    Returns the committed record.
    """
    record = store["rejectionRecords"].get(record_id)
    if record is None:
        raise StoreError(f"no such rejection record {record_id!r}")
    candidate = copy.deepcopy(record)
    mutate(candidate)
    if schema.is_legacy_shaped(candidate):
        schema.validate_legacy_rejection_record_for_audit(candidate)
    else:
        schema.validate_rejection_record(candidate)
    store["rejectionRecords"][record_id] = candidate
    return candidate


def increment_reuse_count(store: dict, record_id: str) -> int:
    """[ADDED, per a round-1 independent review Major]: the previous
    version of this batch built `eligibility.decide_reuse()`'s
    reuseCount-threshold check (schema section 5.1's own "force one
    full re-derivation after N reuses" safety valve) but never
    provided any way to actually increment the counter -- nothing in
    this package called it, so the threshold could never be reached
    however many times a record was actually reused. Call this once,
    after a REUSABLE decision was actually acted on (the workflow chose
    not to re-invoke skills/security-validate), never speculatively.
    Returns the new count.

    Resetting to 0 needs no separate function: `mark_revalidated()` /
    `replace_rejection_record()` always install a freshly-built record
    (via `schema.new_rejection_record()`, whose own `reuse_count`
    defaults to 0) rather than mutating the old one in place -- an
    actual full re-derivation naturally starts the counter over,
    exactly the semantics section 5.1 asks for. A caller that instead
    hand-copies the old record's `reuseCount` into a "fresh" one would
    be defeating the safety valve regardless of what this module does,
    the same way it could defeat any other field in this schema.
    """
    record = store["rejectionRecords"].get(record_id)
    if record is None:
        raise StoreError(f"cannot increment reuseCount for {record_id!r}: no such rejection record")
    if schema.is_legacy_shaped(record):
        # A legacy record can never have been reused, so a reuse-count
        # increment on one is a caller-side bug, not a legitimate event.
        raise StoreError(f"cannot increment reuseCount for legacy (audit-only) record {record_id!r}")

    def _mutate(candidate):
        # [CORRECTED, per explicit instruction closing Round 5 findings]:
        # no `.get(..., 0)` -- a missing or wrong-typed reuseCount is a
        # broken record, never "zero so far". `bool` is an `int`
        # subclass in Python (`True + 1 == 2` would pass a plain
        # isinstance check), so it is rejected explicitly.
        if "reuseCount" not in candidate:
            raise schema.SchemaError(f"record {record_id!r} has no reuseCount field -- it cannot be incremented, it must be re-derived")
        current = candidate["reuseCount"]
        if not isinstance(current, int) or isinstance(current, bool) or current < 0:
            raise schema.SchemaError(f"record {record_id!r} has an invalid reuseCount {current!r}")
        candidate["reuseCount"] = current + 1

    committed = _mutate_rejection_record_atomically(store, record_id, _mutate)
    return committed["reuseCount"]


def mark_stale(store: dict, record_id: str, *, reason: str) -> None:
    """[CORRECTED, per explicit instruction closing a Round 5
    independent review Minor]: `reason` must be a non-empty string and
    must pass the secret heuristic, checked BEFORE anything is touched;
    the status change is then applied copy -> validate -> commit, so a
    rejected reason leaves neither `status` nor `staleReason` behind.
    """
    if not isinstance(reason, str) or not reason.strip():
        raise schema.SchemaError(f"mark_stale reason must be a non-empty string, got {reason!r}")
    schema.check_no_secret("staleReason", reason)

    def _mutate(candidate):
        candidate["status"] = schema.STATUS_STALE
        candidate["staleReason"] = reason

    _mutate_rejection_record_atomically(store, record_id, _mutate)


def mark_revalidated(store: dict, record_id: str, new_record: dict) -> None:
    """A STALE record returning to fresh status must go through an
    ACTUAL re-derivation (`new_record` is the freshly-rebuilt record,
    typically from `schema.new_rejection_record` again with updated
    evidence/lastValidation/dependencies) -- this function never just
    strips the `status`/`staleReason` fields off the old record, since
    that would be "re-stamping" a record without re-deriving it, which
    context-manifest-schema.md section 5.1 explicitly forbids.
    """
    if not isinstance(new_record, Mapping):
        raise schema.SchemaError(f"mark_revalidated's new_record must be a record mapping, got {new_record!r}")
    if new_record.get("status") == schema.STATUS_STALE:
        raise StoreError("mark_revalidated's new_record must not itself be STALE")
    replace_rejection_record(store, record_id, new_record)


def write(path: str, store: dict, *, repo_root: str, expected_on_disk_hash: Optional[str], git_commit: Optional[str]) -> str:
    """Atomic write via an exclusive lockfile + temp-file + `os.replace`.
    `expected_on_disk_hash` is the hash `load()` returned when this
    store was last read (or `None` if the file did not exist at load
    time) -- if the file on disk right now does not match, this raises
    `ConcurrentModificationError` rather than silently overwriting
    whatever changed it. Returns the new on-disk hash.

    The hash check, serialization, and replace all happen while
    holding `_acquire_lock()`'s lockfile -- this SERIALIZES concurrent
    writers rather than merely detecting a race after the fact (see
    that function's own docstring for why the earlier, lock-free
    version was insufficient).
    """
    _resolve_safe(path, repo_root)

    # [ADDED, per explicit instruction closing a Round 4 independent
    # review finding promoted to Major]: the same record-level trust
    # boundary `load()` applies, applied before anything is persisted --
    # a store mutated in memory must not be writable in a shape the
    # very next `load()` would refuse. Legacy records loaded from an old
    # file pass their lenient audit-only check and are written back
    # unchanged; a current record must pass strict validation. A
    # caller-side bug, so it raises (as `StoreError`, the type callers
    # of this function already handle).
    try:
        _validate_all_records(store.get("rejectionRecords", {}), store.get("missRecords", {}))
    except (schema.SchemaError, AttributeError, TypeError, KeyError, IndexError) as exc:
        raise StoreError(f"refusing to write a store containing an invalid record: {exc}") from exc

    # [CORRECTED, per a round-2 independent review Major: the lockfile
    # lives in the same directory as `path` -- when that directory
    # (e.g. a repository's first-ever `.security/`) does not exist yet,
    # acquiring the lock BEFORE creating the directory raised a raw,
    # uncaught FileNotFoundError instead of writing successfully. This
    # is a real regression from the round-1 fix, caught because every
    # existing test's fixture directory happened to already exist.]
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)

    lock_path = _acquire_lock(path)
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                current_bytes = f.read()
            current_hash = _hash_bytes(current_bytes)
        else:
            current_hash = None

        if current_hash != expected_on_disk_hash:
            raise ConcurrentModificationError(
                f"{path!r} changed on disk since it was loaded "
                f"(expected hash {expected_on_disk_hash!r}, found {current_hash!r}) -- "
                "refusing to overwrite a concurrent write"
            )

        return _write_locked(path, store, git_commit=git_commit)
    finally:
        _release_lock(lock_path)


_REPLACE_RETRY_ATTEMPTS = 5
_REPLACE_RETRY_DELAY_SECONDS = 0.05


def _replace_with_retry(tmp_path: str, path: str) -> None:
    """[ADDED, per a round-2 independent review Minor]: on Windows,
    `os.replace()` can raise `PermissionError` (WinError 5, a sharing
    violation) when another process briefly has `path` open for
    reading -- independently reproduced by the reviewer under an
    8-thread load/write-retry stress test (1-5 occurrences out of ~200
    writes). This is transient, not a real failure -- a short bounded
    retry resolves it without changing this function's own atomicity
    guarantee (the temp file is still fully written before any replace
    attempt). A caller catching only `StoreError` must not be blindsided
    by a raw `PermissionError` if every retry is exhausted, so the last
    failure is wrapped.
    """
    last_exc: Optional[OSError] = None
    for attempt in range(_REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as exc:
            last_exc = exc
            if attempt < _REPLACE_RETRY_ATTEMPTS - 1:
                time.sleep(_REPLACE_RETRY_DELAY_SECONDS)
    raise StoreError(f"could not replace {path!r} after {_REPLACE_RETRY_ATTEMPTS} attempts: {last_exc}") from last_exc


def _write_locked(path: str, store: dict, *, git_commit: Optional[str]) -> str:
    store = dict(store)
    store["schemaVersion"] = schema.SCHEMA_VERSION
    store["writerVersion"] = WRITER_VERSION
    store["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    store["gitCommit"] = git_commit

    # Deterministic serialization (sort_keys) so an unrelated re-save
    # never produces a diff from key-order alone.
    serialized = json.dumps(store, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    # [ADDED, Batch 2 preflight, per explicit instruction closing a
    # Round 6 disclosure]: encode BEFORE any file is created. A lone
    # surrogate anywhere in the store (a `surrogateescape`-decoded
    # non-UTF-8 file name, for instance) used to raise a raw
    # UnicodeEncodeError from inside the text-mode write, after the
    # temp file already existed. The validators now refuse such strings
    # earlier (schema._check_utf8_encodable), so this is the
    # serialization-boundary backstop: same StoreError type callers
    # already handle, no partial file, nothing on disk touched, and the
    # message never echoes the value.
    try:
        payload = serialized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise StoreError(
            f"refusing to write: the store contains a code point that cannot be encoded as UTF-8 "
            f"(lone surrogate at serialized offset {exc.start}); fix or re-derive the offending record"
        ) from None

    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".feedback.json.", suffix=".tmp", dir=directory)
    try:
        # Binary write of the already-encoded bytes -- no newline
        # translation (on Windows, text mode would silently turn every
        # "\n" into "\r\n" and make the on-disk bytes differ from the
        # hash below) and no second encoding step that could fail.
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    return _hash_bytes(payload)
