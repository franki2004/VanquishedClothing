from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
import re
from django.urls import reverse
from .models import Address
from django.core.validators import RegexValidator
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .models import Review
from django.conf import settings

User = get_user_model()

TAILWIND_INPUT_CLASSES = "w-full border border-gray-300  px-3 py-2 mt-1 focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"

class PasswordInputPreserve(forms.PasswordInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("render_value", True)
        super().__init__(*args, **kwargs)

class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=PasswordInputPreserve(attrs={"class": TAILWIND_INPUT_CLASSES, "autocomplete": "new-password", "placeholder" : "Enter a safe password"}),
        min_length=8,
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=PasswordInputPreserve(attrs={"class": TAILWIND_INPUT_CLASSES, "autocomplete": "new-password", "placeholder" : "Repeat the safe password"}),
        min_length=8,
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password']
        widgets = {
            'email': forms.EmailInput(attrs={"class": TAILWIND_INPUT_CLASSES, "placeholder" : "Enter a valid email"}),
        }

    
    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email:
            raise forms.ValidationError("Email is required.")

        email = email.strip().lower()

        if User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "This email is already registered. Please log in instead."
            )

        if User.objects.filter(email__iexact=email, is_active=False).exists():
            raise forms.ValidationError(
                "This account is awaiting activation. "
                "Please request another activation email."
            )

        return email

    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")

        if password:
            if len(password) < 8:
                self.add_error('password', "Password must be at least 8 characters")
            if not re.search(r'[A-Z]', password):
                self.add_error('password', "Password must contain at least 1 uppercase letter")
            if not re.search(r'[a-z]', password):
                self.add_error('password', "Password must contain at least 1 lowercase letter")
            if not re.search(r'\d', password):
                self.add_error('password', "Password must contain at least 1 number")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": TAILWIND_INPUT_CLASSES,
        "placeholder": "Enter registered email",
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": TAILWIND_INPUT_CLASSES,
        "placeholder": "Enter your password",
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if not email or not password:
            return cleaned_data

        email = email.strip().lower()

        user = User.objects.filter(email__iexact=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                 raise ValidationError(
                    "Your account is awaiting email activation. "
                    "Check your inbox, or resend the activation email below.",
                    code="account_inactive",
                )

            authenticated_user = authenticate(
                email=email,
                password=password,
            )

            if authenticated_user is not None:
                cleaned_data["user"] = authenticated_user
                return cleaned_data

        raise ValidationError("Invalid email or password.")

    

class UserFieldUpdateForm(forms.ModelForm):
    field_name = None

    phone_validator = RegexValidator(
        regex=r'^\+?[0-9]{7,15}$',
        message="Enter a valid phone number"
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone_number"]

    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop("field_name", None)
        super().__init__(*args, **kwargs)

        for field in list(self.fields.keys()):
            if field != self.field_name:
                self.fields.pop(field)

        for field in ["first_name", "last_name", "phone_number"]:
            if field in self.fields:
                self.fields[field].required = False

    def clean_email(self):
        value = self.cleaned_data["email"]
        if not value or "@" not in value:
            raise ValidationError("Invalid email")
        return value

    def clean_first_name(self):
        value = self.cleaned_data.get("first_name", "")
        if value and len(value) < 2:
            raise ValidationError("Too short")
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get("last_name", "")
        if value and len(value) < 2:
            raise ValidationError("Too short")
        return value

    def clean_phone_number(self):
        value = self.cleaned_data.get("phone_number", "")
        if value:
            self.phone_validator(value)
        return value
    



from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "address_line",
            "city",
            "postal_code",
            "country",
            "is_default",
        ]

        widgets = {
            "address_line": forms.TextInput(attrs={
                "id": "modalAddress",
                "class": "border  w-full px-3 py-2",
                "placeholder": "Street, number, entrance, floor..."
            }),
            "city": forms.TextInput(attrs={
                "id": "modalCity",
                "class": "border  w-full px-3 py-2",
                "placeholder": "City"
            }),
            "postal_code": forms.TextInput(attrs={
                "id": "modalPostal",
                "class": "border  w-full px-3 py-2",
                "placeholder": "Postal Code"
            }),
            "country": forms.TextInput(attrs={
                "id": "modalCountry",
                "class": "border  w-full px-3 py-2",
                "placeholder": "Country"
            }),
            "is_default": forms.CheckboxInput(attrs={
                "class": "mr-2"
            }),
        }

    def clean_address_line(self):
        value = self.cleaned_data.get("address_line", "").strip()
        if len(value) < 5:
            raise forms.ValidationError("Address is too short.")
        return value

    def clean_city(self):
        value = self.cleaned_data.get("city", "").strip()
        if len(value) < 2:
            raise forms.ValidationError("City is too short.")
        return value


class StyledPasswordResetForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({
            "class": TAILWIND_INPUT_CLASSES,
            "placeholder": "Enter a registered email"
        })

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")

        if password:
            errors = []
            if len(password) < 8:
                errors.append("Password must be at least 8 characters")
            if not re.search(r'[A-Z]', password):
                errors.append("Password must contain at least 1 uppercase letter")
            if not re.search(r'[a-z]', password):
                errors.append("Password must contain at least 1 lowercase letter")
            if not re.search(r'\d', password):
                errors.append("Password must contain at least 1 number")
            if errors:
                raise forms.ValidationError(errors)
        return password

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email,
                  html_email_template_name=None):

        uid = context["uid"]
        token = context["token"]

        # SAFE FIX: use site domain from context (NOT request)
        domain = context.get("domain", "127.0.0.1:8000")
        protocol = context.get("protocol", "http")

        reset_link = f"{protocol}://{domain}/account/reset/{uid}/{token}/"

        expiry_days = settings.PASSWORD_RESET_TIMEOUT // 86400

        html = render_to_string(
            "accounts/password_reset_email.html",
            {
                "link": reset_link,
                "email": to_email,
                "expiry_days": expiry_days,
            }
        )

        text = (
            "Reset your Vanquished password\n\n"
            "We received a request to reset the password for "
            f"{to_email}. Use the link below to choose a new one:\n"
            f"{reset_link}\n\n"
            f"This link is valid for {expiry_days} day(s).\n"
            "If you didn't request this, you can ignore this email."
        )

        msg = EmailMultiAlternatives(
            subject="Reset your Vanquished password",
            body=text,
            from_email=from_email,
            to=[to_email],
        )

        msg.attach_alternative(html, "text/html")
        msg.send()


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["new_password1"].widget.attrs.update({
            "class": TAILWIND_INPUT_CLASSES
        })
        self.fields["new_password2"].widget.attrs.update({
            "class": TAILWIND_INPUT_CLASSES
        })

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }