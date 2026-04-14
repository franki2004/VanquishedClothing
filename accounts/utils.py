from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .tokens import account_activation_token

def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)

    link = request.build_absolute_uri(
        reverse("activate", kwargs={"uidb64": uid, "token": token})
    )

    html_content = f"""
<div style="font-family:Arial,sans-serif;background:#fff;color:#000;padding:40px;text-align:center;">

    <h1 style="font-size:20px;letter-spacing:2px;text-transform:uppercase;margin-bottom:20px;">
        Vanquished Clothing
    </h1>

    <h2 style="font-size:18px;margin-bottom:10px;">
        Welcome
    </h2>

    <p style="font-size:14px;max-width:420px;margin:20px auto;line-height:1.6;">
        Your account has been created successfully. Activate it to unlock your profile, orders, and store access.
    </p>

    <a href="{link}"
       style="
       display:inline-block;
       padding:14px 24px;
       border:1px solid #000;
       color:#000;
       text-decoration:none;
       font-size:12px;
       letter-spacing:2px;
       text-transform:uppercase;
       ">
        Activate Account
    </a>

    <p style="margin-top:30px;font-size:11px;color:#555;">
        If you did not create this account, ignore this email.
    </p>

</div>
"""

    email = EmailMultiAlternatives(
        "Activate your account",
        "Activate your account using the link.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()