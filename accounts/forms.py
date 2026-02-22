from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
import re
User = get_user_model()


TAILWIND_INPUT_CLASSES = "w-full border border-gray-300 rounded px-3 py-2 mt-1 focus:outline-none focus:ring-2 focus:ring-blue-500"

class PasswordInputPreserve(forms.PasswordInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("render_value", True)
        super().__init__(*args, **kwargs)

class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=PasswordInputPreserve(attrs={"class": TAILWIND_INPUT_CLASSES, "autocomplete": "new-password"}),
        min_length=8,
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=PasswordInputPreserve(attrs={"class": TAILWIND_INPUT_CLASSES, "autocomplete": "new-password"}),
        min_length=8,
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password']
        widgets = {
            'email': forms.EmailInput(attrs={"class": TAILWIND_INPUT_CLASSES}),
        }

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
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": TAILWIND_INPUT_CLASSES}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": TAILWIND_INPUT_CLASSES}))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user is None:
                raise ValidationError("Invalid email or password")
            if not user.is_active:
                raise ValidationError("This account is inactive")
            cleaned_data['user'] = user
        return cleaned_data