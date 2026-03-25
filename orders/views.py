from django.views.decorators.http import require_POST
from .models import CartItem, Cart, Order, OrderItem
from store.models import ProductVariant
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from accounts.forms import AddressForm
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import stripe

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    if not request.session.session_key:
        request.session.create()

    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key
    )
    return cart

def cart_view(request):
    cart = get_or_create_cart(request)

    items = cart.items.select_related("variant__product")

    subtotal = sum((item.total_price for item in items), Decimal("0.00"))

    delivery_fee = Decimal("5.00") if subtotal < 100 and subtotal > 0 else Decimal("0.00")
    total = subtotal + delivery_fee

    context = {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "free_delivery_threshold": 100,
        "remaining_for_free_delivery": max(0, 100 - subtotal),
    }

    return render(request, "store/cart.html", context)


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)

    try:
        item = cart.items.select_related("variant").get(id=item_id)
    except CartItem.DoesNotExist:
        return redirect("cart")

    action = request.POST.get("action")

    if action == "increase":
        item.quantity = min(item.quantity + 1, item.variant.stock)

    elif action == "decrease":
        item.quantity -= 1

    if item.quantity <= 0:
        item.delete()
    else:
        item.save()

    return redirect("cart")

@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    COD_PERCENT = Decimal("0.03")

    if request.method == "POST":

        action = request.POST.get("address_action")

        # SAVE ADDRESS
        if action == "save":
            address_id = request.POST.get("address_id")
            instance = request.user.addresses.filter(id=address_id).first() if address_id else None

            form = AddressForm(request.POST, instance=instance)

            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                address.save()
            return redirect("checkout")

        # DELETE ADDRESS
        if action == "delete":
            address_id = request.POST.get("address_id")
            addr = request.user.addresses.filter(id=address_id).first()
            if addr:
                addr.delete()
            return redirect("checkout")

        # CREATE ORDER
        if action == "order":

            addr = request.user.addresses.filter(id=request.POST.get("address_id")).first()
            if not addr:
                return redirect("checkout")

            payment_method = request.POST.get("payment_method")

            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            phone = request.POST.get("phone", "").strip()

            if not first_name or not last_name or not phone:
                return redirect("checkout")

            full_name = f"{first_name} {last_name}"

            items = cart.items.select_related("variant__product")

            subtotal = sum((item.total_price for item in items), Decimal("0.00"))
            delivery_fee = Decimal("5.00") if subtotal < 100 and subtotal > 0 else Decimal("0.00")

            cod_fee = Decimal("0.00")
            if payment_method == "cod":
                cod_fee = (subtotal * COD_PERCENT).quantize(Decimal("0.01"))

            total = (subtotal + delivery_fee + cod_fee).quantize(Decimal("0.01"))

            order = Order.objects.create(
                user=request.user,
                full_name=full_name,
                phone=phone,
                city=addr.city,
                postal_code=addr.postal_code,
                street=addr.address_line,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                cod_fee=cod_fee,
                total=total,
                payment_method=payment_method,
                status="pending"
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    price_snapshot=item.variant.product.final_price,
                )

            cart.items.all().delete()

            if payment_method == "card":

                with transaction.atomic():

                    # CHECK + RESERVE STOCK
                    for item in items:
                        variant = item.variant

                        if variant.quantity < item.quantity:
                            return redirect("checkout")  # or show error

                    # CREATE ORDER FIRST
                    order = Order.objects.create(
                        user=request.user,
                        full_name=full_name,
                        phone=phone,
                        city=addr.city,
                        postal_code=addr.postal_code,
                        street=addr.address_line,
                        additional_info="",

                        subtotal=subtotal,
                        delivery_fee=delivery_fee,
                        cod_fee=cod_fee,
                        total=total,
                        payment_method=payment_method,

                        status="accepted"  # CRITICAL
                    )

                    for item in items:
                        OrderItem.objects.create(
                            order=order,
                            variant=item.variant,
                            quantity=item.quantity,
                            price_snapshot=item.variant.product.final_price,
                        )

                    # DECREASE STOCK IMMEDIATELY
                    for item in items:
                        variant = item.variant
                        variant.quantity -= item.quantity
                        variant.save()

                    cart.items.all().delete()

                # STRIPE SESSION AFTER STOCK LOCK
                line_items = []
                for item in order.items.all():
                    line_items.append({
                        "price_data": {
                            "currency": "eur",
                            "product_data": {
                                "name": item.variant.product.name,
                            },
                            "unit_amount": int(item.price_snapshot * 100),
                     },
                        "quantity": item.quantity,
                    })

                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    success_url=request.build_absolute_uri(f"/order-success/{order.id}/"),
                    cancel_url=request.build_absolute_uri("/checkout/"),
                )

                return redirect(session.url)

    items = cart.items.select_related("variant__product")

    subtotal = sum((item.total_price for item in items), Decimal("0.00"))
    delivery_fee = Decimal("5.00") if subtotal < 100 and subtotal > 0 else Decimal("0.00")
    total = subtotal + delivery_fee

    addresses = request.user.addresses.all()
    selected_address = request.user.addresses.filter(is_default=True).first() or addresses.first()

    return render(request, "store/checkout.html", {
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "addresses": addresses,
        "selected_address": selected_address,
    })

def checkout_guest(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        address = request.POST.get("address")

        cart = get_or_create_cart(request)

        # create order (adjust to your Order model)
        Order.objects.create(
            name=name,
            email=email,
            address=address,
            total_price=cart.total_price
        )

        cart.items.all().delete()

        return redirect("success")

    return render(request, "store/checkout_guest.html")

def stripe_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    line_items = [{
        "price_data": {
            "currency": "eur",
            "product_data": {"name": item.product.name},
            "unit_amount": int(item.price * 100),  # in cents
        },
        "quantity": item.quantity,
    } for item in order.items.all()]

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri(f"/order-success/{order.id}/"),
        cancel_url=request.build_absolute_uri("/checkout/"),
    )

    return redirect(session.url)

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, "store/order_success.html", {
        "order": order
    })

@staff_member_required
def admin_orders(request):

    if request.method == "POST":
        action = request.POST.get("action")
        order_id = request.POST.get("order_id")

        order = get_object_or_404(Order, id=order_id)

        # prevent double processing
        if order.status != "pending":
            return redirect("admin_orders")

        if action == "accept":

            with transaction.atomic():
                for item in order.items.select_related("variant"):

                    variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)

                    if variant.stock < item.quantity:
                        return redirect("admin_orders")

                    variant.stock -= item.quantity
                    variant.save()

                order.status = "accepted"
                order.save()

        elif action == "deny":
            comment = request.POST.get("comment", "").strip()

            order.status = "denied"
            order.comment = comment
            order.save()

        return redirect("admin_orders")

    orders = Order.objects.prefetch_related("items__variant__product")\
                          .order_by("created_at")  # oldest first

    return render(request, "store/admin_orders.html", {
        "orders": orders
    })