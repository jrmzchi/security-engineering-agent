# Fixture: SQL query built from request data (SAFE — parameterized query), V4 release corpus row RV-02
#
# Expected review outcome: NO confirmed finding. False-positive-avoidance
# counterpart to sql_injection_unsafe.py -- a reviewer must not flag this
# just because it queries a database with a request parameter in scope.
#
# Why it's safe: the query text is fixed; `category` is passed as a
# separate bound parameter and never becomes part of the SQL grammar,
# regardless of what characters it contains. The endpoint is a public
# product-catalog lookup: it returns only published catalog fields (SKU,
# name, category, description), no user, account or other personal data,
# so it is legitimately served without authentication.
#
# Replaces tests/fixtures/sql_injection_safe.py for the V4 release corpus
# only: that V3 fixture's /users route returns users' e-mail addresses
# without any authentication check, a real CWE-306 finding a correct review
# reports. See tests/validation/v4-release-corpus.md.

from flask import Flask, request
import sqlite3

app = Flask(__name__)


@app.route("/catalog/products")
def list_products():
    category = request.args.get("category", "")
    conn = sqlite3.connect("catalog.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sku, name, category, description FROM products "
        "WHERE category = ? AND published = 1",
        (category,),
    )
    rows = cursor.fetchall()
    conn.close()
    return {"products": [
        {"sku": sku, "name": name, "category": cat, "description": description}
        for sku, name, cat, description in rows
    ]}
