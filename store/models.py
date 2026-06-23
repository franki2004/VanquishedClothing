from django.db import models
import os
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.db.models import Avg, Count, Case, When, Value, F, Q

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name
    def __save__(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

class Product(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("active", "Active"), ("archived", "Archived")]
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=50, unique=True, editable=False)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft", db_index=True)
    is_limited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    tags = models.ManyToManyField(Tag, blank=True)
    related_products = models.ManyToManyField(
        'self', blank=True, symmetrical=False, related_name='related_to'
    )

    def get_related_products(self, limit=15):
            manual = list(self.related_products.filter(status="active")[:limit])

            if len(manual) >= limit:
                return manual

            remaining = limit - len(manual)
            exclude_ids = [p.id for p in manual] + [self.id]
            tag_ids = list(self.tags.values_list('id', flat=True))

            # If no tags and no category, can't auto-fill
            if not tag_ids and not self.category:
                return manual

            # Filter: products that share tags OR category with this product
            filter_q = Q()
            if tag_ids:
                filter_q |= Q(tags__in=tag_ids)
            if self.category:
                filter_q |= Q(category=self.category)

            queryset = Product.objects.filter(filter_q).exclude(id__in=exclude_ids).filter(status="active")

            # Annotate shared tags count (only if we have tags to match)
            if tag_ids:
                queryset = queryset.annotate(
                    shared_tags=Count('tags', filter=Q(tags__in=tag_ids), distinct=True)
                )
            else:
                queryset = queryset.annotate(shared_tags=Value(0))

            # Annotate category match (boolean: 1 if matches, 0 if not)
            queryset = queryset.annotate(
                category_match=Case(
                    When(category=self.category, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField()
                )
            )

            # Calculate score: category = 5 points, each tag = 1 point
            queryset = queryset.annotate(
                score=F('category_match') * 5 + F('shared_tags')
            )

            # Fetch and order by score descending
            auto = (
                queryset
                .filter(score__gt=0)
                .order_by('-score', '-id')
                .distinct()[:remaining]
            )

            return manual + list(auto)    
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["slug"])]

    def average_rating(self):
        return self.reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    def review_count(self):
        return self.reviews.count()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) 
        if not self.sku:
            self.sku = f"P{self.pk:06d}"
            super().save(update_fields=["sku"])

    @property
    def is_sold_out(self):
        return not self.variants.filter(stock__gt=0).exists()

    @property
    def final_price(self):
        if self.discount_percent:
            return self.price * (100 - self.discount_percent) / 100
        return self.price

class ProductVariant(models.Model):
    SIZE_CHOICES = [("XS","XS"),("S","S"),("M","M"),("L","L"),("XL","XL"),("2XL","2XL")]
    SIZE_ORDER = {"XS":1,"S":2,"M":3,"L":4,"XL":5,"2XL":6}

    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    size = models.CharField(max_length=5, choices=SIZE_CHOICES)
    stock = models.PositiveIntegerField(default=0)
    size_order = models.PositiveIntegerField(editable=False)

    class Meta:
        unique_together = ("product", "size")
        ordering = ["size_order"]

    def save(self, *args, **kwargs):
        self.size_order = self.SIZE_ORDER[self.size]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.size}"

    def available_quantity(self):
        active_reservations = self.reservations.filter(reserved_until__gt=timezone.now())
        reserved_sum = sum(r.quantity for r in active_reservations)
        return self.stock - reserved_sum

class ProductVariantReservation(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    reserved_at = models.DateTimeField(auto_now_add=True)
    reserved_until = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.reserved_until
    
    def expire(self):
        self.reserved_until = timezone.now()
        self.save()

    def __str__(self):
        owner = self.user or self.session_key
        return f"{owner} reserved {self.quantity} of {self.variant} until {self.reserved_until}"

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
    
    def delete(self, *args, **kwargs):
            if self.image:
                self.image.delete(save=False)
            super().delete(*args, **kwargs)

    
    def save(self, *args, **kwargs):
        try:
            old = ProductImage.objects.get(pk=self.pk)
            if old.image and old.image != self.image:
                old.image.delete(save=False)
        except ProductImage.DoesNotExist:
            pass

        super().save(*args, **kwargs)   
    
    def __str__(self):
        return f"{self.product.name} [{self.order}]"
    
