// Fixture: credentialed CORS restricted to an explicit allowlist (SAFE), V4 release corpus row RV-15
//
// Expected review outcome: NO confirmed finding. False-positive-avoidance
// counterpart to cors_wildcard_credentials_unsafe.js -- a reviewer must not
// flag this just because credentials are enabled and CORS headers are set.
//
// Why it's safe: the Origin is echoed only when it is in a fixed allowlist
// (Vary: Origin is always set); everything the credentialed endpoint relies
// on is in this file: the session middleware (secret required at start-up,
// HttpOnly/Secure/SameSite=Lax cookie, no uninitialized sessions) and a
// route-level guard that answers 401 unless the session carries a signed-in
// user id. The endpoint returns only that caller's display preferences.
//
// Replaces tests/fixtures/cors_restricted_safe.js for the V4 release corpus
// only: that fixture's /api/account reads req.session.user without any
// session middleware or guard in the fixture. See
// tests/validation/v4-release-corpus.md.

const express = require('express');
const session = require('express-session');

const SESSION_SECRET = process.env.SESSION_SECRET;
if (!SESSION_SECRET || SESSION_SECRET.length < 32) {
  throw new Error('SESSION_SECRET must be set to at least 32 characters');
}

const app = express();

const ALLOWED_ORIGINS = new Set([
  'https://app.example.com',
  'https://admin.example.com',
]);

app.use((req, res, next) => {
  res.vary('Origin');
  const origin = req.headers.origin;
  if (ALLOWED_ORIGINS.has(origin)) {
    res.header('Access-Control-Allow-Origin', origin);
    res.header('Access-Control-Allow-Credentials', 'true');
  }
  next();
});

app.use(session({
  name: 'sid',
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: { httpOnly: true, secure: true, sameSite: 'lax', maxAge: 30 * 60 * 1000 },
}));

function requireSignedIn(req, res, next) {
  if (!req.session || typeof req.session.userId !== 'number') {
    return res.status(401).json({ error: 'sign-in required' });
  }
  next();
}

const DEFAULT_PREFERENCES = Object.freeze({ theme: 'light', language: 'en-US' });
const preferencesBySessionUser = new Map();

app.get('/api/preferences', requireSignedIn, (req, res) => {
  const prefs = preferencesBySessionUser.get(req.session.userId) || DEFAULT_PREFERENCES;
  res.json({ theme: prefs.theme, language: prefs.language });
});

module.exports = app;
