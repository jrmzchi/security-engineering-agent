# RV-15: local check of express-session's MemoryStore behaviour (2026-09-29)

**Question.** Revision 6's RV-15 review CONFIRMED a LOW finding on
`tests/fixtures/v4_release/cors_allowlist_session_guarded_safe.js` (git blob `cb20c3a8`): express-session was
configured without a `store`, so it used the default MemoryStore, which "leaks memory ... session flooding". The
question is whether, with the fixture's configuration (`resave: false`, `saveUninitialized: false`, no `store`, and one
route that only reads the session), requests create or keep MemoryStore records. Until now it was NOT RESOLVED,
because express-session was not available locally.

**Result, for the tested versions only: no record is created or kept.** RV-15's revision-6 finding does not reproduce
with express-session **1.19.0** (and express 5.2.1, Node v26.7.0). This conclusion covers only that version. It does
not rewrite any earlier model result: revision 6's RV-15 answer stays a FAILED case in that round's record.

## Environment and installation (user-authorized, 2026-09-29)

- **Location:** an isolated scratch directory outside the repository. The repository's dependencies and lockfile were
  not touched; the repository has no Node package manifest.
- **Command:** `npm install --save-exact --ignore-scripts --no-audit --no-fund express-session@1.19.0 express@5.2.1`,
  in a scratch `package.json` created for the check. It added 76 packages.
- **Network:** used only to fetch those packages, plus one `npm view express-session version` to pin the current
  version.
