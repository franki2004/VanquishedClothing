from django.urls import reverse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
from datetime import timedelta
import stripe
from django.contrib import messages
from .models import CartItem, Cart, Order, OrderItem
from store.models import ProductVariant, ProductVariantReservation
from accounts.forms import AddressForm
from .forms import CustomerForm
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from .emails import send_order_email
import logging
import json

User = get_user_model()
logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

RESERVATION_MINUTES = 5
COD_PERCENT = Decimal("0.03")


# ---------------------------
# CART HELPERS
# ---------------------------
def get_or_create_cart(request=None, user=None):
    if user:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    if not request.session.session_key:
        request.session.create()

    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart

def _owner_q(user, session_key):
    if user:
        return Q(user=user)
    if session_key:
        return Q(session_key=session_key, user__isnull=True)
    return Q(pk__in=[])  

# ---------------------------
# CART
# ---------------------------
def cart_view(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")

    subtotal = sum((item.total_price for item in items), Decimal("0.00"))
    delivery_fee = Decimal("5.00") if 0 < subtotal < 100 else Decimal("0.00")
    total = subtotal + delivery_fee

    return render(request, "store/cart.html", {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "free_delivery_threshold": 100,
        "remaining_for_free_delivery": max(0, 100 - subtotal),
        "free_delivery_progress": min(100, int(subtotal)),
    })


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)

    try:
        item = cart.items.select_related("variant").get(id=item_id)
    except CartItem.DoesNotExist:
        return redirect("cart")

    action = request.POST.get("action")

    if action == "increase":
        item.quantity = min(item.quantity + 1, item.variant.available_quantity())
    elif action == "decrease":
        item.quantity -= 1
    elif action == "remove":
        item.quantity = 0

    if item.quantity <= 0:
        item.delete()
    else:
        item.save()

    return redirect("cart")


