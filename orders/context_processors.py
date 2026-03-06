from .views import get_or_create_cart
from django.db.models import Sum

def cart_count(request):
    try:
        cart = get_or_create_cart(request)
        count = cart.items.aggregate(total=Sum("quantity"))["total"] or 0
    except:
        count = 0

    return {"cart_count": count}