from django import forms
from .models import ProductVariant

class AddToCartForm(forms.Form):
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None
    )

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product:
            # include ALL sizes
            self.fields["variant"].queryset = product.variants.all()

    def clean_variant(self):
        variant = self.cleaned_data["variant"]
        if variant.stock <= 0:
            raise forms.ValidationError("This size is out of stock.")
        return variant