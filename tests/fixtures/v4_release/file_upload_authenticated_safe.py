# Fixture: file upload (SAFE -- validated, size-limited, regenerated name, never served), V4 release corpus row RV-28
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
# Replaces tests/fixtures/file_upload_safe.py for the V4 release corpus only:
# that fixture accepts anonymous uploads with no access control or quota in
# the fixture. See tests/validation/v4-release-corpus.md.

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
    if len(os.listdir(user_dir)) >= MAX_FILES_PER_USER:
        abort(429, "upload quota reached")

    generated_name = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(user_dir, generated_name), "xb") as out:
        out.write(data)
    return {"status": "uploaded", "id": generated_name}
