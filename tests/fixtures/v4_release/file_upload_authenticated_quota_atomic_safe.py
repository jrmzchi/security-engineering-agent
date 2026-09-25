# Fixture: file upload (SAFE -- validated, size-limited, regenerated name, never served, atomic per-user quota),
# V4 release corpus row RV-28 (revision 5 of the corpus)
#
# Expected review outcome: NO confirmed finding. False-positive-avoidance
# counterpart to file_upload_unsafe.py -- a reviewer must not flag this just
# because it is a file-upload endpoint.
#
# Why it's safe: everything the upload relies on is in this file. The route
# requires a signed-in session (Flask's signed session cookie; the secret is
# required at start-up; the cookie is HttpOnly, Secure and SameSite=Strict, so
# a cross-site POST does not carry it). The request body is capped; the type
# is checked by content (magic bytes), not by name or client MIME type; the
# stored name is generated; files go to a per-user directory outside any
# served path; and each user has a fixed file quota.
#
# The quota is enforced by reserving a numbered slot before anything is
# written: os.open(..., O_CREAT | O_EXCL) creates a slot file only if it does
# not exist, as one atomic filesystem operation. That holds across threads
# and across worker processes that use the same UPLOAD_ROOT on a local
# filesystem, because the filesystem -- not a lock inside one process --
# decides which request gets each slot.
# At most MAX_FILES_PER_USER slots can exist, so at most that many uploads can
# be stored. If writing the upload fails, the request deletes only the file it
# created itself and releases its slot. If a worker dies between reserving and
# writing, its slot stays taken: the quota errs towards refusing uploads,
# never towards exceeding the cap.
#
# Replaces v4_release/file_upload_authenticated_safe.py (kept unchanged as the
# regression input for the quota race: it counts the directory and writes
# afterwards, so concurrent requests can all pass the count). See
# tests/validation/v4-release-corpus.md.

import os
import uuid
from functools import wraps

from flask import Flask, abort, request, session

SECRET_KEY = os.environ.get("UPLOAD_APP_SECRET_KEY", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError("UPLOAD_APP_SECRET_KEY must be set to at least 32 characters")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Strict",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)

UPLOAD_ROOT = "/var/app/private-uploads"
MAX_FILES_PER_USER = 100
ALLOWED_MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
}


def signed_in_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not isinstance(session.get("user_id"), int):
            abort(401)
        return view(*args, **kwargs)
    return wrapper


def sniff_extension(data: bytes) -> str | None:
    for magic, ext in ALLOWED_MAGIC_BYTES.items():
        if data.startswith(magic):
            return ext
    return None


# Takes one of the user's MAX_FILES_PER_USER slots; None when all are taken.
def reserve_slot(user_dir: str) -> str | None:
    slots_dir = os.path.join(user_dir, ".slots")
    os.makedirs(slots_dir, exist_ok=True)
    for number in range(MAX_FILES_PER_USER):
        slot = os.path.join(slots_dir, f"{number:03d}")
        try:
            fd = os.open(slot, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        os.close(fd)
        return slot
    return None


# Writes the upload under a reserved slot; None when the quota is reached.
def store_upload(user_dir: str, data: bytes, ext: str) -> str | None:
    slot = reserve_slot(user_dir)
    if slot is None:
        return None
    generated_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(user_dir, generated_name)
    created = False
    try:
        with open(path, "xb") as out:
            created = True
            out.write(data)
    except BaseException:
        if created:
            os.unlink(path)
        os.unlink(slot)
        raise
    return generated_name


@app.route("/upload", methods=["POST"])
@signed_in_required
def upload():
    f = request.files.get("file")
    if f is None:
        abort(400, "no file")
    data = f.read()
    ext = sniff_extension(data)
    if ext is None:
        abort(400, "unsupported file type")

    user_dir = os.path.join(UPLOAD_ROOT, str(session["user_id"]))
    os.makedirs(user_dir, exist_ok=True)
    generated_name = store_upload(user_dir, data, ext)
    if generated_name is None:
        abort(429, "upload quota reached")
    return {"status": "uploaded", "id": generated_name}
