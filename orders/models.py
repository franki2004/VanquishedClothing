from django.db import models
from django.conf import settings
from store.models import ProductVariant
from datetime import timedelta
from django.utils import timezone
from store.models import ProductVariant

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("denied", "Denied"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # SNAPSHOT (IMMUTABLE)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    street = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    additional_info = models.TextField(blank=True)
    email = models.EmailField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cod_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=10, choices=[
        ("card", "Card"),
        ("cod", "Cash on Delivery"),
    ])

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    RETURN_WINDOW_DAYS = 14

    @property
    def return_deadline(self):
        if not self.delivered_at:
            return None
        return self.delivered_at + timedelta(days=self.RETURN_WINDOW_DAYS)

    @property
    def can_request_return(self):
        deadline = self.return_deadline
        return (
            self.status == "completed"
            and deadline is not None
            and timezone.now() <= deadline
        )

    @property
    def returnable_items(self):
        return [i for i in self.items.all() if not i.return_requested]

    @property
    def any_return_requested(self):
        return any(i.return_requested for i in self.items.all())

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

    RETURN_STATUS_CHOICES = [
        ("requested", "Return requested"),
        ("approved", "Return approved"),
        ("rejected", "Return declined"),
        ]
    return_status = models.CharField(
        max_length=10, choices=RETURN_STATUS_CHOICES, blank=True, default=""
    )
    return_admin_comment = models.TextField(blank=True)
    
    class Meta:
        unique_together = ("order", "variant")

    @property
    def total_price(self):
        return self.quantity * self.price_snapshot


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "store.ProductVariant",
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "variant")

    @property
    def total_price(self):
        return self.variant.product.final_price * self.quantity