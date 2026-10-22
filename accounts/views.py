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
import logging
from django.views.decorators.http import require_http_methods

User = get_user_model()
logger = logging.getLogger(__name__)

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        pending_user = User.objects.filter(
            email__iexact=email,
            is_active=False,
        ).first() if email else None

        if pending_user:
            try:
                send_activation_email(request, pending_user)
                messages.success(
                    request,
                    "We've sent another activation email. Please check your inbox."
                )
            except Exception:
                logger.exception(
                    "Failed to resend activation email for pending registration."
                )
                messages.warning(
                    request,
                    "Your account is still awaiting activation. "
                    "We couldn't send the email right now. Please try again later."
                )

            return redirect("activation_sent")

        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            try:
                send_activation_email(request, user)
            except Exception:
                logger.exception("Failed to send activation email.")
                messages.warning(
                    request,
                    "Your account was created, but we couldn't send the "
                    "activation email. You can request another email."
                )

            return redirect("activation_sent")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def resend_activation_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        pending_user = User.objects.filter(
            email__iexact=email,
            is_active=False,
        ).first() if email else None

        if pending_user:
            try:
                send_activation_email(request, pending_user)
            except Exception:
                logger.exception("Failed to send a resent activation email.")

        # Use the same response whether or not a pending account exists.
        messages.success(
            request,
            "If an account with that email is awaiting activation, "
            "an activation email will be sent. Please check your inbox "
            "and spam folder."
        )
        return redirect("activation_sent")

    return render(request, "accounts/resend_activation.html")

def activation_sent_view(request):
    return render(request, "accounts/activation_sent.html")

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            login(request, form.cleaned_data["user"])
            return redirect("home")
    else:
        form = LoginForm()

    show_resend_activation = (
        form.errors.get("__all__")
        and any(
            error.code == "account_inactive"
            for error in form.errors.as_data().get("__all__", [])
        )
    )

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "show_resend_activation": bool(show_resend_activation),
        },
    )


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
    redirect_url = f"{reverse('product', args=[product.id])}#reviews"

    if not product.user_has_purchased(request.user):
        messages.error(request, "Only customers who have purchased this product can leave a review.")
        return redirect(redirect_url)

    if product.reviews.filter(user=request.user).exists():
        messages.error(request, "You've already reviewed this product.")
        return redirect(redirect_url)

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, "Thanks! Your review has been posted.")
    else:
        messages.error(request, "Please choose a rating and write a comment.")

    return redirect(redirect_url)


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