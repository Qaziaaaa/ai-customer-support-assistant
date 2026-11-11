"""Tools — functions the LLM is allowed to call.

How tool calling works (the whole mechanism):
1. We give the model a JSON schema for each tool (auto-generated from the
   function signature + docstring by LangChain).
2. When the model decides it needs data, it does NOT answer the user —
   it returns a `tool_call` (function name + JSON args) instead.
3. OUR code executes the real function and sends the result back as a
   `ToolMessage`. The model then writes the final natural-language answer.

The model never executes anything itself — it only *requests* execution.
That's why tools are the bridge between "LLM brains" and "real data".
"""

from __future__ import annotations

from langchain_core.tools import tool

from src.data.orders import get_order as lookup_order


@tool
def get_order(order_id: str) -> str:
    """Look up a NovaMart order by its ID (format ORD-####).

    Use this whenever the customer asks about order status, tracking,
    delivery date, or contents of a specific order. Returns order details
    as JSON, or a not-found message if the ID does not exist.
    """
    order = lookup_order(order_id)
    if order is None:
        return (
            f"No order found for ID '{order_id}'. "
            "Politely ask the customer to double-check the ID "
            "(expected format ORD-####)."
        )
    # Compact summary the model can quote directly to the customer.
    lines = [
        f"Order {order['id']}",
        f"Product: {order['product']} x{order['quantity']}",
        f"Price: ${order['price_usd']:.2f}",
        f"Shipping: {order['shipping']}",
        f"Status: {order['status']}",
        f"Placed: {order['placed_on']}",
    ]
    if order["delivered_on"]:
        lines.append(f"Delivered: {order['delivered_on']}")
    if order["tracking"]:
        lines.append(f"Tracking: {order['tracking']}")
    return "\n".join(lines)


# Single list the graph (Step 6) will bind to the LLM.
TOOLS = [get_order]
