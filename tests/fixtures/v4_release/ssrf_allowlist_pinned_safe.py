# Fixture: outbound fetch of a user-supplied URL (SAFE), V4 release corpus row RV-22
#
# Expected review outcome: NO confirmed finding. False-positive-avoidance
# counterpart to ssrf_user_url_unsafe.py -- a reviewer must not flag this
# just because it makes an outbound HTTP request derived from user input.
#
# Why it's safe: the URL must be https with no credentials or explicit port
# and a host in an explicit allowlist; every address the host resolves to
# must be a public (globally routable) address; and the connection is then
# made to that already-checked address itself (TLS still verifies the
# certificate for the original host name and sends it as SNI and Host), so a
# second DNS answer cannot redirect it (no rebinding window). Redirects are
# not followed and at most MAX_BYTES of the body are read.
#
# Replaces tests/fixtures/ssrf_allowlist_safe.py for the V4 release corpus
# only: that fixture checks the resolved IP but lets requests.get() resolve
# the host again, a DNS-rebinding gap its own header admits, and reads an
# unbounded body. See tests/validation/v4-release-corpus.md.

import ipaddress
import socket
from urllib.parse import urlparse

import certifi
import urllib3
from flask import Flask, jsonify, request

app = Flask(__name__)

ALLOWED_HOSTS = {"images.trusted-partner.com", "cdn.trusted-partner.com"}
MAX_BYTES = 2 * 1024 * 1024


def public_address(hostname: str) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return None
    addresses = {info[4][0] for info in infos}
    if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
        return None
    return sorted(addresses)[0]


@app.route("/partner-images/preview", methods=["POST"])
def preview_partner_image():
    image_url = str((request.get_json(silent=True) or {}).get("image_url", ""))
    parsed = urlparse(image_url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.port is not None or parsed.username or parsed.password):
        return jsonify({"error": "url not allowed"}), 400

    address = public_address(parsed.hostname)
    if address is None:
        return jsonify({"error": "address not allowed"}), 400

    pool = urllib3.HTTPSConnectionPool(
        address, port=443, server_hostname=parsed.hostname, assert_hostname=parsed.hostname,
        cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), timeout=urllib3.Timeout(total=5), retries=False)
    path = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
    resp = pool.urlopen("GET", path, headers={"Host": parsed.hostname}, redirect=False, preload_content=False)
    try:
        body = resp.read(MAX_BYTES + 1)
    finally:
        resp.release_conn()
    if len(body) > MAX_BYTES:
        return jsonify({"error": "image too large"}), 413
    return jsonify({"status": "fetched", "size": len(body)})
