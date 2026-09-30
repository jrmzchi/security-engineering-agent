using System.Collections.Concurrent;

public sealed class OrderStore
{
    private readonly ConcurrentDictionary<Guid, (string Owner, string Sku, int Quantity)> _orders = new();

    public Task<Guid> CreateAsync(string owner, string sku, int quantity)
    {
        var id = Guid.NewGuid();
        _orders[id] = (owner, sku, quantity);
        return Task.FromResult(id);
    }
}
