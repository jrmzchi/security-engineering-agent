// Fixture: OS command injection (VULNERABLE)
//
// Expected review outcome: CONFIRMED HIGH/CRITICAL command injection
// (CWE-78). See plays/code-review.md's injection section and
// references/node-security.md.
//
// Attack path: `filename` is attacker-controlled (request body),
// reaches exec() concatenated into a shell-interpreted command string,
// and changes the command's structure (e.g. via `; rm -rf /` or `&&`).

const express = require('express');
const { exec } = require('child_process');
const app = express();

app.use(express.json());

app.post('/convert', (req, res) => {
  const filename = req.body.filename;
  // VULNERABLE: exec() spawns a shell and interprets metacharacters;
  // the filename is concatenated directly into the command string.
  exec(`convert ${filename} output.png`, (err, stdout) => {
    if (err) return res.status(500).send('conversion failed');
    res.send('done');
  });
});

module.exports = app;
