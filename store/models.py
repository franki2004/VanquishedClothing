from django.db import models
from django.db import models

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
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    quantity_sold = models.PositiveIntegerField(default=0)
    discounted = models.BooleanField(default=False)
    discounted_percent = models.PositiveIntegerField(default=0)  # 0–90
    limited = models.BooleanField(default=False)
    sold_out = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_sold_out = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    def __str__(self):
        return self.name
    def save(self, *args, **kwargs):
        if not self.sku:
            last = Product.objects.order_by('-id').first()
            self.sku = f"P{(last.id + 1) if last else 1:05d}"
        super().save(*args, **kwargs)



class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    order = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.product.name} image {self.order}"