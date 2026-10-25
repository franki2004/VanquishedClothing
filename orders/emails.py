import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

SUBJECTS = {
    "pending": "We received your order #{id}",
    "accepted": "Your order #{id} has been accepted",
    "denied": "Your order #{id} was declined",
}


def send_order_email(order):
    """Send the order summary to the customer. Never raises."""
    if not order.email or order.status not in SUBJECTS:
        return

    try:
        items = list(order.items.select_related("variant__product"))
        subject = SUBJECTS[order.status].format(id=order.id)

        html = render_to_string("orders/order_email.html", {
            "order": order,
            "items": items,
        })

        lines = [f"{subject}", ""]
        for item in items:
            lines.append(
                f"- {item.variant.product.name} ({item.variant.size}) "
                f"x {item.quantity}: €{item.total_price:.2f}"
            )
        lines += [
            "",
            f"Subtotal: €{order.subtotal}",
            f"Delivery: €{order.delivery_fee}",
        ]
        if order.cod_fee:
            lines.append(f"Cash on delivery fee: €{order.cod_fee}")
        lines.append(f"Total: €{order.total}")
        if order.status == "denied" and order.comment:
            lines += ["", f"Reason: {order.comment}"]

        msg = EmailMultiAlternatives(
            subject,
            "\n".join(lines),
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send()
    except Exception:
        logger.exception("Failed to send order email for order %s", order.id)