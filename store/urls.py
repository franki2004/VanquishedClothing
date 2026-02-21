from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('collections/new/', views.new_products, name='new_products'),
    path('collections/sale/', views.sale_products, name='sale_products'),
    path('collections/<slug:slug>/', views.collection, name='collection'),
    path('search/', views.search, name='search'),
    path('product/<int:id>/', views.product_detail, name='product'),
    path("search/suggestions/", views.search_suggestions, name="search_suggestions"),
]