# ---------------------------
# CHECKOUT ------------ 
# ---------------------------
def checkout(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")

    if not items.exists():
        return redirect("cart")

    subtotal = sum((item.total_price for item in items), Decimal("0.00"))
    delivery_fee = Decimal("5.00") if 0 < subtotal < 100 else Decimal("0.00")
    total = subtotal + delivery_fee

    user = request.user if request.user.is_authenticated else None

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    addresses = user.addresses.all() if user else []
    selected_address = (
        addresses.filter(is_default=True).first() or addresses.first()
        if user else None
    )

    customer_initial = {
        "first_name": getattr(user, "first_name", ""),
        "last_name": getattr(user, "last_name", ""),
        "phone": getattr(user, "phone_number", ""),
        "email": getattr(user, "email", ""),
    } if user else None

    def render_checkout(customer_form, address_form=None, chosen=None):
        return render(request, "store/checkout.html", {
            "items": items,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": total,
            "addresses": addresses,
            "selected_address": chosen or selected_address,
            "customer_form": customer_form,
            "address_form": address_form,
        })

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        customer_form = CustomerForm(request.POST)
        chosen_address = None

        if user:
            address_id = request.POST.get("address_id")
            chosen_address = (
                addresses.filter(id=int(address_id)).first()
                if address_id and address_id.isdigit()
                else None
            )
            action = request.POST.get("address_action", "order")

            # --- address modal actions ---
            if action == "save":
                address_form = AddressForm(request.POST, instance=chosen_address)
                if address_form.is_valid():
                    addr = address_form.save(commit=False)
                    addr.user = user
                    try:
                        addr.save()
                    except ValueError as exc:  # e.g. max 5 addresses
                        messages.error(request, str(exc))
                        return render_checkout(CustomerForm(initial=customer_initial))
                    return redirect("checkout")
                messages.error(request, "Please check the address details and try again.")
                return render_checkout(CustomerForm(initial=customer_initial), address_form)

            if action == "delete":
                if chosen_address:
                    chosen_address.delete()
                return redirect("checkout")

            # --- placing the order ---
            if not chosen_address:
                messages.error(request, "Please select a delivery address.")
                return render_checkout(customer_form)

            if not customer_form.is_valid():
                messages.error(request, "Please fix the errors in your contact details.")
                return render_checkout(customer_form, chosen=chosen_address)

            addr_info = chosen_address

        else:
            if not customer_form.is_valid():
                messages.error(request, "Please fix the errors in your contact details.")
                return render_checkout(customer_form)

            street = request.POST.get("street", "").strip()
            city = request.POST.get("city", "").strip()
            postal_code = request.POST.get("postal_code", "").strip()
            country = request.POST.get("country", "").strip()

            if not all([street, city, postal_code, country]):
                messages.error(request, "Please fill in your full delivery address.")
                return render_checkout(customer_form)

            addr_info = SimpleNamespace(
                id=None, city=city, postal_code=postal_code,
                address_line=street, country=country,
            )

        if payment_method not in ("card", "cod"):
            messages.error(request, "Please choose a payment method.")
            return render_checkout(customer_form, chosen=chosen_address)

        first_name = customer_form.cleaned_data["first_name"]
        last_name = customer_form.cleaned_data["last_name"]
        phone = customer_form.cleaned_data["phone"]
        email = customer_form.cleaned_data["email"]
        full_name = f"{first_name} {last_name}"

        cod_fee = Decimal("0.00")
        if payment_method == "cod":
            cod_fee = (subtotal * COD_PERCENT).quantize(Decimal("0.01"))
        total_with_fees = (subtotal + delivery_fee + cod_fee).quantize(Decimal("0.01"))

        owner_q = _owner_q(user, session_key)

        # ---------------------------
        # CARD (STRIPE)
        # ---------------------------
        if payment_method == "card":
            with transaction.atomic():
                # drop this customer's old holds so retries don't block themselves
                ProductVariantReservation.objects.filter(owner_q).delete()

                locked_items = list(items.select_for_update())
                for item in locked_items:
                    if item.variant.available_quantity() < item.quantity:
                        return redirect("cart")

                for item in locked_items:
                    ProductVariantReservation.objects.create(
                        variant=item.variant,
                        user=user,
                        session_key=session_key if not user else None,
                        quantity=item.quantity,
                        reserved_until=timezone.now() + timedelta(minutes=RESERVATION_MINUTES),
                    )

            line_items = [
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": f"{item.variant.product.name} - {item.variant.size}"},
                        "unit_amount": int(item.variant.product.final_price * 100),
                    },
                    "quantity": item.quantity,
                } for item in items
            ]

            if delivery_fee > 0:
                line_items.append({
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": "Delivery Fee"},
                        "unit_amount": int(delivery_fee * 100),
                    },
                    "quantity": 1,
                })

            metadata = {
                "cart_id": str(cart.id),
                "user_id": str(user.id) if user else "",
                "session_key": session_key if not user else "",
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "email": email,
                "city": addr_info.city,
                "postal_code": addr_info.postal_code,
                "street": addr_info.address_line,
                "country": addr_info.country,
                "delivery_fee": str(delivery_fee),
            }

            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    success_url=request.build_absolute_uri(reverse("checkout_success_page")),
                    cancel_url=request.build_absolute_uri(reverse("checkout")),
                    metadata=metadata,
                )
            except Exception:
                logger.exception("Stripe session creation failed for cart %s", cart.id)
                ProductVariantReservation.objects.filter(owner_q).delete()
                messages.error(
                    request,
                    "We couldn't start the card payment. Please try again or choose cash on delivery.",
                )
                return render_checkout(customer_form, chosen=chosen_address)

            return redirect(session.url)

        # ---------------------------
        # COD
        # ---------------------------
        with transaction.atomic():
            ProductVariantReservation.objects.filter(owner_q).delete()

            locked_items = list(items.select_for_update())

            # check EVERYTHING first, then change stock (the old loop could
            # commit partial stock changes before returning)
            for item in locked_items:
                if item.variant.available_quantity() < item.quantity:
                    return redirect("cart")

            for item in locked_items:
                variant = item.variant
                variant.stock -= item.quantity
                variant.save(update_fields=["stock"])

            order = Order.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
                email=email,
                city=addr_info.city,
                postal_code=addr_info.postal_code,
                street=addr_info.address_line,
                country=addr_info.country,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                cod_fee=cod_fee,
                total=total_with_fees,
                payment_method="cod",
                status="pending",
            )

            for item in locked_items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    price_snapshot=item.variant.product.final_price,
                )

            cart.items.all().delete()
            transaction.on_commit(lambda: send_order_email(order))

        return redirect("checkout_success_page")

    # ---------------------------
    # GET
    # ---------------------------
    return render_checkout(
        CustomerForm(initial=customer_initial),
        AddressForm() if user else None,
    )

