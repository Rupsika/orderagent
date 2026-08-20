"""
tools.py

Defines the agent's tools using LangChain's @tool decorator.

Security note (mirrors the README's "backend controls which customer
identity is allowed to be accessed"): build_tools() is called once per
request with the *authenticated* customer_id from the API layer, and
that id is closed over inside each tool function. The LLM can pass an
order_id in its tool call, but every tool re-checks that the order
actually belongs to this customer before returning anything. The LLM
never gets to supply its own customer_id.
"""

from langchain_core.tools import tool
import crud as db


def build_tools(customer_id: str):
    """Return the list of tools for this specific authenticated customer."""

    @tool
    def get_my_orders() -> str:
        """List all orders placed by the current customer, with id and status."""
        orders = db.get_orders_for_customer(customer_id)
        if not orders:
            return "This customer has no orders on file."
        return "\n".join(
            f"- {o['order_id']}: status={o['status']}, total={o['total']}, placed_at={o['placed_at']}"
            for o in orders
        )

    @tool
    def get_order_details(order_id: str) -> str:
        """Get full details (items, total, status) for one order by its order_id."""
        order = db.get_order(order_id)
        if not order or order["customer_id"] != customer_id:
            return f"No order {order_id} found for this customer."
        return str(order)

    @tool
    def get_tracking_status(order_id: str) -> str:
        """Get live shipment tracking status and history for an order_id."""
        order = db.get_order(order_id)
        if not order or order["customer_id"] != customer_id:
            return f"No order {order_id} found for this customer."
        shipment = db.get_tracking(order_id)
        if not shipment:
            return f"Order {order_id} has no shipment/tracking record yet (status: {order['status']})."
        return str(shipment)

    @tool
    def get_my_tickets() -> str:
        """List this customer's past and open support tickets."""
        tickets = db.get_tickets_for_customer(customer_id)
        if not tickets:
            return "No past tickets for this customer."
        return "\n".join(
            f"- {t['ticket_id']}: {t['subject']} (status={t['status']}, order={t['order_id']})"
            for t in tickets
        )

    @tool
    def create_support_ticket(order_id: str, subject: str, description: str) -> str:
        """
        Create a support ticket for this customer about a specific order.
        Use this when the issue can't be resolved immediately by giving
        information alone (e.g. damaged package, missing delivery, needs
        human follow-up).
        """
        order = db.get_order(order_id)
        if not order or order["customer_id"] != customer_id:
            return f"Cannot create ticket: order {order_id} not found for this customer."
        ticket = db.create_ticket(customer_id, order_id, subject, description)
        return f"Created ticket {ticket['ticket_id']} with status OPEN."

    @tool
    def check_refund_eligibility(order_id: str) -> str:
        """Check whether an order is eligible for a refund based on its status and age."""
        order = db.get_order(order_id)
        if not order or order["customer_id"] != customer_id:
            return f"No order {order_id} found for this customer."
        if order["status"] == "DELIVERED":
            return f"Order {order_id} is DELIVERED. Eligible for refund request within policy window (raise a ticket to proceed)."
        if order["status"] in ("PROCESSING", "SHIPPED"):
            return f"Order {order_id} has not been delivered yet ({order['status']}). Not eligible for refund; cancellation may apply instead."
        return f"Order {order_id} status is {order['status']}; not eligible for refund."

    @tool
    def request_cancellation(order_id: str) -> str:
        """
        Attempt to cancel an order. Only works if the order has not
        shipped yet. This performs a real (mocked) state change, so only
        call it once you're confident the customer wants to cancel.
        """
        order = db.get_order(order_id)
        if not order or order["customer_id"] != customer_id:
            return f"No order {order_id} found for this customer."
        result = db.cancel_order(order_id)
        return result["reason"]

    return [
        get_my_orders,
        get_order_details,
        get_tracking_status,
        get_my_tickets,
        create_support_ticket,
        check_refund_eligibility,
        request_cancellation,
    ]
