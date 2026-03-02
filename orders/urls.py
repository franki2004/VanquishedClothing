from django.urls import path
from . import views

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/item/<int:item_id>/update/", views.update_cart_item, name="update_cart_item"),
]