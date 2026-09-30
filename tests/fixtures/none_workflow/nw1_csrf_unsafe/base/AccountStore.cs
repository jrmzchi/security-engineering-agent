using System.Collections.Concurrent;

public sealed class AccountStore
{
    private readonly ConcurrentDictionary<string, string> _accounts = new();

    public Task DeleteAsync(string userId)
    {
        _accounts.TryRemove(userId, out _);
        return Task.CompletedTask;
    }
}
