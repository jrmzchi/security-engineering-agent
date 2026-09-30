// Fixture: caller-less data-access method, authorization class (SAFE to NOT confirm)
//
// Expected review outcome: No confirmed finding (NEEDS_VERIFICATION is the
// right answer). See plays/finding-validation.md, "Rule — a sink whose
// callers are outside the review scope", authorization class: the method is
// public and loads a document by id with no ownership filter, but object-level
// authorization is normally enforced by the caller, and no caller is in scope.
// The trap: confirming BOLA/IDOR only because the method is public and its
// callers are unseen.

using Microsoft.EntityFrameworkCore;

namespace FixtureApp.Data;

public class DocumentRepository
{
    private readonly AppDbContext _db;

    public DocumentRepository(AppDbContext db) => _db = db;

    public Document? FindById(int documentId)
    {
        return _db.Documents.AsNoTracking().FirstOrDefault(d => d.Id == documentId);
    }

    public List<Document> ListForOwner(int ownerUserId)
    {
        return _db.Documents.AsNoTracking().Where(d => d.OwnerUserId == ownerUserId).ToList();
    }
}

public class Document
{
    public int Id { get; set; }
    public int OwnerUserId { get; set; }
    public string Title { get; set; } = "";
    public byte[] Content { get; set; } = System.Array.Empty<byte>();
}
