// Fixture: authorization class, one unsafe in-scope path (VULNERABLE) — part 1 of 3
//
// Expected review outcome: CONFIRMED HIGH BOLA/IDOR (CWE-639) on the export
// endpoint. See plays/finding-validation.md, "Rule — a sink whose callers are
// outside the review scope", "Any class": Get() reaches the document through
// DocumentService, which enforces ownership; Export() calls the repository
// directly and returns any document to any authenticated user. The trap:
// letting the safe path, or the repository's other unseen callers, erase the
// evidence of the unsafe in-scope path.

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("api/documents")]
[Authorize]
public class DocumentsController : ControllerBase
{
    private readonly Services.DocumentService _service;
    private readonly Data.DocumentRepository _repository;

    public DocumentsController(Services.DocumentService service, Data.DocumentRepository repository)
    {
        _service = service;
        _repository = repository;
    }

    [HttpGet("{documentId:int}")]
    public IActionResult Get(int documentId)
    {
        var doc = _service.GetForCurrentUser(documentId, CurrentUserId());
        return doc is null ? NotFound() : Ok(new { doc.Id, doc.Title });
    }

    [HttpGet("{documentId:int}/export")]
    public IActionResult Export(int documentId)
    {
        var doc = _repository.FindById(documentId);
        if (doc is null)
        {
            return NotFound();
        }
        return File(doc.Content, "application/octet-stream", $"document-{doc.Id}.bin");
    }

    private int CurrentUserId() => int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
}
