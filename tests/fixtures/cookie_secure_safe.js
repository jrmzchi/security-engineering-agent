// Fixture: Session cookie set with security flags (SAFE)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to cookie_insecure_unsafe.js — a reviewer must
// not flag this just because it's a session-setting endpoint.
//
// Why it's safe: httpOnly prevents script access to the cookie value
// entirely; secure ensures it is only ever sent over HTTPS; sameSite
// 'strict' is appropriate here since this cookie is only needed for
// same-site requests (no legitimate top-level cross-site navigation
// needs to carry it).

const crypto = require('crypto');
const express = require('express');
const app = express();

app.post('/login', (req, res) => {
  const sessionId = createSession();
  // SAFE: httpOnly + secure + sameSite all set explicitly.
  res.cookie('session', sessionId, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
  });
  res.json({ status: 'logged in' });
});

function createSession() {
  // SAFE: unguessable token, not derived from username/time.
  return crypto.randomBytes(32).toString('hex');
}

module.exports = app;
