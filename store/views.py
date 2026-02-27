from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, Product, ProductImage, ProductVariant, Tag
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction 
from django.utils.text import slugify

def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'categories': categories})


def returns(request):
    return render(request, 'store/returns.html')

def collection(request, slug):
    category = get_object_or_404(Category, slug=slug)

    products = Product.objects.filter(
        category=category,
        status="active",
    )

    return render(
        request,
        "store/collection.html",
        {
            "category": category,
            "products": products,
        },
    )
def search(request):
    q = request.GET.get("q", "").strip()

    products = (
        Product.objects.filter(
            Q(name__icontains=q) |
            Q(tags__name__icontains=q),
            status="active",
        ).distinct()
        if q
        else Product.objects.none()
    )

    return render(
        request,
        "store/search.html",
        {
            "query": q,
            "products": products,
        },
    )

def product_detail(request, id):
    if request.user.is_staff:
        product = get_object_or_404(Product, id=id)
    else:
        product = get_object_or_404(
            Product,
            id=id,
            status="active",
        )

    return render(request, "store/product.html", {"product": product})

def new_products(request):
    products = Product.objects.filter(
        status="active"
    ).order_by("-created_at")

    return render(
        request,
        "store/collection.html",
        {
            "title": "New",
            "products": products,
        },
    )

def sale_products(request):
    products = Product.objects.filter(
        status="active",
        discount_percent__gt=0,
    )

    return render(
        request,
        "store/collection.html",
        {
            "title": "Sale",
            "products": products,
        },
    )

def search_suggestions(request):
    q = request.GET.get("q", "").strip()

    if len(q) < 2:
        return JsonResponse([], safe=False)

    products = (
        Product.objects.filter(
            Q(name__icontains=q) |
            Q(tags__name__icontains=q),
            status="active",
        )
        .prefetch_related("images")
        .distinct()[:6]
    )

    data = []
    for p in products:
        image = p.images.first()
        data.append({
            "id": p.id,
            "name": p.name,
            "url": f"/product/{p.id}/",
            "image": image.image.url if image else "",
            "price": str(p.final_price),
        })

    return JsonResponse(data, safe=False)

@staff_member_required
def bulk_add_products(request):
    categories = Category.objects.all()
    tags = Tag.objects.all()
    SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

    if request.method == "POST":
        names = request.POST.getlist("name")
        prices = request.POST.getlist("price")
        category_id = request.POST.get("category")
        category = Category.objects.get(id=category_id) if category_id else None

        products = []

        with transaction.atomic():
            # Create products
            for idx, name in enumerate(names):
                price = prices[idx]
                slug = slugify(name)

                category_id = request.POST.get(f"category_{idx}")
                category = Category.objects.get(id=category_id) if category_id else None

                product = Product.objects.create(
                    name=name,
                    slug=slug,
                    price=price,
                    category=category,
                    status="draft",
                )
                product.sku = f"P{product.pk:06d}"
                product.save(update_fields=["sku"])
                products.append(product)

                # Assign tags
                tag_ids = request.POST.getlist(f"tags_{idx}")
                if tag_ids:
                    product.tags.set(tag_ids)

                # Create variants per size
                for size in SIZES:
                    field_name = f"stock_{size}_{idx}"
                    stock_value = request.POST.get(field_name, "0").strip()
                    stock = int(stock_value) if stock_value.isdigit() else 0
                    ProductVariant.objects.create(
                        product=product,
                        size=size,
                        stock=stock,
                    )

            # Attach images per product
            for idx, product in enumerate(products):
                image_files = request.FILES.getlist(f"images_{idx}")
                for order, img in enumerate(image_files):
                    ProductImage.objects.create(
                        product=product,
                        image=img,
                        order=int(request.POST.get(f"image_order_{idx}_{order}", order))
                    )

        return redirect("bulk_add_products")

    return render(request, "store/add_products.html", {
        "categories": categories,
        "tags": tags,
        "sizes": SIZES,
    })

@staff_member_required
def draft_products(request):
    if request.method == "POST":
        action = request.POST.get("action")
        product_ids = request.POST.getlist("selected_products")
        if product_ids:
            products = Product.objects.filter(id__in=product_ids)
            if action == "activate":
                products.update(status="active")
            elif action == "archive":
                products.update(status="archived")
        return redirect("draft_products")

    drafts = Product.objects.filter(status="draft").order_by("-created_at")
    return render(request, "store/draft_products.html", {"drafts": drafts})