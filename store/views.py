from django.shortcuts import render, get_object_or_404
from .models import Category, Product

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
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query, is_active=True) if query else []
    return render(request, 'store/search.html', {
        'query': query,
        'products': products
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