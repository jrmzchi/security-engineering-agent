# Attack Surface Map Template

Used with `plays/attack-surface-mapping.md`. Written to
`.security/attack-surface.json` in the **target repository being
reviewed** — not to this kit's own repository. Node/edge type
vocabulary, ID prefixes, and field meanings are fixed by that play;
this file shows exactly the same worked examples in their persisted
JSON form.

```json
{
  "schemaVersion": 1,
  "updated": "2026-01-01T00:00:00Z",
  "gitCommit": "a1b2c3d-or-null",
  "nodes": [
    {
      "id": "TB-001",
      "type": "TRUST_BOUNDARY",
      "label": "Internet -> authenticated app",
      "evidence": {
        "path": "Program.cs",
        "symbol": "(none)",
        "observation": "app.UseAuthentication() runs before endpoint routing middleware; everything reachable after it requires passing through authentication"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Program.cs"]
    },
    {
      "id": "AS-AUTHN-001",
      "type": "AUTHENTICATION_CONTROL",
      "label": "Cookie authentication",
      "evidence": {
        "path": "Program.cs",
        "symbol": "(none)",
        "observation": "AddAuthentication(...).AddCookie(...)"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Program.cs"]
    },
    {
      "id": "AS-ENTRY-001",
      "type": "ENTRY_POINT",
      "label": "GET /files/{id}/download",
      "evidence": {
        "path": "Controllers/FilesController.cs",
        "symbol": "Download",
        "observation": "[HttpGet(\"{id}/download\")]"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/FilesController.cs"]
    },
    {
      "id": "AS-AUTHZ-001",
      "type": "AUTHORIZATION_CONTROL",
      "label": "Object-level file ownership check",
      "evidence": {
        "path": "Controllers/FilesController.cs",
        "symbol": "Download",
        "observation": "if (file.OwnerId != currentUser.Id) return Forbid();"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/FilesController.cs"]
    },
    {
      "id": "AS-SVC-001",
      "type": "SERVICE",
      "label": "FilesController.Download",
      "evidence": {
        "path": "Controllers/FilesController.cs",
        "symbol": "Download",
        "observation": "action method body"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/FilesController.cs"]
    },
    {
      "id": "AS-SVC-002",
      "type": "SERVICE",
      "label": "FileService.Resolve",
      "evidence": {
        "path": "Services/FileService.cs",
        "symbol": "Resolve",
        "observation": "method body"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Services/FileService.cs"]
    },
    {
      "id": "AS-FS-001",
      "type": "FILESYSTEM",
      "label": "Uploaded-files store",
      "evidence": {
        "path": "Services/FileService.cs",
        "symbol": "Resolve",
        "observation": "Path.Combine(_uploadRoot, storedFileName)"
      },
      "confidence": "HIGH",
      "tags": ["SENSITIVE_SINK"],
      "freshnessOf": ["Services/FileService.cs"]
    },
    {
      "id": "AS-AUTHZ-002",
      "type": "AUTHORIZATION_CONTROL",
      "label": "Admin-role policy check",
      "evidence": {
        "path": "Controllers/AdminController.cs",
        "symbol": "DisableUser",
        "observation": "[Authorize(Policy = \"AdminOnly\")]"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/AdminController.cs"]
    },
    {
      "id": "AS-ENTRY-002",
      "type": "ENTRY_POINT",
      "label": "POST /api/admin/users/{id}/disable",
      "evidence": {
        "path": "Controllers/AdminController.cs",
        "symbol": "DisableUser",
        "observation": "[HttpPost(\"users/{id}/disable\")]"
      },
      "confidence": "HIGH",
      "tags": ["ADMIN_SURFACE"],
      "freshnessOf": ["Controllers/AdminController.cs"]
    },
    {
      "id": "AS-SVC-003",
      "type": "SERVICE",
      "label": "AdminController.DisableUser",
      "evidence": {
        "path": "Controllers/AdminController.cs",
        "symbol": "DisableUser",
        "observation": "action method body"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/AdminController.cs"]
    },
    {
      "id": "AS-SVC-004",
      "type": "SERVICE",
      "label": "UserService.Disable",
      "evidence": {
        "path": "Services/UserService.cs",
        "symbol": "Disable",
        "observation": "method body"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Services/UserService.cs"]
    },
    {
      "id": "AS-DATA-001",
      "type": "DATA_STORE",
      "label": "Application database",
      "evidence": {
        "path": "Services/UserService.cs",
        "symbol": "Disable",
        "observation": "_dbContext.SaveChanges()"
      },
      "confidence": "HIGH",
      "tags": ["SENSITIVE_SINK"],
      "freshnessOf": ["Services/UserService.cs"]
    },
    {
      "id": "AS-ENTRY-003",
      "type": "ENTRY_POINT",
      "label": "possible admin route (unresolved)",
      "evidence": {
        "path": "AdminModule.cs",
        "symbol": "(none)",
        "observation": "routes registered via a custom IRouteConvention that composes paths from controller names at startup - not statically resolvable by reading source alone"
      },
      "confidence": "LOW",
      "status": "NEEDS_VERIFICATION",
      "freshnessOf": ["AdminModule.cs"]
    }
  ],
  "edges": [
    {
      "from": "AS-AUTHN-001",
      "to": "AS-ENTRY-001",
      "type": "AUTHENTICATES",
      "evidence": {
        "path": "Program.cs",
        "symbol": "(none)",
        "observation": "app.UseAuthentication() runs before endpoint routing"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Program.cs"]
    },
    {
      "from": "AS-ENTRY-001",
      "to": "AS-SVC-001",
      "type": "CALLS",
      "evidence": {
        "path": "Controllers/FilesController.cs",
        "symbol": "Download",
        "observation": "the route directly invokes this action method"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/FilesController.cs"]
    },
    {
      "from": "AS-AUTHZ-001",
      "to": "AS-SVC-001",
      "type": "AUTHORIZES",
      "evidence": {
        "path": "Controllers/FilesController.cs",
        "symbol": "Download",
        "observation": "the ownership check runs at the top of Download, before FileService.Resolve is called"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/FilesController.cs"]
    },
    {
      "from": "AS-SVC-001",
      "to": "AS-SVC-002",
      "type": "CALLS",
      "evidence": {
        "path": "Controllers/FilesController.cs",
        "symbol": "Download",
        "observation": "_fileService.Resolve(id)"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/FilesController.cs"]
    },
    {
      "from": "AS-SVC-002",
      "to": "AS-FS-001",
      "type": "READS",
      "evidence": {
        "path": "Services/FileService.cs",
        "symbol": "Resolve",
        "observation": "File.OpenRead(resolvedPath)"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Services/FileService.cs"]
    },
    {
      "from": "AS-AUTHZ-002",
      "to": "AS-ENTRY-002",
      "type": "AUTHORIZES",
      "evidence": {
        "path": "Controllers/AdminController.cs",
        "symbol": "DisableUser",
        "observation": "[Authorize(Policy = \"AdminOnly\")] on the action"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/AdminController.cs"]
    },
    {
      "from": "AS-ENTRY-002",
      "to": "AS-SVC-003",
      "type": "CALLS",
      "evidence": {
        "path": "Controllers/AdminController.cs",
        "symbol": "DisableUser",
        "observation": "the route directly invokes this action method"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/AdminController.cs"]
    },
    {
      "from": "AS-SVC-003",
      "to": "AS-SVC-004",
      "type": "CALLS",
      "evidence": {
        "path": "Controllers/AdminController.cs",
        "symbol": "DisableUser",
        "observation": "_userService.Disable(id)"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Controllers/AdminController.cs"]
    },
    {
      "from": "AS-SVC-004",
      "to": "AS-DATA-001",
      "type": "WRITES",
      "evidence": {
        "path": "Services/UserService.cs",
        "symbol": "Disable",
        "observation": "_dbContext.SaveChanges()"
      },
      "confidence": "HIGH",
      "freshnessOf": ["Services/UserService.cs"]
    }
  ]
}
```

`freshnessOf` (same meaning as `templates/project-security-baseline.md`'s
field of the same name) lists the evidence file(s) a node or edge
depends on — every node and edge above has one — used by
`plays/security-impact-analysis.md` to re-evaluate only the affected
nodes/edges after a change, not the whole map. `tags` (optional) adds
`ADMIN_SURFACE` and/or `SENSITIVE_SINK` on top of a node's structural
`type` — see the play's "Dual-typing" section; note `AS-ENTRY-003`'s
`status: "NEEDS_VERIFICATION"` alongside `confidence: "LOW"` for a
route that could not be statically resolved. `AS-ENTRY-003` has no
outgoing edges in this example because nothing downstream of it could
be confidently resolved either. `status` can also hold `"STALE"` (not
shown above) for a node/edge that *was* resolved but whose evidence a
later change has contradicted — see the play's "Evidence-backed
mapping" section for how that differs from `NEEDS_VERIFICATION`.
