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


RETURN_SUBJECTS = {
    "requested": "We received your return request for order #{id}",
    "approved": "Your return for order #{id} was approved",
    "rejected": "Your return for order #{id} was declined",
}

RETURN_INTROS = {
    "requested": "We received your return request and will review it shortly.",
    "approved": (
        "Your return request was approved. We'll contact you with instructions "
        "for sending the products back and receiving your refund."
    ),
    "rejected": "Unfortunately we couldn't approve your return request.",
}


def send_return_email(order, items, status):
    """Plain-text return update for the customer. Never raises."""
    if not order.email or status not in RETURN_SUBJECTS:
        return

    try:
        subject = RETURN_SUBJECTS[status].format(id=order.id)
        lines = [subject, "", RETURN_INTROS[status], ""]
        for item in items:
            lines.append(
                f"- {item.variant.product.name} ({item.variant.size}) x {item.quantity}"
            )
            if status == "rejected" and item.return_admin_comment:
                lines.append(f"  Reason: {item.return_admin_comment}")

        msg = EmailMultiAlternatives(
            subject,
            "\n".join(lines),
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
        )
        msg.send()
    except Exception:
        logger.exception("Failed to send return email for order %s", order.id)