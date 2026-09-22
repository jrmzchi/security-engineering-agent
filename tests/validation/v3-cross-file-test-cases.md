# V3 Cross-File Test Cases

Validates `plays/cross-file-data-flow.md` and
`plays/adversarial-validation.md`'s canonicalization technique. See
`tests/validation/README.md`'s "Multi-file fixture group" validation
form — these fixtures must be handed to the reviewer being validated
as a full directory, never one file at a time.

## Cross-file vulnerability tracing

| # | Fixture group | Expected outcome | What must actually be traced |
|---|---|---|---|
| 1 | `tests/fixtures/cross_file_sql_unsafe/` | CONFIRMED, CRITICAL/HIGH SQL injection (CWE-89) | `UsersController.Search`'s `q` parameter -> `UserSearchService.SearchUsers` (no validation) -> `UserRepository.FindByNameLike`'s string-interpolated `SqlCommand`. A pass that confirms from `UserRepository.cs` alone, without citing the two intermediate hops, has not actually demonstrated the attack path per `plays/finding-validation.md`'s attack-path requirement. |
| 2 | `tests/fixtures/cross_file_sql_safe/` | No confirmed finding | The same 3-hop trace must be followed to `UserRepository.cs`, where `query` is bound via `SqlParameter` rather than concatenated — a reviewer that stops at "raw ADO.NET, 3 files, looks scary" without reaching the actual sink risks a false positive. |
| 3 | `tests/fixtures/cross_file_path_traversal_unsafe/` | CONFIRMED, HIGH/CRITICAL path traversal (CWE-22) | `DownloadController.Download`'s `reportName` (query string, not a route parameter — no ASP.NET Core route normalization applies) -> `FileService.GetReportBytes` (no validation) -> `PathHelper.ResolveReportPath`'s uncontained `Path.Combine`. |
| 4 | `tests/fixtures/cross_file_path_traversal_safe/` | No confirmed finding | Same 3-hop trace, reaching `PathHelper.cs`'s canonicalize-then-check containment logic. |
| 5 | `tests/fixtures/cross_file_object_authz_unsafe/` | CONFIRMED, HIGH IDOR/BOLA (CWE-639) | `ReportsController.GetReport`'s `[Authorize]` only confirms authentication -> `ReportService.GetReport` has no caller-identity parameter at all -> `ReportRepository.FindById` performs no ownership filtering. A reviewer that stops at "`[Authorize]` is present" without checking whether object-level ownership is enforced anywhere in the chain reproduces the exact miss `plays/authorization.md`'s "IDOR / BOLA" section exists to prevent — that section's three-question trace explicitly separates "is the caller authenticated?" from "is it checked that THIS caller owns THIS object?" |
| 6 | `tests/fixtures/cross_file_object_authz_safe/` | No confirmed finding | Same 3-hop trace, reaching `ReportService.cs`'s explicit `report.OwnerUserId != currentUserId` check — and confirming `reportId`'s sequential nature does NOT by itself justify a finding (see `plays/authorization.md`'s severity-amplifier note). |

## Adversarial canonicalization pair

| # | Fixture | Expected outcome | Expected `adversarialValidation` result | What the checklist must find |
|---|---|---|---|---|
| 7 | `tests/fixtures/path_prefix_before_canonicalization_deceptive.cs` | CONFIRMED, HIGH/CRITICAL path traversal | `BYPASS_FOUND` (technique 6: encoding/canonicalization differences) | The `StartsWith` containment check runs against the *uncanonicalized* combined path — `Path.Combine("/var/app/reports", "../../../../etc/passwd")` still starts with `/var/app/reports` as a literal string, even though it resolves outside that directory once opened. A reviewer that sees the containment check and stops, without checking *what value* it runs against, will incorrectly clear this as safe. |
| 8 | `tests/fixtures/path_prefix_after_canonicalization_safe.cs` | No confirmed finding | `CONTROL_HOLDS` — **not** `BYPASS_FOUND` | Structurally the same shape as case 7 (a `StartsWith` check on a combined path), but this one canonicalizes with `Path.GetFullPath` first. Case 8 exists specifically so this checklist has a negative case: applying the same techniques here and reporting a bypass anyway would be a fabricated finding. |

Cases 7 and 8 are deliberately structured as a matched pair — run them
back to back. A validation pass that gets case 7 right but also flags
case 8 has not learned to distinguish a real bypass from a
superficially similar but actually-sound control; that is a failure
mode as serious as missing case 7 outright — see
`plays/adversarial-validation.md`'s "A different objective from
ordinary validation, not more of the same" section, which frames this
checklist as reducing false negatives without becoming a source of
false positives of its own.
