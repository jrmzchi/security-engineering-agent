# Fixture: Unrestricted file upload with traversal in the filename
# (VULNERABLE)
#
# Expected review outcome: CONFIRMED HIGH/CRITICAL — CWE-434
# (unrestricted upload) combined with CWE-22 (path traversal via the
# client-supplied filename), enabling arbitrary file write. See
# plays/file-security.md's "Uploads" section.
#
# (An earlier version of this fixture additionally claimed that an
# uploaded ".py" file would execute — Flask/Werkzeug's static-file
# serving does not execute anything regardless of extension, so that
# claim did not hold and has been removed. The arbitrary-file-write
# path below does not depend on it.)
#
# Attack path: no extension/content validation, and the client-supplied
# filename is used directly, unsanitized, to build the save path.
# `os.path.join` does not stop `..` segments from escaping the intended
# directory (see references/python-security.md) — a multipart upload
# with filename "../../app.py" overwrites the application's own source
# file; a filename of "../templates/base.html" overwrites a template
# rendered on every page (stored XSS on every subsequent request,
# regardless of whether anything ever "executes").

import os
from flask import Flask, request

app = Flask(__name__)

UPLOAD_DIR = os.path.join(app.static_folder, "uploads")


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    # VULNERABLE: no extension/content-type validation, and the
    # client-supplied filename is used as-is to build the save path —
    # os.path.join does not strip ".." segments, so a filename like
    # "../../app.py" writes outside UPLOAD_DIR entirely.
    save_path = os.path.join(UPLOAD_DIR, f.filename)
    f.save(save_path)
    return {"status": "uploaded", "path": save_path}
