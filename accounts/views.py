from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
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
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "accounts/dashboard.html", {"orders": orders})