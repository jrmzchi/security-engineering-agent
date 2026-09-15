# Fixture: Outbound fetch restricted to an allowlisted host, with the
# resolved IP checked (SAFE)
#
# Expected review outcome: NO confirmed finding. False-positive-
# avoidance counterpart to ssrf_user_url_unsafe.py — a reviewer must
# not flag this just because it makes an outbound HTTP request derived
# from user input.
#
# Why it's safe: the host is checked against an explicit allowlist
# (not just "looks like a URL"), and the *resolved* IP address is
# checked against internal/link-local/loopback ranges before
# connecting, which a hostname-only check would miss.
#
# Caveat this fixture does NOT fully address: the resolved IP from
# resolved_ip_is_internal() is not pinned for the actual connection —
# requests.get() below re-resolves the hostname itself, so a DNS
# answer that changes between the two lookups (rebinding) would still
# slip through. Fully defending against rebinding requires connecting
# to the already-checked IP directly (e.g. a custom transport adapter)
# while keeping the original Host header. See plays/api-security.md's
# SSRF section.

import ipaddress
import socket
from urllib.parse import urlparse

from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

ALLOWED_HOSTS = {"images.trusted-partner.com", "cdn.trusted-partner.com"}


def resolved_ip_is_internal(hostname: str) -> bool:
    try:
        addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(addr)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except socket.gaierror:
        return True  # cannot resolve -> treat as unsafe, fail closed


@app.route("/import-avatar", methods=["POST"])
def import_avatar():
    image_url = request.json.get("image_url", "")
    parsed = urlparse(image_url)

    # SAFE: allowlist the host and scheme.
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        return jsonify({"error": "host not allowed"}), 400

    # SAFE (partial): also check the resolved IP, not just the
    # hostname string. Does not pin the connection to this resolved
    # IP - see the caveat in the header comment.
    if resolved_ip_is_internal(parsed.hostname):
        return jsonify({"error": "resolved address not allowed"}), 400

    resp = requests.get(image_url, timeout=5, allow_redirects=False)
    return jsonify({"status": "fetched", "size": len(resp.content)})
