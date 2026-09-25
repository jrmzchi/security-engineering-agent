// Fixture: session-style cookie set with security flags (SAFE), V4 release corpus row RV-13
//
// Expected review outcome: NO confirmed finding. False-positive-avoidance
// counterpart to cookie_insecure_unsafe.js -- a reviewer must not flag this
// just because an endpoint issues a session cookie.
//
// Why it's safe: the cookie value is an unguessable random id; httpOnly
// keeps it away from scripts, secure restricts it to HTTPS, sameSite
// 'strict' keeps it off cross-site requests, and it is scoped to /cart
// with a bounded lifetime. It identifies an anonymous shopping cart only:
// it grants no identity or privilege, so issuing it without a login is
// correct.
//
// Replaces tests/fixtures/cookie_secure_safe.js for the V4 release corpus
// only: that fixture's /login handler answers "logged in" and issues a
// session without checking any credential, a real authentication defect a
// correct review reports. See tests/validation/v4-release-corpus.md.

const crypto = require('crypto');
const express = require('express');

const app = express();

app.post('/cart/session', (req, res) => {
  const cartSessionId = crypto.randomBytes(32).toString('hex');
  res.cookie('cart_session', cartSessionId, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    path: '/cart',
    maxAge: 2 * 60 * 60 * 1000,
  });
  res.json({ status: 'cart ready' });
});

module.exports = app;
