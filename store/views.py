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
from django.core.paginator import Paginator
from django.db.models import Prefetch
import json
from django.contrib import messages
from .forms import DiscountForm

SIZES = ["XS", "S", "M", "L", "XL", "2XL"]

def apply_filters(request, products):
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    sizes = request.GET.getlist("size")
    if sizes:
        products = products.filter(
            variants__size__in=sizes,
            variants__stock__gt=0
        ).distinct()

    selected_sizes = sizes

    limited = request.GET.get("limited")
    if limited == "true":
        products = products.filter(is_limited=True)

    discount = request.GET.get("discount")
    if discount:
        products = products.filter(discount_percent__gte=discount)

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

    return products, selected_sizes


def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'categories': categories})


def returns(request):
    return render(request, 'store/returns.html')

def collection(request, slug=None, filter_type=None):
    category = None
    products = Product.objects.filter(status="active")

    if filter_type == "new":
        products = products.order_by("-created_at")
        active_filter = "new"
        title = "New"

    elif filter_type == "sale":
        products = products.filter(discount_percent__gt=0)
        active_filter = "sale"
        title = "Sale"

    elif slug:
        category = get_object_or_404(Category, slug=slug)
        products = products.filter(category=category)
        active_filter = "category"
        title = category.name
    else:
        active_filter = "category"
        title = "All"

    products, selected_sizes = apply_filters(request, products)

    paginator = Paginator(products, 42)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, "store/collection.html", {
        "category": category,
        "title": title,
        "products": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "active_filter": active_filter,
        "selected_sizes": selected_sizes,
        "sizes": SIZES
    })

