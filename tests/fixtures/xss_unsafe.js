// Fixture: Reflected XSS (VULNERABLE)
//
// Expected review outcome: CONFIRMED HIGH XSS (CWE-79). See
// plays/web-security.md and references/browser-security.md.
//
// Attack path: `name` is attacker-controlled (URL query string),
// reaches innerHTML unescaped, and executes as HTML/script in the
// victim's browser — a URL like ?name=<img src=x onerror=alert(1)>
// runs attacker JavaScript in the page's origin.

function renderGreeting() {
  const params = new URLSearchParams(window.location.search);
  const name = params.get('name') || 'guest';
  const el = document.getElementById('greeting');
  // VULNERABLE: innerHTML parses the string as HTML.
  el.innerHTML = 'Welcome, ' + name + '!';
}

document.addEventListener('DOMContentLoaded', renderGreeting);
