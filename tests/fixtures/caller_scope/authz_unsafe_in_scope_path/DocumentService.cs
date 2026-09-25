// Fixture: authorization class, one unsafe in-scope path (VULNERABLE) — part 2 of 3
//
// See DocumentsController.cs. This service is the SAFE path: it returns a
// document only to its owner. It does not protect the controller's Export()
// action, which never calls it.

namespace FixtureApp.Services;

public class DocumentService
{
    private readonly Data.DocumentRepository _repository;

    public DocumentService(Data.DocumentRepository repository) => _repository = repository;

    public Data.Document? GetForCurrentUser(int documentId, int currentUserId)
    {
        var doc = _repository.FindById(documentId);
        if (doc is null || doc.OwnerUserId != currentUserId)
        {
            return null;
        }
        return doc;
    }
}
