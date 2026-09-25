// Fixture: cross-file SQL (SAFE -- parameterized), V4 release corpus row RV-35 -- part 2 of 3
//
// See ProductsController.cs and ProductRepository.cs.

namespace FixtureApp.Services;

public class ProductSearchService
{
    private readonly Repositories.ProductRepository _repository;

    public ProductSearchService(Repositories.ProductRepository repository) => _repository = repository;

    public List<Models.Product> SearchProducts(string query)
    {
        return _repository.FindPublishedByNameLike(query);
    }
}
