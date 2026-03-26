from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import UserFieldUpdateForm, AddressForm
from orders.models import Order
from .forms import LoginForm, RegisterForm
from django.core.paginator import Paginator

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

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