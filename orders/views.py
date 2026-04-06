from django.urls import reverse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.paginator import Paginator
from decimal import Decimal
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

User = get_user_model()

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

    # ---------------------------
    # POST
    # ---------------------------
    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        customer_form = CustomerForm(request.POST)

        if user:
            # Address handling for logged-in users
            address_id = request.POST.get("address_id")
            address_instance = (
                addresses.filter(id=int(address_id)).first()
                if address_id and address_id.isdigit()
                else None
            )

            address_form = AddressForm(request.POST or None, instance=address_instance)
            action = request.POST.get("address_action", "order")

            if action == "save" and address_form.is_valid():
                addr = address_form.save(commit=False)
                addr.user = user
                addr.save()
                return redirect("checkout")

            if action == "delete" and address_instance:
                address_instance.delete()
                return redirect("checkout")

            if not customer_form.is_valid() or not address_instance:
                if not address_instance:
                    customer_form.add_error(None, "Select address.")
                return render(request, "store/checkout.html", {
                    "items": items,
                    "subtotal": subtotal,
                    "delivery_fee": delivery_fee,
                    "total": total,
                    "addresses": addresses,
                    "selected_address": selected_address,
                    "customer_form": customer_form,
                    "address_form": address_form,
                })

            first_name = customer_form.cleaned_data["first_name"]
            last_name = customer_form.cleaned_data["last_name"]
            phone = customer_form.cleaned_data["phone"]
            email = customer_form.cleaned_data["email"]  # <-- added
            addr_info = address_instance

        else:
            # Guest checkout
            if not customer_form.is_valid():
                return render(request, "store/checkout.html", {
                    "items": items,
                    "subtotal": subtotal,
                    "delivery_fee": delivery_fee,
                    "total": total,
                    "addresses": [],
                    "selected_address": None,
                    "customer_form": customer_form,
                    "address_form": None,
                })

            first_name = customer_form.cleaned_data["first_name"]
            last_name = customer_form.cleaned_data["last_name"]
            phone = customer_form.cleaned_data["phone"]
            email = customer_form.cleaned_data["email"]  # <-- added
            addr_info = type("Addr", (), {
                "city": request.POST.get("city"),
                "postal_code": request.POST.get("postal_code"),
                "address_line": request.POST.get("street"),
                "country": request.POST.get("country"),
            })()

        full_name = f"{first_name} {last_name}"

        cod_fee = Decimal("0.00")
        if payment_method == "cod":
            cod_fee = (subtotal * COD_PERCENT).quantize(Decimal("0.01"))

        total_with_fees = (subtotal + delivery_fee + cod_fee).quantize(Decimal("0.01"))

        # ---------------------------
        # CARD (STRIPE)
        # ---------------------------
        if payment_method == "card":
            with transaction.atomic():
                for item in items.select_for_update():
                    variant = item.variant
                    if variant.available_quantity() < item.quantity:
                        return redirect("cart")

                    ProductVariantReservation.objects.create(
                        variant=variant,
                        user=user if user else None,
                        session_key=session_key if not user else None,
                        quantity=item.quantity,
                        reserved_until=timezone.now() + timedelta(minutes=RESERVATION_MINUTES)
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
                "user_id": str(user.id) if user else "",
                "session_key": session_key if not user else "",
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "email": email,  # <-- added
                "city": addr_info.city,
                "postal_code": addr_info.postal_code,
                "street": addr_info.address_line,
                "country": getattr(addr_info, "country", ""),
                "delivery_fee": str(delivery_fee),
                "address_id": str(addr_info.id) if user else "",
            }

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=request.build_absolute_uri(reverse("checkout_success_page")),
                cancel_url=request.build_absolute_uri(reverse("checkout")),
                metadata=metadata
            )
            return redirect(session.url)

        # ---------------------------
        # COD
        # ---------------------------
        else:
            with transaction.atomic():
                for item in items.select_for_update():
                    variant = item.variant
                    if variant.available_quantity() < item.quantity:
                        return redirect("cart")
                    variant.stock -= item.quantity
                    variant.save()

                order = Order.objects.create(
                    user=user,
                    full_name=full_name,
                    phone=phone,
                    email=email,  # <-- added
                    city=addr_info.city,
                    postal_code=addr_info.postal_code,
                    street=addr_info.address_line,
                    country=getattr(addr_info, "country", ""),
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    cod_fee=cod_fee,
                    total=total_with_fees,
                    payment_method="cod",
                    status="pending"
                )

                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        variant=item.variant,
                        quantity=item.quantity,
                        price_snapshot=item.variant.product.final_price
                    )

                cart.items.all().delete()
                return redirect("checkout_success_page")

    # ---------------------------
    # GET
    # ---------------------------
    customer_form = CustomerForm(initial={
        "first_name": getattr(user, "first_name", ""),
        "last_name": getattr(user, "last_name", ""),
        "phone": getattr(user, "phone_number", ""),
        "email": getattr(user, "email", "")
    } if user else None)
    address_form = AddressForm() if user else None

    return render(request, "store/checkout.html", {
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "addresses": addresses,
        "selected_address": selected_address,
        "customer_form": customer_form,
        "address_form": address_form,
    })

# ---------------------------
# STRIPE WEBHOOK
# ---------------------------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})

        user_id = metadata.get("user_id") or None
        session_key = metadata.get("session_key") or None

        user = User.objects.filter(id=user_id).first() if user_id else None

        if user:
            cart = Cart.objects.filter(user=user).first()
        else:
            cart = Cart.objects.filter(session_key=session_key).first()

        if not cart:
            return HttpResponse(status=200)

        items = cart.items.select_related("variant__product")

        with transaction.atomic():
            subtotal = Decimal("0.00")

            for item in items.select_for_update():
                variant = item.variant

                reservation = ProductVariantReservation.objects.filter(
                    variant=variant,
                    reserved_until__gt=timezone.now()
                ).filter(
                    Q(user=user) | Q(session_key=session_key)
                ).first()

                if not reservation or reservation.quantity < item.quantity:
                    continue

                variant.stock -= item.quantity
                variant.save()

                reservation.delete()
                subtotal += item.total_price

            order = Order.objects.create(
                user=user,
                full_name=f"{metadata.get('first_name','')} {metadata.get('last_name','')}".strip(),
                phone=metadata.get("phone"),
                email=metadata.get("email") or "",  # <-- added
                street=metadata.get("street"),
                city=metadata.get("city"),
                postal_code=metadata.get("postal_code"),
                country=metadata.get("country"),
                subtotal=subtotal,
                delivery_fee=Decimal(metadata.get("delivery_fee", "0.00")),
                total=Decimal(session["amount_total"]) / 100,
                payment_method="card",
                status="accepted"
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    price_snapshot=item.variant.product.final_price
                )

            ProductVariantReservation.objects.filter(
                Q(user=user) | Q(session_key=session_key)
            ).delete()

            cart.items.all().delete()

    return HttpResponse(status=200)

def checkout_success_page(request):
    return render(request, "store/checkout_success.html")

# ---------------------------
# ADMIN ORDERS -- needs deny fix
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

        elif action == "deny":
            order.status = "denied"
            order.comment = request.POST.get("comment", "")
            order.save()

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