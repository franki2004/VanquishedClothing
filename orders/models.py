from django.db import models
from django.conf import settings
from store.models import Product  # assuming your Product model is in store app

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user}"

    def update_total(self):
        self.total_price = sum(item.total_price() for item in self.items.all())
        self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)  # snapshot of product price at order
    returned = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(blank=True, null=True)
    exchange_requested = models.BooleanField(default=False)
    exchange_requested_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"

    def total_price(self):
        return self.quantity * self.price