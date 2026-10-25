from django import forms

from .models import Comment, Vote


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Add a comment...",
                    "maxlength": 2000,
                }
            )
        }
        labels = {"text": ""}

    def clean_text(self) -> str:
        text = self.cleaned_data["text"].strip()
        if not text:
            raise forms.ValidationError("Comment cannot be empty.")
        return text


class VoteForm(forms.Form):
    """Validates the submitted vote value (+1 or -1)."""

    vote_value = forms.TypedChoiceField(choices=Vote.Value.choices, coerce=int)