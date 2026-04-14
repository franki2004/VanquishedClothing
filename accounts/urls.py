from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import StyledPasswordResetForm, StyledSetPasswordForm

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("account/", views.account_dashboard, name="account_dashboard"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("activation-sent/", views.activation_sent_view, name="activation_sent"),
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        form_class=StyledPasswordResetForm
    ), name="password_reset"),

    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        form_class=StyledSetPasswordForm
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"
    ), name="password_reset_complete"),
    
]