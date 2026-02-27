from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from .forms import UserFieldUpdateForm

from orders.models import Order
from .forms import LoginForm, RegisterForm

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

    if request.method == "POST":
        field = request.POST.get("field")
        allowed_fields = ["email", "first_name", "last_name", "phone_number"]

        if field in allowed_fields:
            form = UserFieldUpdateForm(
                request.POST,
                instance=user,
                field_name=field
            )

            if form.is_valid():
                form.save()
                return redirect("account_dashboard")
            else:
                form_errors = form.errors
                active_field = field

    orders = user.orders.prefetch_related("items__variant__product")

    return render(request, "accounts/dashboard.html", {
        "orders": orders,
        "form_errors": form_errors,
        "active_field": active_field
    })