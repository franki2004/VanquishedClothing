from django.db import models
import os
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=50, unique=True, editable=False)

    price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(default=0)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    is_limited = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products",
    )

    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_sold_out(self):
        return not self.variants.filter(stock__gt=0).exists()

    @property
    def final_price(self):
        if self.discount_percent:
            return self.price * (100 - self.discount_percent) / 100
        return self.price


class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ("XS", "XS"),
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("2XL", "2XL"),
    ]

    product = models.ForeignKey(
        Product,
        related_name="variants",
        on_delete=models.CASCADE,
    )

    size = models.CharField(
        max_length=5,
        choices=SIZE_CHOICES,
    )

    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "size")
        ordering = ["size"]

    def __str__(self):
        return f"{self.product.name} - {self.size}"
    
def product_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    product_name = slugify(instance.product.name)
    order = instance.order or 0

    return f"products/{product_name}/{order}/vanquished{ext}"

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=product_image_path)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.name} [{self.order}]"
    
