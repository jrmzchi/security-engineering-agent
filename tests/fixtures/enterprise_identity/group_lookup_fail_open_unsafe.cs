// Fixture: directory group check that grants access when the directory fails (VULNERABLE)
//
// Expected review outcome: CONFIRMED, HIGH fail-open authorization
// (CWE-636 not failing securely; CWE-285).
// See plays/enterprise-identity-security.md, "Fail-closed on identity failure".
//
// Attack path: the approval endpoint is meant for members of the Finance
// Approvers group. Whenever the group lookup throws (domain controller
// unreachable, timeout, or a query the caller can make fail), the handler
// grants the requirement, so any signed-in user can approve invoices.

using Microsoft.AspNetCore.Authorization;

namespace FixtureApp.Identity;

public sealed class FinanceApproverRequirement : IAuthorizationRequirement { }

public interface IDirectoryGroups
{
    Task<bool> IsMemberAsync(string userPrincipalName, string groupDn, CancellationToken ct);
}

public sealed class FinanceApproverHandler : AuthorizationHandler<FinanceApproverRequirement>
{
    private const string ApproversGroupDn = "CN=Finance Approvers,OU=Groups,DC=corp,DC=example";
    private readonly IDirectoryGroups _groups;
    private readonly ILogger<FinanceApproverHandler> _log;

    public FinanceApproverHandler(IDirectoryGroups groups, ILogger<FinanceApproverHandler> log)
    {
        _groups = groups;
        _log = log;
    }

    protected override async Task HandleRequirementAsync(AuthorizationHandlerContext context, FinanceApproverRequirement requirement)
    {
        var upn = context.User.Identity?.Name;
        if (upn is null)
        {
            return;
        }
        try
        {
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(3));
            if (await _groups.IsMemberAsync(upn, ApproversGroupDn, cts.Token))
            {
                context.Succeed(requirement);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "Group lookup failed for {User}; allowing to avoid blocking month-end", upn);
            context.Succeed(requirement); // VULNERABLE: directory failure grants access
        }
    }
}
