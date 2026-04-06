from django.urls import path
from . import views

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/item/<int:item_id>/update/", views.update_cart_item, name="update_cart_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout-success/", views.checkout_success_page, name="checkout_success_page"),
    path("admin/orders/", views.admin_orders, name="admin_orders"),
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook")
]