from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.core.cache import cache
from django.template.loader import render_to_string
from django.conf import settings
from .tokens import account_activation_token


def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)

    link = request.build_absolute_uri(
        reverse("activate", kwargs={"uidb64": uid, "token": token})
    )

    expiry_days = settings.PASSWORD_RESET_TIMEOUT // 86400

    html_content = render_to_string(
        "accounts/activation_email.html",
        {"link": link, "expiry_days": expiry_days},
    )

    text_content = (
        "Welcome to Vanquished Clothing!\n\n"
        "Activate your account using the link below:\n"
        f"{link}\n\n"
        f"This link is valid for {expiry_days} day(s).\n"
        "If you didn't create this account, you can ignore this email."
    )

    email = EmailMultiAlternatives(
        "Activate your Vanquished account",
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()


RESEND_COOLDOWN_SECONDS = 60

def can_send_activation(user):
    """True if no activation email was sent to this user in the last minute."""
    return cache.add(f"activation_cooldown:{user.pk}", True, RESEND_COOLDOWN_SECONDS)