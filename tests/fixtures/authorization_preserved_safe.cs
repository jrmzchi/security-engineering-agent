// Fixture: [Authorize] preserved on a sensitive endpoint (SAFE)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to authorization_removed_unsafe.cs — a
// reviewer scanning a diff that touches this controller for unrelated
// reasons (e.g. adding a new field to the delete confirmation
// response) must not flag it just because it's an admin endpoint;
// [Authorize(Roles = "Admin")] is still present and unchanged.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("admin/users")]
[Authorize(Roles = "Admin")]
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
