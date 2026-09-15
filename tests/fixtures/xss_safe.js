// Fixture: Reflected XSS (SAFE — text-only sink)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to xss_unsafe.js — a reviewer must not flag
// this just because attacker-controlled input reaches the DOM.
//
// Why it's safe: textContent sets the node's text, not its HTML — the
// browser never parses the value as markup, so it cannot execute as
// script regardless of what characters it contains.

function renderGreeting() {
  const params = new URLSearchParams(window.location.search);
  const name = params.get('name') || 'guest';
  const el = document.getElementById('greeting');
  // SAFE: textContent does not parse HTML.
  el.textContent = 'Welcome, ' + name + '!';
}

document.addEventListener('DOMContentLoaded', renderGreeting);
