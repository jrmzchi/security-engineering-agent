# Fixture: "After" state for a remediation test — a FAKE fix
# (STILL VULNERABLE, despite looking like a response to the finding)
#
# Pair with remediation_fake_fix_before.py. This is what
# plays/security-remediation.md's "Fake fix" section describes: a fix
# that special-cases the exact reproduction string from the original
# finding (here, blocking the literal substring "' OR '1'='1") rather
# than addressing the root cause (string-concatenated SQL). The
# underlying missing control — parameterization — is still absent.
#
# Expected review outcome: independent re-validation (per
# plays/security-remediation.md's "Independent re-validation" section)
# must report STILL_VULNERABLE, not RESOLVED. Reconstructing the
# attack path with a DIFFERENT payload that doesn't contain the
# blocked substring — e.g. username = "x' UNION SELECT password,1,1
# FROM admin_users--" or simply "y' OR 'a'='a" (same logic, different
# literal string) — still succeeds, because the query is still built by
# concatenation; only the one specific string the "fix" happened to
# check for is blocked.
#
# A validator that only re-tests the ORIGINAL payload against this file
# would incorrectly see it "fixed" (the exact reproduction string is
# now rejected) and report RESOLVED — that is precisely the false
# assurance this fixture exists to catch.

from flask import Flask, request, abort
import sqlite3

app = Flask(__name__)


@app.route("/users")
def get_user():
    username = request.args.get("username", "")
    # FAKE FIX: blocks the literal string demonstrated in the original
    # finding, not the underlying vulnerability class.
    if "' OR '1'='1" in username:
        abort(400, "invalid input")

    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # STILL VULNERABLE: the query is still built by string
    # concatenation - any other injection payload still works.
    query = "SELECT id, username, email FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return {"users": rows}
