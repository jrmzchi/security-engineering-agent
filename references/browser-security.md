# Reference: Browser Security

Browser/DOM-specific concerns backing `plays/web-security.md`. See
`references/javascript-security.md` for language-level concerns (eval,
prototype pollution) that apply here too.

## DOM sinks

```javascript
// Unsafe: attacker-controlled data reaching an HTML-parsing sink
el.innerHTML = userInput;
el.outerHTML = userInput;
el.insertAdjacentHTML('beforeend', userInput);
document.write(userInput);

// Safe: text-only sinks do not parse HTML
el.textContent = userInput;
el.innerText = userInput;
```

React: `dangerouslySetInnerHTML={{ __html: userInput }}` is the
equivalent unsafe sink — JSX text nodes (`<div>{userInput}</div>`) escape
automatically and are safe.

Angular: `[innerHTML]` binding sanitizes by default; calling
`bypassSecurityTrustHtml()` on attacker-influenced content defeats that
sanitization and is the actual unsafe sink.

Vue: `v-html` is the unsafe sink; `{{ }}` interpolation is escaped and
safe.

The string form of `setTimeout`/`setInterval` is also an eval-like sink
in browsers: `setTimeout(userInput, 100)` executes `userInput` as code
when it is a string (this is browser-specific — see
`references/javascript-security.md`). Passing an actual function
reference (`setTimeout(() => handle(userInput), 100)`) is the safe form
regardless of what `userInput` contains, since it is then treated as
data, not code.

## postMessage

See `plays/web-security.md`'s "Unsafe postMessage" section for the
receive/send analysis. Example of the safe pattern for both sides:

```javascript
// Receiving: check origin AND validate shape before acting
window.addEventListener('message', (event) => {
  if (event.origin !== 'https://trusted.example.com') return;
  if (typeof event.data !== 'object' || event.data.type !== 'expected-type') return;
  handle(event.data);
});

// Sending: explicit target origin, not '*', especially for sensitive data
targetWindow.postMessage(sessionData, 'https://trusted.example.com');
```

## localStorage / sessionStorage

```text
Storing session tokens, auth tokens, or PII in localStorage/sessionStorage
    -> readable by ANY script running in that origin, including one
    injected via an XSS vulnerability elsewhere on the same origin
    (unlike an HttpOnly cookie, which JavaScript cannot read at all).
    This does not create XSS by itself, but it means a single XSS bug
    anywhere on the origin can steal the token directly — it removes a
    layer of defense-in-depth that an HttpOnly cookie would have
    provided.
No data classification at all — treating localStorage as a general
    key-value store without considering that any origin-scoped script
    can read every key in it
```

Prefer `HttpOnly` cookies for session/auth tokens where the architecture
allows it (traditional server-rendered or same-origin API apps). For SPA/
cross-origin API architectures that need the token accessible to
JavaScript for `Authorization` headers, treat localStorage token storage
as an accepted risk that raises the severity of any XSS finding
elsewhere on the same origin — note this connection explicitly when both
are present.

## Cookies (browser-side view)

See `plays/configuration-security.md`'s "Insecure cookies" and
`plays/authentication.md`'s "Session hijacking" for the flag-level
checks (`Secure`/`HttpOnly`/`SameSite`). From the browser side
specifically: a cookie set without `HttpOnly` is readable by
`document.cookie` from any script on the page, same exposure as
localStorage above. For the `SameSite` flag's role in CSRF specifically
(and why `Lax` does not protect a state-changing GET endpoint), see
`plays/web-security.md`'s "CSRF" section directly.

## URL parsing and redirects

```javascript
// Unsafe: naive prefix check that can be bypassed
if (url.startsWith('https://trusted.example.com')) { location.href = url; }
// bypassed by: https://trusted.example.com.attacker.com/

// Safer: parse, check the actual host, and navigate using the PARSED
// value — not the original string (checking parsed but navigating with
// the raw input reopens the same class of parser-differential bypass)
const parsed = new URL(url, location.origin);
if (parsed.origin === 'https://trusted.example.com') { location.href = parsed.href; }
```

See `plays/web-security.md`'s "Open redirect" section.

## CSP

```html
<!-- Weak: unsafe-inline/unsafe-eval defeat most of CSP's XSS mitigation -->
<meta http-equiv="Content-Security-Policy"
      content="script-src 'self' 'unsafe-inline' 'unsafe-eval'">

<!-- Stronger: nonce- or hash-based, no unsafe-inline/eval -->
<meta http-equiv="Content-Security-Policy"
      content="script-src 'self' 'nonce-{random-per-response}'">
```

```text
Content-Security-Policy: script-src 'self' 'nonce-{random-per-response}'; frame-ancestors 'none'
```

**`frame-ancestors` (and `report-uri`/`report-to`, and `sandbox`) only take
effect when CSP is delivered as an HTTP response header.** A CSP set via
`<meta http-equiv>` silently ignores these directives per the CSP spec —
a page relying on `<meta>` for clickjacking protection has no protection
at all. Neither does `X-Frame-Options` work via `<meta>` — like
`frame-ancestors`, it is only honored as a response header. If a `<meta>`
CSP is all a page has, treat clickjacking as unmitigated for that page
and flag it (see `plays/web-security.md`'s "Clickjacking" section) —
the fix is to set the header at the web server, reverse proxy, or CDN
layer, not in page markup.

## CORS (browser-side implication)

The browser enforces CORS on the requesting page's side; the actual
policy is set server-side (see `references/aspnet-security.md` /
`references/node-security.md` for the framework-level configuration).
From the browser/application code side, check that `fetch`/`XHR` calls
do not disable credentials-mode assumptions in a way that masks a
server-side CORS misconfiguration during testing.
