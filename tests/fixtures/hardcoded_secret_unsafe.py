# Fixture: Hardcoded credentials (VULNERABLE)
#
# Expected review outcome: CONFIRMED secret exposure, TWO findings —
# the AWS credential pair (one finding) and the database connection
# string (a second, separate finding). See plays/secrets-security.md
# and plays/data-security.md.
#
# Why this is a real finding, not a false positive: both values are
# realistic-looking (correct AWS access key ID / secret access key
# shape, no "EXAMPLE"/"TEST"/"XXX"/"fake"/"dummy" marker in either
# value; a database password that is not a textbook placeholder
# either) and appear in a module written like production configuration.
# plays/secrets-security.md's "is it a real secret or an example/test/
# placeholder value?" check is a check on the VALUE itself, not on
# which directory the file happens to live in — a real leaked
# credential does not stop being real because it was found inside a
# repository's tests/ directory. See
# tests/validation/README.md for how to run a validation pass without
# this comment block (and the fact that this file lives under
# tests/fixtures/) leaking the expected answer.
#
# Contrast with hardcoded_secret_example_value.py, which uses AWS's own
# officially-documented placeholder key (containing the literal marker
# "EXAMPLE") and should NOT be flagged — the distinguishing signal is
# in the value's own content, not the file's location.
#
# Meta-note (not part of the finding itself): the values below are
# synthetic, generated only for this fixture, and are not provisioned
# against any real account or database.

AWS_ACCESS_KEY_ID = "AKIAQZRJMN4T7VXHK2LP"
AWS_SECRET_ACCESS_KEY = "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"

DATABASE_URL = "postgresql://app_user:xQ7mK9pLwZ3vN8tR2h@prod-db.internal:5432/appdb"


def get_s3_client():
    import boto3

    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
