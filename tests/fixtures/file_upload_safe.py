# Fixture: File upload (SAFE — validated, size-limited, regenerated
# name, stored outside any served directory)
#
# Expected review outcome: NO confirmed finding. False-positive-
# avoidance counterpart to file_upload_unsafe.py — a reviewer must not
# flag this just because it is a file-upload endpoint.
#
# Why it's safe: file type is checked by content (magic bytes), request
# size is capped (see plays/file-security.md's "No size limit ->
# resource exhaustion" — an earlier version of this fixture had no cap
# and would itself have been a valid CWE-770 finding; MAX_CONTENT_LENGTH
# closes that), the filename is regenerated (never taken from the
# client), and storage is outside any directory the app serves
# statically — so even a successful upload cannot be requested back and
# rendered.

import os
import uuid
from flask import Flask, request, abort

app = Flask(__name__)

# SAFE: caps request body size — Flask/Werkzeug reject anything larger
# before it is read into memory.
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

# Outside app.static_folder on purpose — never served directly.
UPLOAD_DIR = "/var/app/private-uploads"

ALLOWED_MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpg",   # JPEG
    b"\x89PNG\r\n\x1a\n": "png",
}


def sniff_extension(data: bytes) -> str | None:
    for magic, ext in ALLOWED_MAGIC_BYTES.items():
        if data.startswith(magic):
            return ext
    return None


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    data = f.read()

    # SAFE: validate by content, not by client-supplied extension/MIME.
    ext = sniff_extension(data)
    if ext is None:
        abort(400, "unsupported file type")

    # SAFE: regenerated filename — the client's filename is never used
    # to build a filesystem path.
    generated_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, generated_name)

    with open(save_path, "wb") as out:
        out.write(data)

    return {"status": "uploaded", "id": generated_name}
