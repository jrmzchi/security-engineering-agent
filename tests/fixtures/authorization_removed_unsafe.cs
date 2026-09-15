// Fixture: [Authorize] removed from a sensitive endpoint (VULNERABLE)
//
// Expected review outcome: CONFIRMED CRITICAL — broken access control
// (CWE-284/CWE-862, missing authorization). See
// plays/authorization.md and plays/security-change-detection.md's
// HIGH-sensitivity signal list ("authorization" changes).
//
// This fixture represents the diff itself, not just the end state —
// the point is that a diff-aware reviewer must notice a REMOVED
// [Authorize] attribute as a change to flag, not just review the
// current file as if it always looked this way:
//
//   [ApiController]
//   [Route("admin/users")]
// - [Authorize(Roles = "Admin")]
//   public class AdminUsersController : ControllerBase
//   {
//       [HttpDelete("{userId}")]
//       public IActionResult DeleteUser(int userId) { ... }
//   }
//
// Attack path: any authenticated OR unauthenticated caller (depending
// on whether authentication middleware still runs ahead of this
// controller) can now call DELETE /admin/users/{userId} — an
// administrative function that previously required the Admin role.

using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("admin/users")]
// VULNERABLE: [Authorize(Roles = "Admin")] was removed from this line
// by the change under review.
public class AdminUsersController : ControllerBase
{
    private readonly IUserService _users;

    public AdminUsersController(IUserService users) => _users = users;

    [HttpDelete("{userId}")]
    public IActionResult DeleteUser(int userId)
    {
        _users.Delete(userId);
        return NoContent();
    }
}
