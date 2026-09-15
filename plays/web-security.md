# Play: Web / Browser Security

Authoritative procedure for browser-side vulnerability classes. See
`references/browser-security.md` for concrete safe/unsafe code shapes.

## Scope

```text
XSS (reflected, stored, DOM-based)
CSRF
Clickjacking
Unsafe postMessage
Open redirect
CORS misconfiguration
CSP weaknesses
Unsafe DOM operations
```

## XSS (CWE-79)

Trace attacker-controlled data to an HTML/DOM sink:

```text
innerHTML / outerHTML / insertAdjacentHTML
document.write
eval / new Function on strings built from input
React dangerouslySetInnerHTML
Angular [innerHTML] with bypassSecurityTrust*
Razor Html.Raw
```

**Do not report XSS unless attacker-controlled data can realistically
reach an executable DOM/HTML context without adequate encoding or
sanitization.** A value that is only ever rendered through a framework's
default auto-escaping text binding (JSX text nodes, Razor `@value`,
Angular interpolation `{{ }}`, Vue `{{ }}`) is not XSS — that is exactly
what those bindings are for.

Reflected vs. stored vs. DOM-based changes the attack path's entry point
(request parameter vs. persisted data vs. client-side script reading
`location`/`document.referrer`/etc.) but not the sink analysis.

## CSRF (CWE-352)

Check for state-changing requests (non-GET, or GET with side effects —
itself a smell) that rely only on ambient credentials (cookies) without
an anti-forgery token, a `SameSite=Strict` cookie, or a custom-header
requirement that a cross-site form cannot set. Framework anti-forgery
(ASP.NET `[ValidateAntiForgeryToken]`, Django's CSRF middleware) is a real
control — verify it is actually applied to the relevant endpoints, not
just present somewhere in the codebase.

**`SameSite=Lax` does not protect a state-changing GET endpoint.** Lax
still attaches cookies to a top-level cross-site GET navigation (e.g. an
attacker page setting `window.location = 'https://victim/account/delete?confirm=1'`).
If an endpoint has side effects on GET, `SameSite=Lax` alone is not a
CSRF control for it — treat it the same as a `SameSite=None` cookie for
that endpoint and require an anti-forgery token or convert the endpoint
to a non-GET method. `SameSite=Lax` is only an adequate control for
requests that are exclusively non-GET.

## Clickjacking (CWE-1021)

Check for `X-Frame-Options` or a CSP `frame-ancestors` directive on
pages that perform sensitive actions. Absence matters most on pages that
take a single click/action (e.g. "confirm purchase", "authorize").

## Unsafe postMessage

This has two independent sides — check both; a fix on only one side
leaves the other exploitable.

**Receiving.** Check every `window.addEventListener('message', ...)`
handler:

```text
Does it check event.origin against an explicit allowlist?
Does it validate the shape/type of event.data before acting on it?
```

A handler that acts on `event.data` without an origin check can be
triggered by any page that gets the victim to load it in a frame/window.

**Sending.** Check every `postMessage(data, targetOrigin)` call:

```text
Is targetOrigin a wildcard '*' while data contains a session token,
    auth code, PII, or anything else sensitive?
```

`postMessage(data, '*')` delivers `data` to whatever origin the target
window/iframe currently has — including an origin the target navigated
to after the reference was obtained, or a malicious third-party widget
embedded alongside it. Sensitive payloads must use an explicit target
origin, not `'*'`.

## Open redirect (CWE-601)

Any redirect target derived from user input (query param, referrer,
stored profile field) should be validated against an allowlist of hosts
or restricted to a relative path. This becomes higher-impact when chained
with OAuth flows (redirect_uri) or phishing.

## CORS misconfiguration

```text
Access-Control-Allow-Origin: * combined with Access-Control-Allow-Credentials: true
    -> invalid per spec in most implementations, but check for a
       reflected-origin implementation that effectively achieves the same

Origin reflected from the request without an allowlist check
    -> any origin can make credentialed requests
```

## CSP weaknesses

```text
unsafe-inline / unsafe-eval in script-src
    -> defeats most of CSP's XSS mitigation value
missing frame-ancestors
    -> no clickjacking protection from CSP
overly broad script-src (e.g. a wildcard subdomain you don't fully control)
```

CSP absence is not itself a vulnerability (it is defense-in-depth) — do
not report "missing CSP" as a standalone finding at the same severity as
an actual injection; note it as a hardening recommendation unless it is
the only thing standing between a real injection point and impact.
