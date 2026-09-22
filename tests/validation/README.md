# Validation

This is not an executable test suite in the traditional sense — there
is no fixed algorithm to assert against. This kit's correctness depends
on an AI agent's semantic judgment (following `skills/security-review`
and `plays/*.md`), so "does it work" has to be checked by actually
running a review against the fixtures below and comparing the result to
`expected-results.md`.

## How to run a validation pass

1. Point `skills/security-review` at `tests/fixtures/` — treat it as
   the repository under review (a QUICK or STANDARD review is
   sufficient; these are small, isolated files, not a real project).
2. For each fixture, record what the review produced: no finding, or a
   finding with its severity/confidence and CONFIRMED/REJECTED/NEEDS
   VERIFICATION status.
3. Compare against `expected-results.md`.
4. Where the result does not match, that is itself the finding — it
   means a play, reference, or skill needs a correction, the same way
   the code-reviewer passes during this kit's own construction found
   and fixed real gaps (see the `*_deceptive.cs` fixtures' comments for
   two examples of exactly that).

## What "pass" means

```text
*_unsafe.* / *_deceptive.cs   -> must produce a CONFIRMED finding of
                                 the expected category. A miss here is
                                 a false negative - the more serious
                                 failure mode, since it means a real
                                 vulnerability shape would slip through
                                 silently.

*_safe.* / hardcoded_secret_example_value.py
                               -> must NOT produce a CONFIRMED finding.
                                 A miss here is a false positive - see
                                 plays/finding-validation.md's
                                 confidence model; a LOW-confidence or
                                 NEEDS_VERIFICATION note is acceptable,
                                 an incorrectly CONFIRMED finding is not.
```

The two `*_deceptive.cs` fixtures specifically exercise the asymmetry
noted during this kit's construction: it is easy to build a system that
never false-positives by being too willing to accept an apparent
mitigation at face value. Each presents something that looks like a
valid control (`SameSite=Lax`, a `Content-Disposition` header) but is
not, for the specific attack path shown. A reviewer that is fooled by
the apparent mitigation has the same practical effect as a false
negative and should be treated as a validation failure.

## Validation forms

Most of `tests/fixtures/` is validated the static-single-file way
described above, but three kinds of fixture/document need a different
procedure:

```text
Static single file (*_unsafe / *_safe / *_deceptive.cs)
  -> "What 'pass' means" above.

Diff pair (authorization_removed_unsafe.cs /
           authorization_preserved_safe.cs)
  -> Present the pair as a DIFF, not two static files: the "unsafe"
     member's [Authorize] attribute removed relative to the "safe"
     member, in the form a reviewer would actually see it (a unified
     diff, or "here is the before and after"). Pass = CONFIRMED on the
     removal; a reviewer handed only the static "unsafe" file with no
     diff context has not actually been validated for diff-awareness,
     even if it happens to flag the file (see
     plays/authorization.md's missing-function-authorization and
     default-allow sections, which are sufficient to flag this file on
     its own merits regardless of diff framing).

Remediation pair (remediation_fake_fix_before.py /
                   remediation_fake_fix_after_still_vulnerable.py)
  -> Feed both files to the validator role per
     plays/security-remediation.md's "Independent re-validation"
     section: the "before" file's finding is the original CONFIRMED
     SQL injection; the "after" file is the claimed fix. Pass =
     re-validation reports STILL_VULNERABLE (per
     plays/security-remediation.md's re-validation outcomes) using a
     payload other than the one the fake fix blocklists, not RESOLVED.

Text-case lookup tables (classification-test-cases.md,
                          gate-test-cases.md,
                          design-routing-test-cases.md)
  -> No code review involved. For each row, look up the answer in the
     cited authoritative play/skill (plays/security-change-detection.md,
     plays/security-gate.md, skills/security-design's activation list)
     and compare to the table's "expected" column. Pass = the table's
     answer is what the play/skill itself yields. A mismatch means
     either the table or the play needs correcting — same principle as
     "Where the result does not match" above, just applied to a
     document instead of a code fixture.

Multi-file fixture group (a directory under tests/fixtures/ holding
                           several files that only demonstrate the
                           vulnerability/safety claim together, e.g.
                           cross_file_sql_unsafe/'s Controller +
                           Service + Repository)
  -> Hand the reviewer being validated ALL files in the directory at
     once, as they would encounter a real multi-file codebase — never
     one file from the group in isolation (a single file like
     cross_file_sql_unsafe/UsersController.cs shows no vulnerability
     at all on its own; per plays/cross-file-data-flow.md, the point is
     exactly that the reviewer must trace across the file boundary).
     Pass = CONFIRMED (for an `_unsafe` group) or no confirmed finding
     (for a `_safe` group) on the full group, citing the actual
     cross-file path. Getting the *right* answer by examining only one
     file in the group (e.g. flagging the Repository's SQL sink
     without tracing that `query` is attacker-controlled) is not a
     pass — see plays/finding-validation.md's attack-path requirement,
     which this form exists to validate wasn't skipped.
```

## Running a fixture "blind"

A handful of fixtures — `hardcoded_secret_unsafe.py` in particular —
rely on a distinction (a real value vs. an officially-documented
placeholder) that a reviewer should reach by examining the value
itself, not by reading this fixture's own header comment explaining
what the expected answer is. When actually running a validation pass,
strip each fixture's leading comment block (or copy just the code below
it) before handing the file to the reviewer being validated, so the
pass measures the reviewer's judgment rather than its ability to read
the answer key.

## Fixture format

Every fixture starts with a comment block stating the expected outcome
and, for `*_unsafe`/`*_deceptive` fixtures, the attack path. This is
there so the validation pass has a written prediction to check the
actual review output against — not so a reviewer can just read the
comment and "know the answer" (a real review of unknown code has no
such comment; a reviewer that only performs correctly when told the
answer in advance has not actually validated anything).

## Adding a fixture

New fixture pairs are welcome as this kit's coverage grows — follow the
existing naming convention (`<category>_unsafe.<ext>` /
`<category>_safe.<ext>`, `<category>_deceptive.<ext>` for a
false-negative-avoidance case, `<category>_before.<ext>` /
`<category>_after_<outcome>.<ext>` for a remediation pair, or
`<category>_unsafe`/`<category>_safe` as a directory holding several
files for a cross-file case — see "Validation forms" above), add the
comment block describing the expected outcome and why, and add a row
to `expected-results.md`. If the new fixture doesn't fit the static
single-file validation form, add its procedure to "Validation forms"
above.
