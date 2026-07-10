from django import forms
from django.utils import timezone

class DiscountForm(forms.Form):
    discount_percent = forms.IntegerField(
        min_value=1, max_value=90,
        widget=forms.NumberInput(attrs={
            "class": "border rounded px-3 py-2 w-24"
        })
    )
    discount_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            "type": "datetime-local",
            "class": "border rounded px-3 py-2"
        })
    )
    discount_end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            "type": "datetime-local",
            "class": "border rounded px-3 py-2"
        })
    )

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("discount_start"), cleaned.get("discount_end")
        if start and end:
            if end <= start:
                raise forms.ValidationError("End date/time must be after the start date/time.")
            if end < timezone.now():
                raise forms.ValidationError("End date/time is in the past.")
        return cleaned