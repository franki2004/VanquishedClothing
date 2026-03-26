from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("collection/", views.collection, name="collection"),
    path("collection/new/", views.collection, {"filter_type": "new"}, name="new_products"),
    path("collection/sale/", views.collection, {"filter_type": "sale"}, name="sale_products"),
    path("collection/<slug:slug>/", views.collection, name="collection"),
    path('search/', views.search, name='search'),
    path('product/<int:id>/', views.product_detail, name='product'),
    path("search/suggestions/", views.search_suggestions, name="search_suggestions"),
    path('returns', views.returns, name='returns'),
    path("add-products/", views.bulk_add_products, name="bulk_add_products"),
    path("drafts/", views.draft_products, name="draft_products"),
    path("product/<int:id>/add-draft/", views.add_to_draft, name="add_to_draft"),
    path("product/<int:id>/edit/", views.edit_product, name="edit_product"),
]