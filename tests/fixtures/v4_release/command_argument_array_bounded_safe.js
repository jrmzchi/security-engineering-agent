// Fixture: external program run with an argument array (SAFE), V4 release corpus row RV-04 (corpus revision 3)
//
// Expected review outcome: NO confirmed finding. False-positive-avoidance
// counterpart to command_injection_unsafe.js -- a reviewer must not flag
// this just because request data influences an external program call.
//
// Why it's safe: execFile() without { shell: true } spawns no shell, so no
// value reaches a shell parser. Nothing the client sends is passed to
// ImageMagick as-is: the client names an asset KEY, looked up in a
// server-side Map of fixed, deployment-owned PNG files (an unknown key is a
// 404), and a size that must parse as an integer in a fixed range; the
// server formats the geometry string and fixes the output coder. The
// endpoint converts public assets only, so it needs no sign-in, and the
// work it can trigger is bounded in this file: at most MAX_CONCURRENT
// conversions at a time (429 otherwise), each with a timeout and an output
// size cap.
//
// Replaces tests/fixtures/command_injection_safe.js for the V4 release
// corpus (revision 2 used command_argument_array_allowlisted_safe.js, which
// had no concurrency bound). See tests/validation/v4-release-corpus.md.

const express = require('express');
const { execFile } = require('child_process');

const app = express();
app.use(express.json({ limit: '1kb' }));

const ASSETS = new Map([
  ['logo', '/srv/app/assets/logo.png'],
  ['banner', '/srv/app/assets/banner.png'],
  ['icon', '/srv/app/assets/icon.png'],
]);
const MIN_SIZE = 32;
const MAX_SIZE = 1024;
const MAX_CONCURRENT = 2;
let running = 0;

app.post('/thumbnails', (req, res) => {
  const source = ASSETS.get(String(req.body.asset));
  if (source === undefined) {
    return res.status(404).send('unknown asset');
  }
  const size = Number(req.body.size);
  if (!Number.isInteger(size) || size < MIN_SIZE || size > MAX_SIZE) {
    return res.status(400).send('size must be an integer between 32 and 1024');
  }
  if (running >= MAX_CONCURRENT) {
    return res.status(429).send('busy, retry later');
  }
  running += 1;
  execFile(
    'convert',
    [source, '-resize', `${size}x${size}`, 'png:-'],
    { encoding: 'buffer', maxBuffer: 8 * 1024 * 1024, timeout: 10000 },
    (err, stdout) => {
      running -= 1;
      if (err) return res.status(500).send('conversion failed');
      res.type('image/png').send(stdout);
    },
  );
});

module.exports = app;
