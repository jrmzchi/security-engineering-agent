# Fixture: SQL injection (SAFE — parameterized query)
#
# Expected review outcome: NO confirmed finding. This is the
# false-positive-avoidance counterpart to sql_injection_unsafe.py — a
# reviewer must not flag this just because it queries a database with
# a request parameter in scope.
#
# Why it's safe: the query text is fixed; `username` is passed as a
# separate bound parameter and never becomes part of the SQL grammar,
# regardless of what characters it contains.

from flask import Flask, request
import sqlite3

app = Flask(__name__)


@app.route("/users")
def get_user():
    username = request.args.get("username", "")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # SAFE: parameterized query — the driver binds the value
    # separately from the query text.
    cursor.execute(
        "SELECT id, username, email FROM users WHERE username = ?",
        (username,),
    )
    rows = cursor.fetchall()
    conn.close()
    return {"users": rows}