def search(request):
    q = request.GET.get("q", "").strip()

    base_qs = Product.objects.filter(status="active")

    if q:
        base_qs = base_qs.filter(
            Q(name__icontains=q) |
            Q(tags__name__icontains=q)
        ).distinct()
    else:
        base_qs = Product.objects.none()

    products, selected_sizes = apply_filters(request, base_qs)

    paginator = Paginator(products, 42)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "store/collection.html", {
        "products": page_obj,
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "selected_sizes": selected_sizes,
        "sizes": SIZES,
        "title": f"Search: {q}",
        "active_filter": "search",
        "query": q,
        "category": None,
    })

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

            available = variant.available_quantity()
            item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

            if not created:
                if item.quantity < available:
                    item.quantity += 1
                    item.save()
            else:
                if available > 0:
                    item.quantity = 1
                    item.save()

            return redirect("cart")
    else:
        form = AddToCartForm(product=product)

    # --- Reviews ---
    reviews_qs = product.reviews.select_related("user").order_by("-created_at")
    paginator = Paginator(reviews_qs, 10)
    page_number = request.GET.get("page", 1)
    reviews_page = paginator.get_page(page_number)

    user_review = None
    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()
    related_products = product.get_related_products(limit=15)
    return render(
        request,
        "store/product.html",
        {
            "product": product,
            "form": form,
            "reviews_page": reviews_page,
            "user_review": user_review,
            "related_products": related_products,
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
def add_product(request):
    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        discount = request.POST.get("discount_percent") or 0

        category_id = request.POST.get("category")
        category = (
            Category.objects.get(id=category_id)
            if category_id
            else None
        )

        with transaction.atomic():
            product = Product.objects.create(
                name=name,
                slug=name.replace(" ", "-").lower(),
                price=price,
                category=category,
                discount_percent=discount,
                status="draft",
            )

            product.tags.set(
                request.POST.getlist("tags")
            )

            product.related_products.set(
                request.POST.getlist("related_products")
            )

            for size in SIZES:
                stock = request.POST.get(
                    f"stock_{size}",
                    "0"
                )

                ProductVariant.objects.create(
                    product=product,
                    size=size,
                    stock=int(stock) if stock else 0
                )

            files = request.FILES.getlist("images")

            for i, image in enumerate(files):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    order=i
                )

        return redirect("draft_products")

    return render(
        request,
        "store/add_product.html",
        {
            "categories": categories,
            "tags": tags,
            "sizes": SIZES,
        },
    )

@staff_member_required
def related_products_search(request):
    q = request.GET.get("q", "").strip()
    page = int(request.GET.get("page", 1))

    qs = Product.objects.order_by("-id")

    if q:
        qs = qs.filter(name__icontains=q)

    qs = qs.prefetch_related(
        Prefetch("images", queryset=ProductImage.objects.order_by("order"))
    )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page)

    products = [
        {
            "id": p.id,
            "name": p.name,
            "image": (
                p.images.first().image.url
                if p.images.exists()
                else ""
            ),
        }
        for p in page_obj.object_list
    ]

    return JsonResponse({
        "products": products,
        "page": page_obj.number,
        "pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
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
    product = get_object_or_404(
        Product.objects.prefetch_related("images", "related_products", "tags", "variants"),
        id=id
    )

    selected_tag_ids = list(product.tags.values_list("id", flat=True))
    selected_related_ids = list(product.related_products.values_list("id", flat=True))

    selected_related_products = list(
    product.related_products.values("id", "name")
)

    if request.method == "POST":
        product.name = request.POST.get("name", product.name)
        product.price = request.POST.get("price", product.price)
        product.discount_percent = request.POST.get(
            "discount_percent", product.discount_percent
        )

        category_id = request.POST.get("category")
        product.category_id = category_id or None
        product.save()

        # tags
        product.tags.set(request.POST.getlist("tags"))

        # related products
        product.related_products.set(request.POST.getlist("related_products"))

        # variants
        existing_variants = {v.size: v for v in product.variants.all()}

        for size in SIZES:
            stock_value = request.POST.get(f"stock_{size}", "0")
            stock_value = int(stock_value) if stock_value else 0

            if size in existing_variants:
                v = existing_variants[size]
                v.stock = stock_value
                v.save(update_fields=["stock"])
            elif stock_value > 0:
                ProductVariant.objects.create(
                    product=product,
                    size=size,
                    stock=stock_value
                )

        # DELETE IMAGES
        delete_ids = request.POST.get("images_to_delete", "")
        if delete_ids:
            ids = [int(x) for x in delete_ids.split(",") if x.strip()]
            ProductImage.objects.filter(product=product, id__in=ids).delete()

        # REORDER EXISTING IMAGES (FROM DRAG & DROP)
        order = request.POST.get("existing_image_order")
        if order:
            try:
                ids = json.loads(order)

                for index, img_id in enumerate(ids):
                    ProductImage.objects.filter(
                        id=img_id,
                        product=product
                    ).update(order=index)

            except Exception:
                pass

        # UPDATE EXISTING IMAGE ORDER INPUTS (fallback legacy, optional safe delete)
        for img in product.images.all():
            order_val = request.POST.get(f"image_order_{img.id}")
            if order_val is not None:
                img.order = int(order_val)
                img.save(update_fields=["order"])

        # ADD NEW IMAGES (ORDERED FROM JS)
        new_order_raw = request.POST.get("new_image_order", "[]")

        try:
            new_order = json.loads(new_order_raw)
        except Exception:
            new_order = []

        files = request.FILES.getlist("images")

        for i, file in enumerate(files):
            order = new_order[i] if i < len(new_order) else i

            ProductImage.objects.create(
                product=product,
                image=file,
                order=order
            )

        return redirect("draft_products")

    return render(request, "store/edit_product.html", {
    "product": product,
    "categories": Category.objects.all(),
    "tags": Tag.objects.all(),
    "sizes": SIZES,
    "selected_tag_ids": selected_tag_ids,
    "selected_related_ids": selected_related_ids,
    "selected_related_products": json.dumps(selected_related_products),
    "variant_stocks": {v.size: v.stock for v in product.variants.all()},
    "images": product.images.all(),
})



@staff_member_required
def product_discount_manage(request):
    paginate_by = 10
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    querystring = f"?{request.GET.urlencode()}" if request.GET else ""

    # Build the base queryset (search + filter)
    qs = Product.objects.select_related("category").prefetch_related("tags")

    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(sku__icontains=query)
        ).distinct()

    if category_id:
        qs = qs.filter(category_id=category_id)

    qs = qs.order_by("name")

    if request.method == "POST":
        product_ids = request.POST.getlist("product_ids")
        action = request.POST.get("action")

        if not product_ids:
            messages.error(request, "Select at least one product first.")
            return redirect(request.path + querystring)

        if action == "clear":
            updated = Product.objects.filter(id__in=product_ids).update(
                discount_percent=0, discount_start=None, discount_end=None
            )
            messages.success(request, f"Removed discount from {updated} product(s).")
            return redirect(request.path + querystring)

        form = DiscountForm(request.POST)
        if form.is_valid():
            updated = Product.objects.filter(id__in=product_ids).update(
                discount_percent=form.cleaned_data["discount_percent"],
                discount_start=form.cleaned_data["discount_start"],
                discount_end=form.cleaned_data["discount_end"],
            )
            messages.success(request, f"Discount applied to {updated} product(s).")
            return redirect(request.path + querystring)

        messages.error(request, "Please fix the errors below.")
    else:
        form = DiscountForm()

    paginator = Paginator(qs, paginate_by)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "query": query,
        "selected_category": category_id,
        "form": form,
    }
    return render(request, "store/discount_manage.html", context)