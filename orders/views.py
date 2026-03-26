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
from .forms import CustomerForm
from django.core.paginator import Paginator

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

COD_PERCENT = Decimal("0.03")

@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("variant__product")
    subtotal = sum((item.total_price for item in items), Decimal("0.00"))
    delivery_fee = Decimal("5.00") if subtotal < 100 and subtotal > 0 else Decimal("0.00")
    total = subtotal + delivery_fee

    addresses = request.user.addresses.all()
    selected_address = addresses.filter(is_default=True).first() or addresses.first()

    if request.method == "POST":
        customer_form = CustomerForm(request.POST)
        address_id = request.POST.get("address_id")
        address_instance = request.user.addresses.filter(id=address_id).first() if address_id else None
        address_form = AddressForm(request.POST, instance=address_instance)

        # Determine action
        action = request.POST.get("address_action")

        # Save or update address
        if action == "save":
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                address.save()
                return redirect("checkout")
            else:
                selected_address = address_instance or selected_address

        # Delete address
        elif action == "delete":
            addr = address_instance
            if addr:
                addr.delete()
            return redirect("checkout")

        # Place order
        elif action == "order":
            if not customer_form.is_valid() or not address_instance:
                selected_address = address_instance or selected_address
            else:
                payment_method = request.POST.get("payment_method")
                first_name = customer_form.cleaned_data["first_name"]
                last_name = customer_form.cleaned_data["last_name"]
                phone = customer_form.cleaned_data["phone"]
                full_name = f"{first_name} {last_name}"

                cod_fee = Decimal("0.00")
                if payment_method == "cod":
                    cod_fee = (subtotal * COD_PERCENT).quantize(Decimal("0.01"))

                total_with_fees = (subtotal + delivery_fee + cod_fee).quantize(Decimal("0.01"))

                # Card payment: reserve stock, create order, stripe session
                if payment_method == "card":
                    with transaction.atomic():
                        # check stock
                        for item in items:
                            if item.variant.quantity < item.quantity:
                                customer_form.add_error(None, f"Not enough stock for {item.variant.product.name}")
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

                        # create order
                        order = Order.objects.create(
                            user=request.user,
                            full_name=full_name,
                            phone=phone,
                            city=address_instance.city,
                            postal_code=address_instance.postal_code,
                            street=address_instance.address_line,
                            subtotal=subtotal,
                            delivery_fee=delivery_fee,
                            cod_fee=cod_fee,
                            total=total_with_fees,
                            payment_method=payment_method,
                            status="accepted"
                        )

                        for item in items:
                            OrderItem.objects.create(
                                order=order,
                                variant=item.variant,
                                quantity=item.quantity,
                                price_snapshot=item.variant.product.final_price
                            )
                            # reduce stock
                            item.variant.quantity -= item.quantity
                            item.variant.save()

                        cart.items.all().delete()

                    # Stripe checkout session
                    line_items = []
                    for item in order.items.all():
                        line_items.append({
                            "price_data": {
                                "currency": "eur",
                                "product_data": {"name": item.variant.product.name},
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

                # COD order
                else:
                    order = Order.objects.create(
                        user=request.user,
                        full_name=full_name,
                        phone=phone,
                        city=address_instance.city,
                        postal_code=address_instance.postal_code,
                        street=address_instance.address_line,
                        subtotal=subtotal,
                        delivery_fee=delivery_fee,
                        cod_fee=cod_fee,
                        total=total_with_fees,
                        payment_method=payment_method,
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
                    return redirect("order-success", order.id)

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

    status_filter = request.GET.get("status", "pending")

    orders = Order.objects.prefetch_related("items__variant__product")

    if status_filter == "accepted":
        orders = orders.filter(status="accepted").order_by("-created_at")
    elif status_filter == "denied":
        orders = orders.filter(status="denied").order_by("-created_at")
    else:
        orders = orders.filter(status="pending").order_by("created_at")

    paginator = Paginator(orders, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "store/admin_orders.html", {
        "orders": page_obj,
        "page_obj": page_obj,
        "status_filter": status_filter,
    })