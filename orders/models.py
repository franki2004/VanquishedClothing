from django.db import models
from django.conf import settings
from store.models import Product, ProductVariant  # assuming your Product model is in store app

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("denied", "Denied"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
    )

    quantity = models.PositiveIntegerField()
    price_snapshot = models.DecimalField(max_digits=8, decimal_places=2)

    return_requested = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("order", "variant")

    def __str__(self):
        return f"{self.quantity} × {self.variant.product.name} ({self.variant.size})"

    @property
    def total_price(self):
        return self.quantity * self.price_snapshot