- **Resolved versions** (scratch lockfile):
  - express-session 1.19.0 (`sha512-0csaMkGq…`);
  - express 5.2.1 (`sha512-hIS4idWW…`);
  - express-session's own nested cookie-signature 1.0.7, the signer that verifies `sid`;
  - cookie 0.7.2, uid-safe 2.1.5, on-headers 1.1.0.
  - (cookie-signature 1.2.2 at the top level is express's copy.)
- **Fixture:** `app.js` is a byte copy of the fixture. Its `git hash-object` is `cb20c3a8`, the same as the committed
  blob. It is loaded unchanged, with a random 64-character `SESSION_SECRET`.

## Method

- **Instrumentation.** Before the fixture is loaded, `session.MemoryStore.prototype` is wrapped:
  - `on` hands over the store instance the middleware creates internally, since that instance is not exported;
  - `set`, `touch`, `get` and `destroy` are counted;
  - the store's contents are read through its own `all()`.
- **Transports:**
  - plain HTTP;
  - "simulated TLS": `req.connection.encrypted = true` on each request before the app. express-session's secure check
    then treats the request as HTTPS, which matters because the fixture sets `cookie.secure: true`. The fixture's own
    configuration is not changed.
- **Requests per transport (515):**
  - 200 with no cookie;
  - 50 with a random `sid` without the `s:` prefix (ignored without a lookup);
  - 50 with an `s:` value carrying a bad signature;
  - 50 with the allowlisted `Origin`;
  - 50 to an unknown path;
  - 25 `OPTIONS` with the allowlisted `Origin`;
  - 50 with a `sid` validly signed with the fixture's own secret, by express-session's own signer, for a session id
    that is not in the store. This is the one shape that reaches `store.get`;
  - 20 `HEAD` and 20 `POST`.
- **Positive controls,** on the same library and cookie options over simulated TLS, 50 requests each. They show the
  instrumentation sees writes when a session is saved:
  - (a) `saveUninitialized: true`;
  - (b) `saveUninitialized: false` with a route that writes the session.

## Observed

| Run | Transport | Requests | Statuses | Set-Cookie headers | set / touch / get / destroy | Records in store |
|---|---|---|---|---|---|---|
| fixture (unchanged) | plain HTTP | 515 | 401 ×420, 404 ×70, 200 ×25 (OPTIONS) | 0 | 0 / 0 / 50 / 0 | **0** |
| fixture (unchanged) | simulated TLS | 515 | 401 ×420, 404 ×70, 200 ×25 (OPTIONS) | 0 | 0 / 0 / 50 / 0 | **0** |
| control (a) saveUninitialized true | simulated TLS | 50 | 200 ×50 | 50 | 50 / 0 / 0 / 0 | 50 |
| control (b) a route writes the session | simulated TLS | 50 | 200 ×50 | 50 | 50 / 0 / 0 / 0 | 50 |

**Reading.**
- With the fixture's configuration, no request saved or kept anything:
  - there was no `set`, `touch` or `destroy`, and the store ended empty;
  - only the 50 validly signed cookies made express-session look the session up (`get`), found nothing, and still
    saved nothing.
- Those 50 lookups also show the counters sit on the fixture's own store instance.
- The two controls show a saved session is counted and read back.
- The result matches what the code alone implies: `saveUninitialized: false`, and no route writes the session. The
  behavioural check confirms it for the tested versions.
- So the "session flooding grows the MemoryStore" impact has no request path in this case. MemoryStore's other
  properties are operational, not a security defect of the case: it is not shared across processes, and it loses its
  data on restart.

## Limits

- It covers only express-session 1.19.0 with express 5.2.1 on Node v26.7.0. The fixture pins no version.
- It is a behavioural check through the fixture's own routes. It does not audit express-session's source.
- The simulated TLS flag stands in for a real TLS listener. The plain-HTTP run gives the same result.

## The script (`check.js`, run with `node check.js` in the scratch directory, next to `app.js`)

```js
// RV-15 local check: does express-session, configured exactly as the fixture, create or keep MemoryStore records
// when no route writes the session? The fixture file (app.js, a byte copy of
// tests/fixtures/v4_release/cors_allowlist_session_guarded_safe.js) is used UNCHANGED.
//
// Instrumentation: MemoryStore.prototype methods are wrapped before the fixture is loaded, so the fixture's own
// default store (created inside session(), not exported) is observed:
//   - `on` is called on the store while the middleware is set up; that hands us the instance;
//   - set / touch / get / destroy are counted;
//   - the store's contents are read from the instance itself (`all`).
// Two positive controls (same library, same options but a session is written) show the instrumentation sees writes.
'use strict';
const http = require('http');
const crypto = require('crypto');
const session = require('express-session');
const express = require('express');
// the signer express-session itself uses (its own nested copy), to build a validly signed cookie for a session id
// that is not in the store -- the one request shape that reaches store.get()
const signature = require('express-session/node_modules/cookie-signature');

const MS = session.MemoryStore.prototype;
const stores = [];
const calls = { set: 0, touch: 0, get: 0, destroy: 0 };
const origOn = MS.on;
MS.on = function (...args) { if (!stores.includes(this)) stores.push(this); return origOn.apply(this, args); };
for (const m of Object.keys(calls)) {
  const orig = MS[m];
  MS[m] = function (...args) { calls[m] += 1; return orig.apply(this, args); };
}

process.env.SESSION_SECRET = crypto.randomBytes(32).toString('hex');

function storeSize(store) {
  return new Promise((resolve, reject) => store.all((err, all) => (err ? reject(err) : resolve(Object.keys(all || {}).length))));
}

function request(port, { path = '/api/preferences', method = 'GET', headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, path, method, headers }, (res) => {
      res.resume();
      res.on('end', () => resolve({ status: res.statusCode, setCookie: (res.headers['set-cookie'] || []).length }));
    });
    req.on('error', reject);
    req.end();
  });
}

async function run(label, app, tls, plan) {
  const before = { ...calls };
  const server = http.createServer((req, res) => {
    if (tls) req.connection.encrypted = true;   // TLS terminated at the socket: express-session's issecure() sees it
    app(req, res);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const statuses = {};
  let setCookies = 0;
  let n = 0;
  for (const step of plan) {
    for (let i = 0; i < step.count; i += 1) {
      const r = await request(port, step.make(i));
      statuses[r.status] = (statuses[r.status] || 0) + 1;
      setCookies += r.setCookie;
      n += 1;
    }
  }
  await new Promise((r) => server.close(r));
  const store = stores[stores.length - 1];
  const delta = Object.fromEntries(Object.keys(calls).map((k) => [k, calls[k] - before[k]]));
  return { label, transport: tls ? 'simulated TLS' : 'plain HTTP', requests: n, statuses, setCookieHeaders: setCookies,
           storeCalls: delta, recordsInStore: await storeSize(store) };
}

const ALLOWED = 'https://app.example.com';
const plan = [
  { count: 200, make: () => ({}) },                                                        // no cookie
  { count: 50, make: () => ({ headers: { cookie: `sid=${crypto.randomBytes(16).toString('hex')}` } }) },  // forged, unsigned
  { count: 50, make: () => ({ headers: { cookie: `sid=s%3A${crypto.randomBytes(16).toString('hex')}.x` } }) }, // forged, bad signature
  { count: 50, make: () => ({ headers: { origin: ALLOWED } }) },                           // allowlisted origin
  { count: 50, make: () => ({ path: '/not-a-route' }) },                                   // 404 path
  { count: 25, make: () => ({ method: 'OPTIONS', headers: { origin: ALLOWED } }) },        // preflight-shaped
  { count: 50, make: () => ({ headers: { cookie: 'sid=' + encodeURIComponent('s:' + signature.sign(
    crypto.randomBytes(16).toString('hex'), process.env.SESSION_SECRET)) } }) },          // validly signed, no such session
  { count: 20, make: () => ({ method: 'HEAD' }) },
  { count: 20, make: () => ({ method: 'POST' }) },
];

function controlApp(options, write) {
  const app = express();
  app.use(session({ name: 'sid', secret: process.env.SESSION_SECRET, ...options }));
  app.get('/api/preferences', (req, res) => { if (write) req.session.touchedBy = 'control'; res.json({}); });
  return app;
}

(async () => {
  const results = [];
  for (const tls of [false, true]) {
    delete require.cache[require.resolve('./app.js')];
    const fixtureApp = require('./app.js');
    results.push(await run('fixture (unchanged)', fixtureApp, tls, plan));
  }
  const base = { resave: false, cookie: { httpOnly: true, secure: true, sameSite: 'lax', maxAge: 30 * 60 * 1000 } };
  results.push(await run('control: saveUninitialized true', controlApp({ ...base, saveUninitialized: true }, false), true,
                         [{ count: 50, make: () => ({}) }]));
  results.push(await run('control: a route writes the session', controlApp({ ...base, saveUninitialized: false }, true), true,
                         [{ count: 50, make: () => ({}) }]));
  console.log(JSON.stringify({ node: process.version, expressSession: require('express-session/package.json').version,
                               express: require('express/package.json').version, storesObserved: stores.length, results }, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
```
