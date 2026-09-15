// Fixture: IDOR / Broken Object Level Authorization (SAFE — ownership
// check enforced)
//
// Expected review outcome: NO confirmed finding. False-positive-
// avoidance counterpart to idor_unsafe.cs — a reviewer must not flag
// this just because the route takes an ID and the endpoint requires
// authentication.
//
// Why it's safe: the handler verifies the order belongs to the
// authenticated caller before returning it, in addition to requiring
// authentication. An unguessable ID is NOT what makes this safe — the
// explicit ownership check is (see plays/authorization.md).

using System.Security.Claims;
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
        var order = _orders.GetById(orderId);
        if (order is null)
        {
            return NotFound();
        }

        // SAFE: object-level authorization — confirm the caller owns
        // this specific order before returning it.
        var currentUserId = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        if (order.OwnerUserId != currentUserId)
        {
            return Forbid();
        }

        return Ok(order);
    }
}
