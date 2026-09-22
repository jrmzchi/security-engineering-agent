# Play: Repository Consistency Check

Authoritative procedure for `scripts/windows/consistency-check.ps1` /
`scripts/macos/consistency-check.sh`. A lightweight, mechanical recall
tool for this kit's own Markdown — not a semantic security engine, and
not part of `skills/security-review`'s scanner lineup (it does not
scan a target repository's source code; it scans *this kit's own*
`plays/`/`skills/`/`templates/`/`tests/` for the specific failure mode
that caused repeated review rounds during V3's development: the same
concept stated in multiple files, one file updated, another forgotten.

## Tool = recall, Agent/human = judgment

The tool answers *"where should I look?"* — it does not, and must not
be made to, answer *"are these two natural-language security rules
semantically identical?"* Every hit is a candidate for review, not a
finding in its own right. Do not treat a clean run (`PASS`) as proof
of consistency, and do not treat every hit as something that must be
fixed — see "Interpreting output" below for the judgment step this
tool does not perform.

## Categories

```text
STALE_TERM         a phrase that has historically meant "this
                   wiring/fact isn't finished yet" — flagged wherever
                   it appears, since it may now be describing
                   something that actually IS finished
VOCABULARY         a specific term appearing in a context it has
                   historically been misused in (e.g. a finding-only
                   status word applied to an object that doesn't carry
                   that status) — NOT a general search for every
                   occurrence of a status word
BROKEN_REFERENCE   a backtick-quoted file path that does not exist in
                   this repository
HYGIENE            an accidentally-tracked generated artifact
                   (__pycache__, *.pyc, unexpected output/scans or
                   output/reports content, temp files) not covered by
                   .gitignore
```

`DEPRECATED_PATTERN` and `TODO_REVIEW` are reserved, optional
categories for future use — do not populate either speculatively; add
a pattern only once a real instance of that failure mode has actually
occurred (see "No duplicated pattern lists" below for why this
matters more here than it would for an ordinary lint rule).

## No duplicated pattern lists

`STALE_TERM` and `VOCABULARY` patterns live in exactly one place:
`tools/consistency-patterns.txt`. Both scripts parse that same file at
runtime — neither hard-codes an equivalent pattern list of its own.
This is deliberate: a pattern list is exactly the kind of "same fact
in two places" this tool exists to prevent recurrences of, and it
would be self-defeating for the tool itself to violate that principle.
`BROKEN_REFERENCE` and `HYGIENE` are structural checks (path
existence, filename globs) rather than a pattern list, so each script
implements that logic directly — there is nothing to factor out.

## Seeding STALE_TERM / VOCABULARY

Every pattern currently in `tools/consistency-patterns.txt` was lifted
from an actual defect found and fixed during this kit's own V3
integration work — not invented speculatively (see that file's own
header for the discipline this follows, and
`plays/adversarial-validation.md`'s "Why this is safe" for the kind of
review history a `VOCABULARY` pattern typically encodes). When a
review finds a new instance of "the same concept, stated twice,
drifted apart," add the pattern that would have caught it, phrased
generally enough to catch the next instance of the same shape — not so
generally that it produces mostly noise (see "Interpreting output"
below on why over-broad patterns cost more than they save).

## Running it

```powershell
.\scripts\windows\consistency-check.ps1
```

```bash
./scripts/macos/consistency-check.sh
```

Both scan this kit's own repository (not a target repository under
review) — there is no `-Path`/`--path` override, since this tool's
entire purpose is checking *this kit's* internal consistency. Run it
before finalizing a batch of work that touches multiple
`plays/`/`skills/`/`templates/` files together, the same discipline a
manual full-repository grep sweep already applied by hand during V3's
own development — this tool does not replace the judgment that sweep
required, it gives it a starting point that does not depend on
remembering to grep for the right phrase each time.

## Output

```text
Repository Consistency Check

STALE_TERM
  skills/example/SKILL.md:42
  "not yet wired..."

VOCABULARY
  templates/security-report.md:81
  "CONFIRMED attack chain"

BROKEN_REFERENCE
  plays/example.md:20
  "../references/missing.md"

HYGIENE
  tests/fixtures/__pycache__/example.pyc

Result:
REVIEW_REQUIRED
```

`Result: PASS` when nothing is found. Only actionable hits are
printed — a `STALE_TERM`/`VOCABULARY` pattern with zero matches
produces no output for that category, not an empty section.

## Exit codes

```text
0   PASS            no mechanically actionable hit
1   REVIEW_REQUIRED  one or more hits — needs a human/agent judgment
                     pass, not necessarily a fix (see "Interpreting
                     output" below)
2   ERROR            the checker itself failed to run (missing
                     tools/consistency-patterns.txt, malformed pattern
                     line, filesystem error) — distinct from "ran
                     cleanly and found nothing"
```

Do not treat exit code 1 as a CI failure in the same sense as a failed
test — see "Interpreting output."

## Interpreting output

A hit is a place to look, not a confirmed defect:

```text
STALE_TERM hit   -> read the surrounding sentence; is the described
                   thing actually still unwired, or has a later batch
                   since wired it up (making this hit real) — or is
                   this occurrence itself the disclosure that a
                   DIFFERENT, still-genuinely-unwired thing exists
                   (making this hit a false positive)?
VOCABULARY hit   -> read the surrounding sentence; is the term used in
                   the specific misleading way the pattern was seeded
                   from, or in an unrelated, correct sense (e.g. a
                   Nit's own catalogue of past mistakes, like this
                   play's own examples above, will legitimately match
                   STALE_TERM/VOCABULARY patterns without being an
                   instance of the mistake itself)
BROKEN_REFERENCE
  hit             -> confirm the path really doesn't exist (a typo'd
                   extension, wrong relative depth) versus a
                   deliberate negated reference ("there is no separate
                   agents/X.md for this capability" — several
                   `integrations/claude/agents/*.md` wrappers say
                   exactly this on purpose); do not "fix" one by
                   creating the named file just to make the reference
                   resolve
HYGIENE hit      -> confirm it's actually a generated artifact before
                   deleting anything — investigate what created it
                   rather than assuming; an unfamiliar file may be
                   someone's in-progress work, not a build byproduct
```

A pattern whose hits are mostly false positives (the interpretation
step above rejects most of them) has a bad signal-to-noise ratio and
should be narrowed or removed — this is the same "false positives
undermine the tool" principle any deterministic scanner in this kit is
held to (see `plays/finding-validation.md`'s coverage-gap handling for scanner
output generally).

## What this tool deliberately does not do

No LLM call, no semantic-equivalence judgment, and deliberately no
gate-policy parser that tries to convert `plays/security-gate.md` into
executable logic — a machine-readable second representation of an
authoritative play is itself a new place for truth to drift, and it
would protect only that one play. An LLM-backed consistency script
would be worse: that is just another review pass hidden behind a
script, not a mechanical recall tool, and it reintroduces exactly the
"another place truth can drift" problem this tool exists to reduce.
This tool's entire value is being simple enough that its own logic
does not need the same scrutiny as the things it checks.
