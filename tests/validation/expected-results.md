# Expected Results

One row per fixture in `tests/fixtures/`. See `tests/validation/README.md`
for how to run a pass and what "pass" means — in particular, read that
file's note on stripping each fixture's own header comment before
running a pass, so the "answer" isn't visible to the reviewer being
validated. `Trap being tested` is filled in only for the
`*_safe`/`*_example` fixtures where the risk is a specific, plausible
over-eager pattern match, for the `*_deceptive.cs` fixtures where it
names the apparent-but-invalid mitigation, and for the remediation
pair's after-state where the risk is a validator that re-tests only
the original payload.

| Fixture | Expected outcome | Category / CWE | Trap being tested |
|---|---|---|---|
| `sql_injection_unsafe.py` | CONFIRMED, HIGH/CRITICAL | SQL injection / CWE-89 | — |
| `sql_injection_safe.py` | No confirmed finding | — | reviewer flags any DB query touched by request data, regardless of parameterization |
| `command_injection_unsafe.js` | CONFIRMED, HIGH/CRITICAL | OS command injection / CWE-78 | — |
| `command_injection_safe.js` | No confirmed finding | — | reviewer flags any `child_process` call with request-derived input, regardless of `shell` usage |
| `path_traversal_unsafe.cs` | CONFIRMED, HIGH/CRITICAL | Path traversal / CWE-22 | — |
| `path_traversal_safe.cs` | No confirmed finding | — | reviewer flags any `Path.Combine` with a query parameter, ignoring the containment check that follows it |
| `xss_unsafe.js` | CONFIRMED, HIGH | XSS / CWE-79 | — |
| `xss_safe.js` | No confirmed finding | — | reviewer flags any DOM write from `location.search`, regardless of which sink is used |
| `idor_unsafe.cs` | CONFIRMED, HIGH | IDOR / BOLA / CWE-639 | — |
| `idor_safe.cs` | No confirmed finding | — | reviewer flags this just because the route takes an ID and the endpoint requires authentication, missing that an explicit object-level ownership check is also present |
| `hardcoded_secret_unsafe.py` | CONFIRMED, 2 findings (AWS key pair + database connection string) | Hardcoded credential / CWE-798 | — |
| `hardcoded_secret_example_value.py` | No confirmed finding (INFORMATIONAL at most) | — | reviewer flags any string shaped like an AWS key, ignoring the `EXAMPLE` marker and documented-placeholder context |
| `file_upload_unsafe.py` | CONFIRMED, HIGH/CRITICAL | Unrestricted upload + path traversal via filename / CWE-434 + CWE-22 | — |
| `file_upload_safe.py` | No confirmed finding | — | reviewer flags any file-upload endpoint regardless of validation/storage location/size limit |
| `csrf_samesite_lax_deceptive.cs` | CONFIRMED, HIGH | CSRF / CWE-352 | `SameSite=Lax` cookie config, presented as if it were sufficient — it does not cover top-level GET navigation |
| `upload_webroot_content_disposition_deceptive.cs` | CONFIRMED, HIGH | Unrestricted upload -> stored XSS on the app's own origin / CWE-434 + CWE-79 | `Content-Disposition: attachment` on the download endpoint, which never runs for a direct request to the uploaded file |
| `ef_fromsqlraw_vs_interpolated.cs` (`FindByNameUnsafe`) | CONFIRMED, HIGH/CRITICAL | SQL injection / CWE-89 | — |
| `ef_fromsqlraw_vs_interpolated.cs` (`FindByNameSafe`) | No confirmed finding | — | reviewer flags `FromSqlInterpolated` just because it "looks like" string interpolation |
| `ef_fromsqlraw_vs_interpolated.cs` (`FindByNameSafeRawWithParams`) | No confirmed finding | — | reviewer flags any `FromSqlRaw` call regardless of whether parameters are passed separately |
| `authorization_removed_unsafe.cs` | CONFIRMED, CRITICAL | Broken access control / CWE-284, CWE-862 | — |
| `authorization_preserved_safe.cs` | No confirmed finding | — | reviewer flags this just because it's an admin endpoint reachable via a diff that touched the file, missing that `[Authorize(Roles = "Admin")]` is unchanged |
| `cors_wildcard_credentials_unsafe.js` | CONFIRMED, HIGH | CORS misconfiguration / CWE-942 | — |
| `cors_restricted_safe.js` | No confirmed finding | — | reviewer flags any CORS middleware that sets `Access-Control-Allow-Credentials: true`, missing that the origin is checked against an explicit allowlist rather than reflected |
| `ssrf_user_url_unsafe.py` | CONFIRMED, HIGH/CRITICAL | SSRF / CWE-918 | — |
| `ssrf_allowlist_safe.py` | No confirmed finding | — | reviewer flags any outbound `requests.get` derived from user input, missing the host allowlist and resolved-IP check (the resolved-IP check is not a complete DNS-rebinding defense on its own — see the fixture's header comment — but does not change the expected outcome here) |
| `redirect_unvalidated_unsafe.cs` | CONFIRMED, MEDIUM/HIGH | Open redirect / CWE-601 | — |
| `redirect_local_safe.cs` | No confirmed finding | — | reviewer flags any `Redirect`-family call fed by a query parameter, missing that `LocalRedirect` + `Url.IsLocalUrl` reject non-local targets |
| `cookie_insecure_unsafe.js` | CONFIRMED, MEDIUM/HIGH | Insecure cookie / CWE-614, CWE-1004 | — |
| `cookie_secure_safe.js` | No confirmed finding | — | reviewer flags any `res.cookie` call, missing that `httpOnly`/`secure`/`sameSite` are all set |
| `remediation_fake_fix_before.py` | CONFIRMED, HIGH/CRITICAL | SQL injection / CWE-89 | — |
| `remediation_fake_fix_after_still_vulnerable.py` | Re-validation result: `STILL_VULNERABLE` (not `RESOLVED`) | SQL injection / CWE-89, unresolved | reviewer re-tests only the original literal payload (`' OR '1'='1`), sees it blocked, and incorrectly reports `RESOLVED` — see `plays/security-remediation.md`'s "Fake fix" section |

See also `tests/validation/classification-test-cases.md`,
`tests/validation/gate-test-cases.md`, and
`tests/validation/design-routing-test-cases.md` for the change-detection,
gate-policy, and security-design-routing test cases — those validate
different capabilities than the CONFIRMED/not-CONFIRMED table above and
are not duplicated here.

## Summary counts (for a quick pass/fail read)

```text
Must produce a CONFIRMED finding:      16  (7 *_unsafe fixtures from
                                             tests/fixtures/'s original
                                             batch + 2 *_deceptive.cs +
                                             1 unsafe method inside
                                             ef_fromsqlraw_vs_interpolated.cs
                                             + 5 *_unsafe.* fixtures
                                             added in this batch
                                             + remediation_fake_fix_before.py)
Must NOT produce a CONFIRMED finding:  14  (7 *_safe/*_example fixtures +
                                             2 safe methods inside
                                             ef_fromsqlraw_vs_interpolated.cs
                                             + 5 *_safe fixtures added in
                                             this batch)
Must resolve to STILL_VULNERABLE on
re-validation (not a CONFIRMED/not-
CONFIRMED case):                        1  (remediation_fake_fix_after_still_vulnerable.py)
```
