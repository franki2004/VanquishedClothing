from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ProductVariant, CartItem, Cart
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
    return render(request, "store/cart.html", {"cart": cart})


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)

    try:
        item = cart.items.get(id=item_id)
    except CartItem.DoesNotExist:
        return redirect("cart")

    action = request.POST.get("action")

    if action == "increase":
        if item.quantity < item.variant.stock:
            item.quantity += 1
            item.save()

    elif action == "decrease":
        item.quantity -= 1
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()

    return redirect("cart")