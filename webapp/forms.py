from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from core.models import Address, Review

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=False, max_length=15)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field-input"


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["label", "street", "city", "state", "pincode", "is_default"]
        widgets = {
            "label": forms.TextInput(attrs={"placeholder": "Home, Work..."}),
            "street": forms.TextInput(attrs={"placeholder": "Street address"}),
            "city": forms.TextInput(attrs={"placeholder": "City"}),
            "state": forms.TextInput(attrs={"placeholder": "State"}),
            "pincode": forms.TextInput(attrs={"placeholder": "PIN code"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_default":
                field.widget.attrs["class"] = "field-input"


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("card", "Card"),
        ("upi", "UPI"),
        ("wallet", "Wallet"),
    ]
    address = forms.ModelChoiceField(queryset=Address.objects.none(), empty_label=None)
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)
    special_instructions = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "field-input"})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["address"].queryset = Address.objects.filter(user=user)
        self.fields["address"].widget.attrs["class"] = "field-input"
        self.fields["payment_method"].widget.attrs["class"] = "field-input"


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5, "class": "field-input"}),
            "comment": forms.Textarea(attrs={"rows": 3, "class": "field-input"}),
        }
