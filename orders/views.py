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
# CHECKOUT ------------ NEEDS DELIVERY FEE FIXES
# ---------------------------
@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")

    subtotal = sum((item.total_price for item in items), Decimal("0.00"))
    delivery_fee = Decimal("5.00") if 0 < subtotal < 100 else Decimal("0.00")
    total = subtotal + delivery_fee

    addresses = request.user.addresses.all()
    selected_address = addresses.filter(is_default=True).first() or addresses.first()

    if request.method == "POST":
        customer_form = CustomerForm(request.POST)

        address_id = request.POST.get("address_id")
        address_instance = None
        if address_id and address_id.isdigit():
            address_instance = request.user.addresses.filter(id=int(address_id)).first()

        address_form = AddressForm(request.POST or None, instance=address_instance)

        action = request.POST.get("address_action")

        # ---------------------------
        # SAVE ADDRESS
        # ---------------------------
        if action == "save":
            if address_form.is_valid():
                addr = address_form.save(commit=False)
                addr.user = request.user
                addr.save()
                return redirect("checkout")
            # if invalid, fall through to render with errors

        # ---------------------------
        # DELETE ADDRESS
        # ---------------------------
        elif action == "delete":
            if address_instance:
                address_instance.delete()
            return redirect("checkout")

        # ---------------------------
        # PLACE ORDER
        # ---------------------------
        elif action == "order":
            if not customer_form.is_valid() or not address_instance:
                if not address_instance:
                    customer_form.add_error(None, "Please select or add a valid address.")
                # Render with errors
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

            payment_method = request.POST.get("payment_method")
            first_name = customer_form.cleaned_data["first_name"]
            last_name = customer_form.cleaned_data["last_name"]
            phone = customer_form.cleaned_data["phone"]
            full_name = f"{first_name} {last_name}"

            cod_fee = Decimal("0.00")
            if payment_method == "cod":
                cod_fee = (subtotal * COD_PERCENT).quantize(Decimal("0.01"))

            total_with_fees = (subtotal + delivery_fee + cod_fee).quantize(Decimal("0.01"))

            # ---------------------------
            # CARD PAYMENT
            # ---------------------------
            if payment_method == "card":
                with transaction.atomic():
                    for item in items.select_for_update():
                        variant = item.variant
                        if variant.available_quantity() < item.quantity:
                            customer_form.add_error(None, f"Not enough stock for {variant}")
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

                        ProductVariantReservation.objects.create(
                            variant=variant,
                            user=request.user,
                            quantity=item.quantity,
                            reserved_until=timezone.now() + timedelta(minutes=RESERVATION_MINUTES)
                        )

                # BUILD STRIPE LINE ITEMS
                line_items = [
                    {
                        "price_data": {
                            "currency": "eur",
                            "product_data": {
                                "name": f"{item.variant.product.name} - {item.variant.size}"
                            },
                            "unit_amount": int(item.variant.product.final_price * 100),
                        },
                        "quantity": item.quantity,
                    }
                    for item in items
                ]

                # ADD DELIVERY FEE AS SEPARATE ITEM
                if delivery_fee > 0:
                    line_items.append({
                        "price_data": {
                            "currency": "eur",
                            "product_data": {
                                "name": "Delivery Fee"
                            },
                            "unit_amount": int(delivery_fee * 100),
                        },
                        "quantity": 1,
                    })

                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    success_url=request.build_absolute_uri(reverse("checkout_success_page")),
                    cancel_url=request.build_absolute_uri(reverse("checkout")),
                    metadata={
                        "user_id": request.user.id,
                        "address_id": address_instance.id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": phone,
                        "city": address_instance.city,
                        "postal_code": address_instance.postal_code,
                        "street": address_instance.address_line,
                        "country": address_instance.country,
                        "delivery_fee": str(delivery_fee),
                    }
                )

                return redirect(session.url)

            # ---------------------------
            # COD PAYMENT
            # ---------------------------
            else:
                with transaction.atomic():
                    for item in items.select_for_update():
                        variant = item.variant
                        if variant.available_quantity() < item.quantity:
                            customer_form.add_error(None, f"Not enough stock for {variant}")
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

                    order = Order.objects.create(
                        user=request.user,
                        full_name=full_name,
                        phone=phone,
                        city=address_instance.city,
                        postal_code=address_instance.postal_code,
                        street=address_instance.address_line,
                        country=address_instance.country,
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
    # GET REQUEST
    # ---------------------------
    else:
        customer_form = CustomerForm(initial={
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "phone": getattr(request.user, "phone_number", "")
        })
        address_form = AddressForm()

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

        user_id = metadata.get("user_id")
        session_key = metadata.get("session_key")

        user = None
        if user_id:
            user = User.objects.filter(id=user_id).first()

        cart = None
        if user:
            cart = Cart.objects.filter(user=user).first()
        elif session_key:
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
                    user=user if user else None,
                    session_key=session_key if not user else None,
                    reserved_until__gt=timezone.now()
                ).first()

                if not reservation or reservation.quantity < item.quantity:
                    continue

                variant.stock -= item.quantity
                variant.save()

                reservation.delete()
                subtotal += item.total_price

            order = Order.objects.create(
                user=user,
                full_name=(
                    f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip()
                    or metadata.get("name")
                ),
                phone=metadata.get("phone"),
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

            # cleanup reservations
            ProductVariantReservation.objects.filter(
                user=user if user else None,
                session_key=session_key if not user else None
            ).delete()

            cart.items.all().delete()

    return HttpResponse(status=200)

def checkout_guest(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")

    subtotal = sum((item.total_price for item in items), Decimal("0.00"))
    delivery_fee = Decimal("5.00") if 0 < subtotal < 100 else Decimal("0.00")
    total = subtotal + delivery_fee

    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        city = request.POST.get("city")
        postal_code = request.POST.get("postal_code")
        street = request.POST.get("street")
        payment_method = request.POST.get("payment_method")

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        # ---------------------------
        # CARD (RESERVE STOCK + STRIPE)
        # ---------------------------
        if payment_method == "card":
            with transaction.atomic():
                for item in items.select_for_update():
                    variant = item.variant

                    if variant.available_quantity() < item.quantity:
                        return redirect("cart")

                    ProductVariantReservation.objects.create(
                        variant=variant,
                        session_key=session_key,
                        quantity=item.quantity,
                        reserved_until=timezone.now() + timedelta(minutes=RESERVATION_MINUTES)
                    )

            # BUILD LINE ITEMS (INCLUDING DELIVERY)
            line_items = [
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": f"{item.variant.product.name} - {item.variant.size}"
                        },
                        "unit_amount": int(item.variant.product.final_price * 100),
                    },
                    "quantity": item.quantity,
                }
                for item in items
            ]

            if delivery_fee > 0:
                line_items.append({
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": "Delivery Fee"
                        },
                        "unit_amount": int(delivery_fee * 100),
                    },
                    "quantity": 1,
                })

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=request.build_absolute_uri(reverse("checkout_success_page")),
                cancel_url=request.build_absolute_uri(reverse("checkout")),
                metadata={
                    "session_key": session_key,
                    "name": name,
                    "phone": phone,
                    "city": city,
                    "postal_code": postal_code,
                    "street": street,
                    "delivery_fee": str(delivery_fee),
                }
            )

            return redirect(session.url)

        # ---------------------------
        # COD (DIRECT ORDER)
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
                    full_name=name,
                    phone=phone,
                    city=city,
                    postal_code=postal_code,
                    street=street,
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    total=total,
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

    return render(request, "store/checkout_guest.html", {
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
    })

def checkout_success_page(request):
    return render(request, "store/checkout_success.html")

# ---------------------------
# ADMIN ORDERS
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