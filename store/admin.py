from django.contrib import admin
from .models import (
    Category,
    Tag,
    Product,
    ProductVariant,
    ProductImage,
    ProductVariantReservation,
)


# ---------------------------
# CATEGORY
# ---------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


# ---------------------------
# TAG
# ---------------------------
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


# ---------------------------
# PRODUCT IMAGE INLINE
# ---------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


# ---------------------------
# PRODUCT VARIANT INLINE
# ---------------------------
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("size", "stock")


# ---------------------------
# PRODUCT
# ---------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "status",
        "price",
        "discount_percent",
        "final_price_display",
        "category",
        "is_limited",
        "created_at",
    )

    list_filter = (
        "status",
        "category",
        "is_limited",
        "created_at",
    )

    search_fields = (
        "name",
        "sku",
    )

    readonly_fields = (
        "sku",
        "created_at",
        "final_price_display",
    )

    prepopulated_fields = {"slug": ("name",)}

    inlines = [ProductVariantInline, ProductImageInline]

    def final_price_display(self, obj):
        return obj.final_price
    final_price_display.short_description = "Final Price"


# ---------------------------
# PRODUCT VARIANT
# ---------------------------
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "size",
        "stock",
        "available_quantity_display",
    )

    list_filter = (
        "size",
        "product__category",
    )

    search_fields = (
        "product__name",
    )

    def available_quantity_display(self, obj):
        return obj.available_quantity()
    available_quantity_display.short_description = "Available"


# ---------------------------
# PRODUCT IMAGE
# ---------------------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "order",
    )

    list_filter = ("product",)
    ordering = ("product", "order")


# ---------------------------
# RESERVATIONS
# ---------------------------
@admin.register(ProductVariantReservation)
class ProductVariantReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "variant",
        "user",
        "session_key",
        "quantity",
        "reserved_until",
        "is_expired",
    )

    list_filter = (
        "reserved_until",
        "variant__product",
    )

    search_fields = (
        "variant__product__name",
        "user__email",
        "session_key",
    )

    readonly_fields = ("reserved_at",)

    ordering = ("-reserved_until",)

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True