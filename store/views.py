from django.shortcuts import render, get_object_or_404
from .models import Category, Product
from django.http import JsonResponse
from django.db.models import Q

def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'categories': categories})

def collection(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_active=True)
    return render(request, 'store/collection.html', {
        'category': category,
        'products': products
    })

def search(request):
    q = request.GET.get("q", "").strip()

    products = (
        Product.objects
        .filter(
            Q(name__icontains=q) |
            Q(tags__name__icontains=q),
            is_active=True
        )
        .distinct()
        if q else Product.objects.none()
    )

    return render(request, "store/search.html", {
        "query": q,
        "products": products,
    })

def product_detail(request, id):
    product = get_object_or_404(Product, id=id, is_active=True)
    return render(request, 'store/product.html', {'product': product})

def new_products(request):
    products = Product.objects.filter(is_active=True).order_by('-date_created')
    return render(request, 'store/collection.html', {
        'title': 'New',
        'products': products
    })

def sale_products(request):
    products = Product.objects.filter(is_active=True, discounted=True)
    return render(request, 'store/collection.html', {
        'title': 'Sale',
        'products': products
    })

def search_suggestions(request):
    q = request.GET.get("q", "").strip()

    if len(q) < 2:
        return JsonResponse([], safe=False)

    products = (
        Product.objects
        .filter(
            Q(name__icontains=q) |
            Q(tags__name__icontains=q),
            is_active=True
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
            "price": p.price
        })

    return JsonResponse(data, safe=False)