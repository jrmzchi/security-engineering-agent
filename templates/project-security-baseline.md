# Project Security Baseline Template

Used with `plays/project-security-baseline.md`. Two parts: a compact
**Summary** (safe to load into most tasks) and the full **Facts** record
(machine-readable, loaded only when a specific fact is actually
relevant). Written to the *target repository being reviewed* under
`.security/`, not to this kit's own repository.

## Summary (`.security/README.md`)

```markdown
# Security Baseline Summary

Stack:
<languages/frameworks/runtime, one line>

Hosting:
<deployment OS/platform, or UNKNOWN>

Auth:
<authentication + authorization approach, one line>

Storage:
<database/ORM, one line>

Files:
<file storage approach, if any>

External services:
<outbound integrations, if any>

Last updated: <date> at commit <short SHA, or "no commits yet">

Relevant to current change:
<filled in per-task, not stored — e.g. "Authorization + File storage">
```

## Facts (`.security/baseline.json`)

```json
{
  "schemaVersion": 1,
  "updated": "2026-01-01T00:00:00Z",
  "gitCommit": "a1b2c3d-or-null",
  "facts": {
    "runtime": {
      "value": ".NET 8",
      "confidence": "HIGH",
      "source": "CODE_EVIDENCE",
      "evidence": [
        { "path": "MyApp.csproj", "observation": "TargetFramework net8.0" }
      ],
      "freshnessOf": ["MyApp.csproj"]
    },
    "framework": {
      "value": "ASP.NET Core MVC",
      "confidence": "HIGH",
      "source": "CODE_EVIDENCE",
      "evidence": [
        { "path": "Program.cs", "observation": "AddControllersWithViews" }
      ],
      "freshnessOf": ["Program.cs"]
    },
    "hosting": {
      "value": "UNKNOWN",
      "confidence": "UNKNOWN",
      "source": "NONE",
      "evidence": [],
      "freshnessOf": []
    },
    "authentication": {
      "value": "Cookie authentication",
      "confidence": "HIGH",
      "source": "CODE_EVIDENCE",
      "evidence": [
        { "path": "Program.cs", "observation": "AddAuthentication(...).AddCookie(...)" }
      ],
      "freshnessOf": ["Program.cs"]
    }
  }
}
```

Each entry under `facts` uses the same shape, plus an optional
`status` field (omitted when the fact is current — only add it when
current source evidence has contradicted the fact, with value
`"STALE"`; see the play's "Freshness and invalidation" section).
`freshnessOf` lists the evidence file(s) this fact depends on — when
one of them changes, re-evaluate only that fact. `hosting` above shows
the `UNKNOWN` case: no `evidence`, `source: "NONE"`, no guess,
`confidence: "UNKNOWN"` rather than inferring IIS from the framework
alone.

Additional fact keys follow the same shape as needed:
`authorization`, `database`, `orm`, `frontend`, `externalServices`,
`fileStorage`, `secretSources`, `backgroundJobs`, `adminSurfaces`,
`publicSurfaces`, `securityMiddleware`, `sensitiveData`. Add only the
keys a given project's evidence actually supports — do not pad the
schema with `UNKNOWN` placeholders for facts nobody asked about yet.
