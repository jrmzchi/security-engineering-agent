// Fixture: Session cookie set without security flags (VULNERABLE)
//
// Expected review outcome: CONFIRMED MEDIUM/HIGH insecure session
// cookie configuration (CWE-614 missing Secure, CWE-1004 missing
// HttpOnly). See plays/authentication.md's "Session hijacking" and
// plays/configuration-security.md's "Insecure cookies".
//
// Attack path: no HttpOnly means any script running on this origin
// (e.g. via an XSS bug elsewhere on the site) can read the session
// cookie directly via document.cookie and exfiltrate it. No Secure
// means the cookie is also sent over plain HTTP if the site is ever
// reached that way (a downgrade, a misconfigured link, mixed content),
// exposing it to network-level interception.

const crypto = require('crypto');
const express = require('express');
const app = express();

app.post('/login', (req, res) => {
  const sessionId = createSession();
  // VULNERABLE: no httpOnly, no secure, no explicit sameSite.
  res.cookie('session', sessionId);
  res.json({ status: 'logged in' });
});

function createSession() {
  // Unguessable token - the vulnerability under test here is the
  // missing cookie flags, not the token generation.
  return crypto.randomBytes(32).toString('hex');
}

module.exports = app;
