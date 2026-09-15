# Fixture: "Before" state for a remediation test (VULNERABLE)
#
# Pair this with remediation_fake_fix_after_still_vulnerable.py — see
# tests/validation/README.md and plays/security-remediation.md's "Fake
# fix" section for what this pair is testing: that a validator, given
# both, reports the "after" as STILL_VULNERABLE rather than RESOLVED.
#
# Expected review outcome (this file, in isolation): CONFIRMED
# HIGH/CRITICAL SQL injection (CWE-89) — same shape as
# sql_injection_unsafe.py. Original finding's demonstrated payload:
# username = "' OR '1'='1".

from flask import Flask, request
import sqlite3

app = Flask(__name__)


@app.route("/users")
def get_user():
    username = request.args.get("username", "")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # VULNERABLE: string-concatenated SQL.
    query = "SELECT id, username, email FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return {"users": rows}
