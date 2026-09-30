// Fixture: authorization class, one unsafe in-scope path (VULNERABLE) — part 3 of 3
//
// See DocumentsController.cs. A public data-access method with no ownership
// filter of its own (normal: the control belongs to its callers). Other
// callers outside this directory may exist; they do not change the verdict on
// the in-scope Export() path.

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
}

public class Document
{
    public int Id { get; set; }
    public int OwnerUserId { get; set; }
    public string Title { get; set; } = "";
    public byte[] Content { get; set; } = System.Array.Empty<byte>();
}
