// Fixture: CORS reflecting any origin with credentials enabled (VULNERABLE)
//
// Expected review outcome: CONFIRMED HIGH — CORS misconfiguration
// (CWE-942). See plays/web-security.md's "CORS misconfiguration"
// section.
//
// Note on naming: a literal `Access-Control-Allow-Origin: *` combined
// with `Access-Control-Allow-Credentials: true` is invalid per the
// Fetch spec and most browsers reject it outright — the real-world
// version of this misconfiguration is an origin-REFLECTING policy
// (whatever Origin the request sends, echo it back) combined with
// credentials enabled, which achieves the same effectively-any-origin
// result and IS accepted by browsers. That is what this fixture shows.
//
// Attack path: a malicious site at https://evil.example makes a
// credentialed fetch() to this API. The server reflects
// "https://evil.example" back as Access-Control-Allow-Origin and sets
// Access-Control-Allow-Credentials: true, so the browser allows the
// cross-site page to read the authenticated response — any
// session-cookie-authenticated data this API returns is now readable
// by any origin that asks. (This requires the session cookie itself
// to be set with SameSite=None; Secure — under the modern
// Lax-by-default cookie behavior, a cookie with no explicit SameSite
// would not be sent on this cross-site fetch at all, and the CORS
// misconfiguration alone would not be exploitable.)

const express = require('express');
const app = express();

// VULNERABLE: reflects whatever Origin header the request sends,
// rather than checking it against an allowlist, and enables credentials.
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', req.headers.origin);
  res.header('Access-Control-Allow-Credentials', 'true');
  next();
});

app.get('/api/account', (req, res) => {
  // Assume session-cookie authentication elsewhere in the app, with
  // the cookie set as SameSite=None; Secure (required for it to be
  // sent on the cross-site request this fixture's attack path relies
  // on — see the note above).
  res.json({ email: req.session.user.email, balance: req.session.user.balance });
});

module.exports = app;
