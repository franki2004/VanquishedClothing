from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, Product, ProductImage, ProductVariant, Tag
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction 
from orders.forms import AddToCartForm
from orders.views import get_or_create_cart
from orders.models import CartItem

SIZES = ["XS", "S", "M", "L", "XL", "2XL"]

def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'categories': categories})


def returns(request):
    return render(request, 'store/returns.html')

def collection(request, slug=None):
    category = None
    products = Product.objects.filter(status="active")

    # Category filtering
    if slug:
        category = get_object_or_404(Category, slug=slug)
        products = products.filter(category=category)

    # Sorting
    sort = request.GET.get("sort")

    if sort == "price_asc":
        products = products.order_by("price")
    elif sort == "price_desc":
        products = products.order_by("-price")
    elif sort == "az":
        products = products.order_by("name")
    elif sort == "za":
        products = products.order_by("-name")
    elif sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "oldest":
        products = products.order_by("created_at")

    categories = Category.objects.all()

    return render(
        request,
        "store/collection.html",
        {
            "category": category,
            "products": products,
            "categories": categories,
            "active_filter": "category"
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

    if request.method == "POST":
        form = AddToCartForm(request.POST, product=product)

        if form.is_valid():
            variant = form.cleaned_data["variant"]
            cart = get_or_create_cart(request)

            item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
            )

            if not created:
                item.quantity += 1
                item.save()

            return redirect("cart")
    else:
        form = AddToCartForm(product=product)

    return render(
        request,
        "store/product.html",
        {
            "product": product,
            "form": form,
        },
    )

def new_products(request):
    products = Product.objects.filter(
        status="active"
    ).order_by("-created_at")
    
    sort = request.GET.get("sort")

    if sort == "price_asc":
        products = products.order_by("price")
    elif sort == "price_desc":
        products = products.order_by("-price")
    elif sort == "az":
        products = products.order_by("name")
    elif sort == "za":
        products = products.order_by("-name")
    elif sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "oldest":
        products = products.order_by("created_at")

    return render(
        request,
        "store/collection.html",
        {
            "title": "New",
            "products": products,
            "active_filter": "new"
        },
    )

def sale_products(request):
    products = Product.objects.filter(
        status="active",
        discount_percent__gt=0,
    )

    sort = request.GET.get("sort")

    if sort == "price_asc":
        products = products.order_by("price")
    elif sort == "price_desc":
        products = products.order_by("-price")
    elif sort == "az":
        products = products.order_by("name")
    elif sort == "za":
        products = products.order_by("-name")
    elif sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "oldest":
        products = products.order_by("created_at")

    return render(
        request,
        "store/collection.html",
        {
            "title": "Sale",
            "products": products,
            "active_filter": "sale"
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

    if request.method == "POST":
        names = request.POST.getlist("name")
        prices = request.POST.getlist("price")
        discounts = request.POST.getlist("discount_percent")
        products = []

        with transaction.atomic():
            for idx, name in enumerate(names):
                price = prices[idx]
                discount_raw = discounts[idx] if idx < len(discounts) else ""
                discount = int(discount_raw) if discount_raw.strip() else 0

                category_id = request.POST.get(f"category_{idx}")
                category = Category.objects.get(id=category_id) if category_id else None

                product = Product.objects.create(
                    name=name,
                    slug=name.replace(" ", "-").lower(),
                    price=price,
                    category=category,
                    discount_percent=discount,
                    status="draft",
                )
                product.sku = f"P{product.pk:06d}"
                product.save(update_fields=["sku"])
                products.append(product)

                # Tags
                tag_ids = request.POST.getlist(f"tags_{idx}")
                if tag_ids:
                    product.tags.set(tag_ids)

                # Variants
                for size in SIZES:
                    stock_value = request.POST.get(f"stock_{size}_{idx}", "0").strip()
                    stock = int(stock_value) if stock_value.isdigit() else 0
                    ProductVariant.objects.create(product=product, size=size, stock=stock)

                # Images with order
                files = request.FILES.getlist(f"images_{idx}")
                orders = request.POST.getlist(f"image_order_{idx}[]")
                for i, f in enumerate(files):
                    order = int(orders[i]) if i < len(orders) else i
                    ProductImage.objects.create(product=product, image=f, order=order)

        return redirect("draft_products")

    return render(request, "store/add_products.html", {
        "categories": categories,
        "tags": tags,
        "sizes": SIZES,
    })

@staff_member_required
@require_POST
def add_to_draft(request, id):
    product = get_object_or_404(Product, id=id)

    if product.status == "active":
        product.status = "draft"
        product.save(update_fields=["status"])

    return redirect("draft_products")

@staff_member_required
def draft_products(request):

    if request.method == "POST":
        ids = request.POST.getlist("selected_products")
        action = request.POST.get("action")

        products = Product.objects.filter(id__in=ids)

        if action == "activate":
            products.update(status="active")

        elif action == "archive":
            products.update(status="archived")

        elif action == "delete":
            products.delete()

    context = {
        "active_products": Product.objects.filter(status="active"),
        "drafts": Product.objects.filter(status="draft"),
        "archived_products": Product.objects.filter(status="archived"),
    }

    return render(request, "store/draft_products.html", context)

@staff_member_required
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)

    # Prepare selected tags for template
    selected_tag_ids = list(product.tags.values_list("id", flat=True))

    if request.method == "POST":
        # Update basic fields
        product.name = request.POST.get("name", product.name)
        product.price = request.POST.get("price", product.price)
        product.discount_percent = request.POST.get("discount_percent", product.discount_percent)
        category_id = request.POST.get("category")
        if category_id:
            product.category_id = int(category_id)
        product.save()

        existing_variants = {v.size: v for v in product.variants.all()}

        for size in SIZES:
            stock_value = request.POST.get(f"stock_{size}")
            if stock_value is not None:
                if size in existing_variants:
                    variant = existing_variants[size]
                    variant.stock = int(stock_value) if stock_value else 0
                    variant.save()
                else:
                    stock = int(stock_value) if stock_value else 0
                    if stock > 0:
                        ProductVariant.objects.create(product=product, size=size, stock=stock)

        # Update tags
        tag_ids = request.POST.getlist("tags")
        product.tags.set(tag_ids)

        # Delete images marked for deletion
        images_to_delete = request.POST.get("images_to_delete", "")
        if images_to_delete:
            ids = [int(i) for i in images_to_delete.split(",") if i]
            ProductImage.objects.filter(id__in=ids, product=product).delete()

        # Update order of existing images
        for img in product.images.all():
            order = request.POST.get(f"image_order_{img.id}")
            if order is not None:
                img.order = int(order)
                img.save(update_fields=["order"])

        # Handle new uploaded images
        image_files = request.FILES.getlist("images")
        for i, img in enumerate(image_files):
            order = request.POST.get(f"new_image_order_{i}", i)
            ProductImage.objects.create(product=product, image=img, order=int(order))

        return redirect("draft_products")
    
    variant_stocks = {v.size: v.stock for v in product.variants.all()}

    return render(
        request,
        "store/edit_product.html",
        {
            "product": product,
            "categories": Category.objects.all(),
            "tags": Tag.objects.all(),
            "sizes": SIZES,
            "variant_stocks": variant_stocks,
            "images": product.images.all(),
            "selected_tag_ids": selected_tag_ids,
        },
    )

