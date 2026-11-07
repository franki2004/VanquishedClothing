from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("variant", "quantity", "price_snapshot", "return_requested",
              "return_status", "return_reason", "return_admin_comment")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "status", "payment_method", "total", "created_at", "delivered_at")
    list_filter = ("status", "payment_method")
    search_fields = ("full_name", "email", "phone")
    inlines = [OrderItemInline]


admin.site.register(OrderItem)