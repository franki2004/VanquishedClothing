from django import forms
from .models import ProductVariant
from django.core.validators import RegexValidator

class AddToCartForm(forms.Form):
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None
    )

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product:
            self.fields["variant"].queryset = product.variants.all()

    def clean_variant(self):
        variant = self.cleaned_data["variant"]
        if variant.stock <= 0:
            raise forms.ValidationError("This size is out of stock.")
        return variant


phone_validator = RegexValidator(
    regex=r'^\+?\d{6,15}$',
    message="Enter a valid phone number."
)

class CustomerForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "border rounded-lg px-4 py-2 w-full",
            "placeholder": "First Name"
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "border rounded-lg px-4 py-2 w-full",
            "placeholder": "Last Name"
        })
    )
    phone = forms.CharField(
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "class": "border rounded-lg px-4 py-2 w-full",
            "placeholder": "Phone Number"
        })
    )

    def clean_first_name(self):
        value = self.cleaned_data.get("first_name", "").strip()
        if len(value) < 2:
            raise forms.ValidationError("First name is too short.")
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get("last_name", "").strip()
        if len(value) < 2:
            raise forms.ValidationError("Last name is too short.")
        return value