# ---------------------------
# STRIPE WEBHOOK
# ---------------------------
def _fulfil_card_order(session):
    """Create the order for a paid Stripe Checkout session."""
    session_id = session["id"]
    metadata = session.get("metadata") or {}

    # already processed (Stripe retries deliveries)
    if Order.objects.filter(stripe_session_id=session_id).exists():
        return

    cart_id = str(metadata.get("cart_id") or "")
    cart = Cart.objects.filter(id=int(cart_id)).first() if cart_id.isdigit() else None
    if not cart:
        logger.error("Stripe session %s PAID but cart %r was not found - needs manual review",
                     session_id, cart_id)
        return

    user_id = metadata.get("user_id")
    user = User.objects.filter(id=user_id).first() if user_id else None
    session_key = metadata.get("session_key") or None

    try:
        delivery_fee = Decimal(metadata.get("delivery_fee") or "0.00")
    except InvalidOperation:
        delivery_fee = Decimal("0.00")

    amount_total = (Decimal(session.get("amount_total") or 0) / 100).quantize(Decimal("0.01"))

    with transaction.atomic():
        items = list(cart.items.select_related("variant__product").select_for_update())
        if not items:
            logger.error("Stripe session %s PAID but cart %s is empty - needs manual review",
                         session_id, cart.id)
            return

        subtotal = sum((i.total_price for i in items), Decimal("0.00"))

        # The customer already paid. If real stock is short, don't touch stock;
        # create the order as "pending" so an admin can review/refund it.
        short = [i for i in items if i.variant.stock < i.quantity]
        if short:
            status = "pending"
            comment = (
                "PAID BY CARD - stock problem: "
                + ", ".join(str(i.variant) for i in short)
                + f". Check/refund in Stripe ({session_id})."
            )
            logger.error("Stripe session %s paid but stock is short: %s", session_id, comment)
        else:
            status = "accepted"
            comment = ""
            for item in items:
                variant = item.variant
                variant.stock -= item.quantity
                variant.save(update_fields=["stock"])

        # .get(key, "") because Stripe drops empty metadata values
        order = Order.objects.create(
            user=user,
            full_name=f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip(),
            phone=metadata.get("phone", ""),
            email=metadata.get("email", ""),
            street=metadata.get("street", ""),
            city=metadata.get("city", ""),
            postal_code=metadata.get("postal_code", ""),
            country=metadata.get("country", ""),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=amount_total,
            payment_method="card",
            status=status,
            comment=comment,
            stripe_session_id=session_id,
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price_snapshot=item.variant.product.final_price,
            )

        ProductVariantReservation.objects.filter(_owner_q(user, session_key)).delete()
        cart.items.all().delete()
        transaction.on_commit(lambda: send_order_email(order))


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET is not set")
        return HttpResponse(status=500)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    if not sig_header:
        logger.warning("Stripe webhook called without a signature header")
        return HttpResponse(status=400)

    try:
        # verifies the signature; afterwards we read the payload as plain JSON
        stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        event = json.loads(payload)
    except Exception as exc:
        logger.warning("Stripe webhook rejected (signature/payload): %s", exc)
        return HttpResponse(status=400)

    if event.get("type") != "checkout.session.completed":
        return HttpResponse(status=200)

    session = event["data"]["object"]
    session_id = session.get("id")

    if session.get("payment_status") != "paid":
        logger.warning("Stripe session %s completed but payment_status=%s",
                       session_id, session.get("payment_status"))
        return HttpResponse(status=200)

    try:
        _fulfil_card_order(session)
    except Exception:
        # a concurrent duplicate delivery already created it
        if Order.objects.filter(stripe_session_id=session_id).exists():
            return HttpResponse(status=200)
        logger.exception("Failed to create order for Stripe session %s", session_id)
        return HttpResponse(status=500)  # Stripe will retry

    return HttpResponse(status=200)

def checkout_success_page(request):
    return render(request, "store/checkout_success.html")

# ---------------------------
# ADMIN ORDERS -- 
# ---------------------------
@staff_member_required 
def admin_orders(request):
    if request.method == "POST":
        action = request.POST.get("action")
        order_id = request.POST.get("order_id")
        order = get_object_or_404(Order, id=order_id)

        if order.status != "pending":
            return redirect("admin_orders")

        if action == "accept":
            with transaction.atomic():
                for item in order.items.select_related("variant"):
                    variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)

                    if variant.available_quantity() < item.quantity:
                        messages.error(request, f"Not enough stock for {variant}")
                        return redirect("admin_orders")

                    variant.stock -= item.quantity
                    variant.save()

                order.status = "accepted"
                order.save()
                transaction.on_commit(lambda: send_order_email(order))

        elif action == "deny":
            order.status = "denied"
            order.comment = request.POST.get("comment", "")
            order.save()
            send_order_email(order)

        return redirect("admin_orders")

    status_filter = request.GET.get("status", "pending")

    orders = Order.objects.prefetch_related("items__variant__product")

    if status_filter == "accepted":
        orders = orders.filter(status="accepted").order_by("-created_at")
    elif status_filter == "denied":
        orders = orders.filter(status="denied").order_by("-created_at")
    else:
        orders = orders.filter(status="pending").order_by("created_at")

    paginator = Paginator(orders, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "store/admin_orders.html", {
        "orders": page_obj,
        "page_obj": page_obj,
        "status_filter": status_filter,
    })