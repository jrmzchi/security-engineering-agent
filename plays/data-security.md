# Play: Data Security (Cryptography & Sensitive Data)

Authoritative procedure for cryptography and sensitive-data-handling
findings.

## Scope

```text
Hardcoded encryption keys
Weak algorithms
Static IV
Nonce reuse
Improper password hashing
Insecure random generation
Certificate validation bypass
```

Password hashing specifically is also covered from the authentication
angle in `plays/authentication.md` — this play covers the cryptographic
primitive; that one covers the authentication-flow context.

## Hardcoded encryption keys (CWE-321 / CWE-798)

A key or credential compiled into source or committed in configuration is
a finding regardless of how the key is used, because anyone with source
access (which, for many projects, includes former employees, contractors,
or anyone the repo leaks to) can decrypt anything encrypted with it.
Remediation is always the same shape: move the key to a secret store or
environment variable injected at runtime, and rotate the key (assume it
is already compromised once it has been committed).

A key in a test fixture or documentation example is not automatically
exempt from this — apply the same real/example determination as
`plays/secrets-security.md`'s "before reporting a hit" check (is it a
value clearly generated for the test, or a real key that happens to live
in a test file?) rather than treating "it's in `tests/`" as a blanket
pass.

## Weak algorithms (CWE-327)

```text
DES, RC4, MD5 (as a general-purpose hash or for anything security-relevant)
SHA-1 for anything security-relevant (collision-resistance already broken)
ECB mode for block ciphers (does not hide data patterns)
Custom/home-rolled cryptographic algorithms
```

Note: MD5/SHA-1 used purely as a non-security checksum (e.g. deduplicating
uploaded files by content hash, with no security property depended on) is
not a security finding — assess what property the hash is relied on for.

## Static IV / nonce reuse (CWE-329 / CWE-323)

For any mode requiring a unique IV/nonce per encryption operation
(CBC, GCM, CTR, ChaCha20-Poly1305), check whether the IV/nonce is:

```text
hardcoded / constant across all encryptions
derived deterministically from data that can repeat (e.g. a counter that
    resets, or a hash of predictable input)
generated with a CSPRNG and unique per operation (safe)
```

For GCM specifically, nonce reuse under the same key is especially severe
— it can fully break confidentiality and authenticity for the affected
messages.

## Improper password hashing (CWE-916)

See `plays/authentication.md`'s "Weak password handling" section — same
finding, cross-referenced from both angles since it can be found either
by reviewing the auth flow or by reviewing crypto primitive usage
directly.

## Insecure random generation (CWE-338)

```text
.NET Random / JS Math.random() / Python random.random() / C rand() used
    for: session tokens, password reset tokens, API keys, CSRF tokens,
    encryption keys/IVs, anything else where unpredictability is a
    security property
    -> finding; these are not cryptographically secure

Same non-CSPRNG APIs used for: UI jitter, non-security shuffling,
    load-balancing choice, sample data generation
    -> not a finding
```

Safe replacements: `crypto.randomBytes`/`crypto.getRandomValues` (Node/
browser), `secrets` module (Python),
`System.Security.Cryptography.RandomNumberGenerator.GetBytes` (.NET —
note `RNGCryptoServiceProvider` is obsolete as of .NET 6, `SYSLIB0023`;
do not suggest it in remediation examples).

## Certificate validation bypass (CWE-295)

```text
ServerCertificateCustomValidationCallback returning true unconditionally (.NET)
requests(..., verify=False) (Python)
rejectUnauthorized: false (Node)
A custom TrustManager that accepts all certificates (Java)
NODE_TLS_REJECT_UNAUTHORIZED=0 set outside of a controlled local dev environment
```

This defeats TLS's protection against man-in-the-middle attacks for the
affected connection. If found only inside test code that never runs in a
non-test environment, note it but do not treat it at production severity
— verify which environments actually execute that code path.
