from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Account


class BootstrapFormMixin:
    """Gives every field Bootstrap's form-control (or form-select) class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css_class)


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Public sign-up form. Every account made here is a vehicle OWNER."""

    # Clear messages for empty required fields, shown under each field.
    required_messages = {
        "first_name": "Enter your first name.",
        "last_name": "Enter your last name.",
        "username": "Choose a username.",
        "email": "Enter your email address.",
        "password1": "Enter a password.",
        "password2": "Enter the same password again.",
    }

    class Meta:
        model = Account
        fields = ("first_name", "last_name", "username", "email", "contact_number")
        labels = {"contact_number": "Contact number (optional)"}
        help_texts = {"contact_number": "Digits only, with an optional leading +, e.g. +639171234567."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # First and last name are optional on Django's user model, but required here.
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        for name, message in self.required_messages.items():
            self.fields[name].error_messages["required"] = message

        self.fields["first_name"].widget.attrs["autofocus"] = True
        self.fields["username"].widget.attrs.pop("autofocus", None)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Account.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        # UserCreationForm.save() hashes the password with set_password().
        account = super().save(commit=False)
        account.role = Account.Role.OWNER  # nobody can choose their own role
        if commit:
            account.save()
        return account


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Django's login form with TapPark's error messages."""

    error_messages = {
        "invalid_login": "Invalid username or password.",
        "inactive": "This account has been deactivated. Please contact the parking administrator.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].error_messages["required"] = "Enter your username."
        self.fields["password"].error_messages["required"] = "Enter your password."

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            # Django treats a deactivated account like a wrong password. If the
            # password is actually correct, say the account is deactivated instead.
            username = self.cleaned_data.get("username")
            password = self.cleaned_data.get("password")
            account = Account.objects.filter(username=username).first()
            if account and not account.is_active and account.check_password(password):
                raise forms.ValidationError(self.error_messages["inactive"], code="inactive")
            raise
