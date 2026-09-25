// Fixture: admin function gated by a group object ID, overage denied (SAFE)
//
// Expected review outcome: no confirmed finding.
// See plays/enterprise-identity-security.md, "Authorization after login".
//
// Why it is safe: the policy requires membership of one specific group,
// identified by its immutable object ID (not its display name). When the token
// carries the group-overage indicator instead of the group list, the request
// is DENIED rather than let through. The group ID is configuration, not a
// secret.

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Identity;

public static class PayrollPolicy
{
    public const string Name = "PayrollAdmins";

    public static void Register(AuthorizationOptions options, string payrollAdminGroupObjectId) =>
        options.AddPolicy(Name, policy => policy
            .RequireAuthenticatedUser()
            .RequireAssertion(ctx => IsMember(ctx.User, payrollAdminGroupObjectId)));

    internal static bool IsMember(ClaimsPrincipal user, string groupObjectId)
    {
        // Overage: the token lists no groups and points at Graph instead. Membership is
        // unknown, so the request is denied instead of assumed.
        if (user.HasClaim(c => c.Type == "_claim_names" || c.Type == "hasgroups"))
        {
            return false;
        }
        return user.HasClaim("groups", groupObjectId);
    }
}

[ApiController]
[Route("admin/payroll")]
[Authorize(Policy = PayrollPolicy.Name)]
public class PayrollExportController : ControllerBase
{
    private readonly IPayrollStore _payroll;

    public PayrollExportController(IPayrollStore payroll) => _payroll = payroll;

    [HttpGet("export")]
    public IActionResult ExportAll() => File(_payroll.ExportCsv(), "text/csv", "payroll.csv");
}

public interface IPayrollStore
{
    byte[] ExportCsv();
}
