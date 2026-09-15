// Fixture: CORS restricted to an explicit allowlist (SAFE)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to cors_wildcard_credentials_unsafe.js — a
// reviewer must not flag this just because credentials are enabled and
// CORS headers are present; the origin is checked against an explicit
// allowlist rather than reflected or wildcarded.

const express = require('express');
const app = express();

const ALLOWED_ORIGINS = new Set([
  'https://app.example.com',
  'https://admin.example.com',
]);

// SAFE: explicit allowlist check, not a reflection of the request's
// own Origin header.
app.use((req, res, next) => {
  const origin = req.headers.origin;
  if (ALLOWED_ORIGINS.has(origin)) {
    res.header('Access-Control-Allow-Origin', origin);
    res.header('Access-Control-Allow-Credentials', 'true');
  }
  next();
});

app.get('/api/account', (req, res) => {
  res.json({ email: req.session.user.email, balance: req.session.user.balance });
});

module.exports = app;
