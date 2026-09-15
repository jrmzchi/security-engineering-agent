# Reference: JavaScript Security (Language-Level)

Language-level JavaScript/TypeScript concerns that apply regardless of
runtime (browser or Node). See `references/node-security.md` for
Node-specific server-side concerns and `references/browser-security.md`
for browser/DOM-specific concerns.

## eval / Function constructor

```javascript
// Unsafe: constructing executable code from a string built with
// attacker-influenced input
eval(userInput);
new Function(userInput)();

// Safe: JSON.parse for data, no dynamic code construction
JSON.parse(userInput);
```

The string form of `setTimeout`/`setInterval` (`setTimeout(userInput,
100)`) is also an eval-like sink in browsers specifically — see
`references/browser-security.md`. Node's `timers` implementation does
not accept a string callback at all (it throws), so this is not a
cross-runtime concern the way `eval`/`Function` are.

`eval`/`Function` existing in a codebase is not itself a vulnerability
(see `plays/code-review.md`'s "dangerous pattern ≠ vulnerability") — many
uses are on fixed, developer-authored strings. The finding is
attacker-influenced data reaching the string that gets evaluated.

## Prototype pollution (CWE-1321)

```javascript
// Vulnerable pattern: recursive merge/clone of attacker-controlled
// objects without excluding __proto__ / constructor / prototype keys
function merge(target, source) {
  for (const key in source) {
    if (typeof source[key] === 'object') {
      merge(target[key] ??= {}, source[key]);
    } else {
      target[key] = source[key];
    }
  }
}
merge({}, JSON.parse(attackerControlledJson));
// if attackerControlledJson is {"__proto__": {"isAdmin": true}},
// this can pollute Object.prototype for every object in the process
```

Look for this in: hand-rolled deep-merge/clone utilities, JSON-schema
validators/config mergers, and older versions of popular utility
libraries (some historical CVEs in merge/extend/clone utilities in
widely-used npm packages were exactly this pattern — check the
dependency's version against known advisories per
`plays/dependency-security.md` rather than assuming a well-known library
name means it is safe).

**Impact** depends entirely on what the polluted prototype property is
later read by — it can range from a denial-of-service (unexpected
property breaks a null-check elsewhere) to authorization bypass (a
polluted `isAdmin`/`role` default read by later code) to, in some
frameworks, remote code execution via a gadget chain. Do not assume
maximum impact without tracing what actually consumes the polluted
property.

**Safe pattern:** validate/sanitize keys before merging (reject
`__proto__`, `constructor`, `prototype`), use `Object.create(null)` for
objects meant to be plain key-value maps, or use `structuredClone`/a
merge utility with documented prototype-pollution protection and a
current, patched version.

## Insecure serialization

`JSON.parse`/`JSON.stringify` do not execute code and are generally safe
for untrusted input. The risk in JS is almost always at the "what do I do
with the parsed object" step (prototype pollution above, or using a
parsed value as a template/eval input) rather than the parse itself.
