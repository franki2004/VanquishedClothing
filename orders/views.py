from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ProductVariant, CartItem, Cart, Order
from django.shortcuts import render, redirect

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

    subtotal = sum(item.total_price for item in items)

    delivery_fee = 5 if subtotal < 100 and subtotal > 0 else 0
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

def checkout(request):
    if not request.user.is_authenticated:
        return redirect("login")

    return render(request, "store/checkout.html")

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