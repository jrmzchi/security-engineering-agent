# Fixture: SSRF via unrestricted outbound fetch of a user-supplied URL
# (VULNERABLE)
#
# Expected review outcome: CONFIRMED HIGH/CRITICAL SSRF (CWE-918). See
# plays/api-security.md's "External APIs / webhooks / SSRF" section.
#
# Attack path: `image_url` is attacker-controlled (request body), the
# server fetches it directly with no allowlist, no scheme restriction,
# and no check on the resolved IP — an attacker can request
# `http://169.254.169.254/latest/meta-data/` (cloud metadata endpoint)
# or `http://localhost:6379/` (an internal service) and the response is
# echoed back, giving the attacker read access to internal network
# resources the server can reach but the attacker cannot reach directly.

from flask import Flask, request, jsonify
import requests

app = Flask(__name__)


@app.route("/import-avatar", methods=["POST"])
def import_avatar():
    image_url = request.json.get("image_url")
    # VULNERABLE: fetches whatever URL the client supplies, no
    # allowlist, no scheme check, no check on the resolved address.
    resp = requests.get(image_url, timeout=5)
    return jsonify({"status": "fetched", "size": len(resp.content)})
