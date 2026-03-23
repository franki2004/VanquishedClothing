from django.urls import path
from . import views

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/item/<int:item_id>/update/", views.update_cart_item, name="update_cart_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/guest/", views.checkout_guest, name="checkout_guest"),
]