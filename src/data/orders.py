"""NovaMart mock order database.

In a real product this would be a database query. For the MVP the orders
live in a plain dict so the tool-calling demo has something to retrieve.

Each order is keyed by its ID (what the customer would quote in chat).
"""

ORDERS: dict[str, dict] = {
    "ORD-1001": {
        "id": "ORD-1001",
        "customer": "alice@example.com",
        "product": "NovaSound Pro Headphones",
        "quantity": 1,
        "price_usd": 129.99,
        "shipping": "Standard (5-7 business days)",
        "status": "Delivered",
        "placed_on": "2026-10-20",
        "delivered_on": "2026-10-26",
        "tracking": "NV1001US",
    },
    "ORD-1002": {
        "id": "ORD-1002",
        "customer": "bob@example.com",
        "product": "MechaType K75 Keyboard",
        "quantity": 1,
        "price_usd": 74.50,
        "shipping": "Express (2 business days)",
        "status": "In transit",
        "placed_on": "2026-11-05",
        "delivered_on": None,
        "tracking": "NV1002US",
    },
    "ORD-1003": {
        "id": "ORD-1003",
        "customer": "carol@example.com",
        "product": "PulseFit Smartwatch S2",
        "quantity": 2,
        "price_usd": 199.98,
        "shipping": "Standard (5-7 business days)",
        "status": "Shipped",
        "placed_on": "2026-11-08",
        "delivered_on": None,
        "tracking": "NV1003US",
    },
    "ORD-1004": {
        "id": "ORD-1004",
        "customer": "dave@example.com",
        "product": "NovaSound Pro Headphones",
        "quantity": 1,
        "price_usd": 129.99,
        "shipping": "Standard (5-7 business days)",
        "status": "Cancelled",
        "placed_on": "2026-11-01",
        "delivered_on": None,
        "tracking": None,
    },
}


def get_order(order_id: str) -> dict | None:
    """Return the order dict for `order_id`, or None if it does not exist.

    Lookup is case-insensitive so 'ord-1001' and 'ORD-1001' both work.
    """
    return ORDERS.get(order_id.strip().upper())
