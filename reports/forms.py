
from django import forms

from core.models import Area, Category
from .models import Report


class ReportCreateForm(forms.ModelForm):

    class Meta:
        model = Report

        fields = [
            "title",
            "category",
            "area",
            "description",
            "location_text",
            "latitude",
            "longitude",
            "before_image",
        ]

        labels = {
            "before_image": "Photo of the problem",
        }

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Large pothole on Road 5",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "area": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_area",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                }
            ),

            "location_text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Dhanmondi 27, Dhaka",
                    "id": "id_location_text",
                    "autocomplete": "street-address",
                }
            ),

            "latitude": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.000001",
                    "id": "id_latitude",
                }
            ),

            "longitude": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.000001",
                    "id": "id_longitude",
                }
            ),

            "before_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

        help_texts = {
            "before_image": "JPG, PNG or WEBP, up to 5 MB.",
            "latitude": "Click the map to fill this in.",
            "longitude": "Click the map to fill this in.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = (
            Category.objects.all().order_by("name")
        )

        self.fields["area"].queryset = (
            Area.objects.all().order_by("name")
        )

        self.fields["category"].empty_label = (
            "Select a problem category"
        )

        self.fields["area"].empty_label = (
            "Select your area"
        )

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if len(title) < 5:
            raise forms.ValidationError(
                "Please give the report a more descriptive "
                "title (at least 5 characters)."
            )

        return title


class VerificationForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ("verified", "Verify Report"),
            ("rejected", "Reject Report"),
        ]
    )

    remarks = forms.CharField(
        widget=forms.Textarea,
        required=False,
    )


class ReportStatusForm(forms.ModelForm):
    class Meta:
        model = Report

        fields = [
            "operational_status",
            "after_image",
            "resolution_note",
        ]

        widgets = {
            "resolution_note": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

