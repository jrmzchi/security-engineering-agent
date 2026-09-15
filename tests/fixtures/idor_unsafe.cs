// Fixture: IDOR / Broken Object Level Authorization (VULNERABLE)
//
// Expected review outcome: CONFIRMED HIGH IDOR (CWE-639). See
// plays/authorization.md and plays/api-security.md.
//
// Attack path: the caller is authenticated (so a naive check might
// wave this through), but `orderId` is attacker-controlled and the
// handler never checks that the order belongs to the current caller —
// any logged-in user can read any other user's order by guessing or
// incrementing the ID.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FixtureApp.Controllers;

[ApiController]
[Route("api/orders")]
[Authorize]
public class OrdersController : ControllerBase
{
    private readonly IOrderRepository _orders;

    public OrdersController(IOrderRepository orders) => _orders = orders;

    [HttpGet("{orderId}")]
    public IActionResult GetOrder(int orderId)
    {
        // VULNERABLE: authentication is enforced ([Authorize]), but
        // there is no check that this order belongs to the current
        // user — object-level authorization is missing entirely.
        var order = _orders.GetById(orderId);
        if (order is null)
        {
            return NotFound();
        }
        return Ok(order);
    }
}
