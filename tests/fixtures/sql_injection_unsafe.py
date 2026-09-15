# Fixture: SQL injection (VULNERABLE)
#
# Expected review outcome: CONFIRMED HIGH/CRITICAL SQL injection (CWE-89).
# See plays/code-review.md's injection section and
# references/sql-security.md.
#
# Attack path: the `username` query parameter is attacker-controlled,
# reaches cursor.execute() concatenated directly into the query text,
# and changes the query's structure (e.g. `' OR '1'='1`).

from flask import Flask, request
import sqlite3

app = Flask(__name__)


@app.route("/users")
def get_user():
    username = request.args.get("username", "")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # VULNERABLE: string-concatenated SQL. An attacker requesting
    # /users?username=' OR '1'='1 bypasses the intended filter and
    # returns every row.
    query = "SELECT id, username, email FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return {"users": rows}
