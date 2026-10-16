from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from django.db import transaction

from .models import AuthorityProfile

User = get_user_model()


class BootstrapFormMixin:
    """Adds Bootstrap 5 CSS classes to every widget (and 'is-invalid' on errors)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def is_valid(self):
        valid = super().is_valid()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                if "is-invalid" not in widget.attrs.get("class", ""):
                    widget.attrs["class"] += " is-invalid"
        return valid


# ---------------------------------------------------------------- Registration
class CitizenRegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Citizen sign-up. Subclassing UserCreationForm gives us password validation + hashing."""

    role = User.Role.CITIZEN  # class attribute: the role this form creates

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)  # password already hashed here
        user.role = self.role  # never trust the client for role
        if commit:
            user.save()
        return user


class AuthorityRegistrationForm(CitizenRegistrationForm):
    """Creates User(role=authority) + AuthorityProfile(status=pending) atomically."""

    role = User.Role.AUTHORITY

    department = forms.CharField(max_length=150)
    assigned_area_name = forms.CharField(
        max_length=100, label="Assigned area", help_text="The area your department is responsible for."
    )

    field_order = [
        "username", "first_name", "last_name", "email",
        "department", "assigned_area_name", "password1", "password2",
    ]

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)  # authority always needs a saved user
        AuthorityProfile.objects.create(
            user=user,
            department=self.cleaned_data["department"],
            assigned_area_name=self.cleaned_data["assigned_area_name"],
            # approval_status defaults to 'pending'
        )
        return user


# ---------------------------------------------------------------- Login / password
class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


# ---------------------------------------------------------------- Django admin forms
# Needed because we use a custom user model with the stock UserAdmin.
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "role")


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"