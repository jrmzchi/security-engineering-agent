# Fixture: Hardcoded-looking credential that is actually a documented
# placeholder (SAFE — not a real secret)
#
# Expected review outcome: NO confirmed finding, or at most an
# INFORMATIONAL note. False-positive-avoidance counterpart to
# hardcoded_secret_unsafe.py.
#
# Why this is not a finding: AKIAIOSFODNN7EXAMPLE /
# wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY are AWS's own,
# officially-documented placeholder credentials, used throughout AWS's
# public documentation specifically as non-functional examples — they
# are not provisioned against any real account and cannot be activated.
# plays/secrets-security.md's "is it a real secret or an example/test/
# placeholder value?" check should recognize this via the literal
# "EXAMPLE" marker in both values and resolve it as a placeholder, not
# a live credential — the same way it should NOT flag this docstring
# itself for containing the string "SECRET_ACCESS_KEY".

# Example .env entry from our setup documentation (README-style comment
# block, not code that runs):
#
#   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
#   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
#
# Copy this into your local .env and replace both values with your own
# credentials from the AWS IAM console before running the app.

DOCS_EXAMPLE_ENV_SNIPPET = """
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
"""
