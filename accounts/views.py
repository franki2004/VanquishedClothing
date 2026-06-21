from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Review
from store.models import Product
from .forms import UserFieldUpdateForm, AddressForm, LoginForm, RegisterForm, ReviewForm
from django.core.paginator import Paginator
from .utils import send_activation_email
from django.utils.http import urlsafe_base64_decode
from .tokens import account_activation_token
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.urls import reverse

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            send_activation_email(request, user)

            return redirect("activation_sent")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

def activation_sent_view(request):
    return render(request, "accounts/activation_sent.html")

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            
            login(request, form.cleaned_data['user'])
            return redirect('home') 
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect("home")

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        login(request, user)
        return redirect("home")

    return redirect("login")


@login_required
def account_dashboard(request):
    user = request.user
    form_errors = {}
    active_field = None
    active_error = None
    address_form = AddressForm()
    address_action = None
    active_address = None

    if request.method == "POST":

        # USER FIELD UPDATE
        field = request.POST.get("field")
        allowed_fields = ["email", "first_name", "last_name", "phone_number"]

        if field in allowed_fields:
            form = UserFieldUpdateForm(request.POST, instance=user, field_name=field)
            if form.is_valid():
                form.save()
                return redirect("account_dashboard")
            else:
                active_field = field
                active_error = form.errors.get(field, ["Invalid value"])[0]

        # ADDRESS LOGIC
        action = request.POST.get("address_action")

        if action == "save":
            address_id = request.POST.get("address_id")
            instance = user.addresses.filter(id=address_id).first() if address_id else None
            form = AddressForm(request.POST, instance=instance)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = user
                address.save()
                return redirect("account_dashboard")

        elif action == "delete":
            address_id = request.POST.get("address_id")
            address = user.addresses.filter(id=address_id).first()
            if address:
                address.delete()
                return redirect("account_dashboard")

    # ORDERS WITH PAGINATION
    orders_qs = user.orders.prefetch_related("items__variant__product").order_by("-created_at")
    paginator = Paginator(orders_qs, 10)  # 10 orders per page
    page_number = request.GET.get("page")
    orders_page = paginator.get_page(page_number)

    addresses = user.addresses.all()

    return render(request, "accounts/dashboard.html", {
        "orders": orders_page,
        "form_errors": form_errors,
        "active_field": active_field,
        "active_error": active_error,
        "addresses": addresses,
        "address_form": address_form,
        "address_action": address_action,
        "active_address": active_address
    })

def _can_modify(user, review):
    return user.is_staff or user.is_superuser or review.user_id == user.id


@login_required
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.reviews.filter(user=request.user).exists():
        messages.error(request, "You've already reviewed this product.")
        return redirect(f"{reverse('product', args=[product.id])}#reviews")

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, "Your review has been posted.")
    else:
        messages.error(request, "Please choose a rating and write a comment.")

    return redirect(f"{reverse('product', args=[product.id])}#reviews")


@login_required
@require_POST
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if not _can_modify(request.user, review):
        return HttpResponseForbidden("You can't edit this review.")

    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
        form.save()
        messages.success(request, "Your review has been updated.")

    return redirect(f"{reverse('product', args=[review.product_id])}#reviews")


@login_required
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if not _can_modify(request.user, review):
        return HttpResponseForbidden("You can't delete this review.")

    product_id = review.product_id
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect(f"{reverse('product', args=[product_id])}#reviews")