// Fixture: OS command injection (SAFE — argument array, no shell)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to command_injection_unsafe.js — a reviewer
// must not flag this just because it invokes an external program with
// request-derived input.
//
// Why it's safe: execFile() without { shell: true } does not spawn a
// shell — `filename` is passed as a literal argument, so shell
// metacharacters inside it have no special meaning. This fixture's
// scope is specifically shell/command injection (CWE-78). It does NOT
// demonstrate that `filename` is safe to pass to ImageMagick as a
// value — ImageMagick's own coder-prefix syntax (e.g. a filename like
// "https://internal/..." or "text:/etc/passwd") is a separate,
// ImageMagick-specific risk (SSRF / arbitrary file read) that a real
// review should still check for; it is out of scope here.

const express = require('express');
const { execFile } = require('child_process');
const app = express();

app.use(express.json());

app.post('/convert', (req, res) => {
  const filename = req.body.filename;
  // SAFE: argument array, no shell involved.
  execFile('convert', [filename, 'output.png'], (err, stdout) => {
    if (err) return res.status(500).send('conversion failed');
    res.send('done');
  });
});

module.exports = app;
