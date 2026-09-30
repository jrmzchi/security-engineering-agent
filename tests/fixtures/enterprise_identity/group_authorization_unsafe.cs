// Fixture: SSO sign-in treated as authorization for an admin function (VULNERABLE)
//
// Expected review outcome: CONFIRMED, HIGH missing function-level
// authorization (CWE-862 / CWE-285).
// See plays/enterprise-identity-security.md, "Authorization after login",
// and plays/authorization.md, "Missing function authorization".
//
// Attack path: every employee (and every guest account) in the tenant can
// sign in. The payroll export only requires a signed-in user, so any of them
// can download every employee's salary data. The comment's assumption that
// "SSO already restricts this" confuses authentication with authorization.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Identity;

[ApiController]
[Route("admin/payroll")]
[Authorize] // VULNERABLE: authenticated only -- no group, role or policy requirement
public class PayrollExportController : ControllerBase
{
    private readonly IPayrollStore _payroll;

    public PayrollExportController(IPayrollStore payroll) => _payroll = payroll;

    // "Only HR can reach the admin menu, and SSO already restricts this to employees."
    [HttpGet("export")]
    public IActionResult ExportAll() => File(_payroll.ExportCsv(), "text/csv", "payroll.csv");
}

public interface IPayrollStore
{
    byte[] ExportCsv();
}
