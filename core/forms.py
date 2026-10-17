from django import forms
from .models import Area, Category

class ReportFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Search', widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Search report titles'}))
    area = forms.ModelChoiceField(queryset=Area.objects.none(), required=False, empty_label='All areas', widget=forms.Select(attrs={'class':'form-select'}))
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, empty_label='All categories', widget=forms.Select(attrs={'class':'form-select'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All statuses'), ('reported','Reported'), ('in_progress','In Progress'), ('problem_fixed','Problem Fixed'), ('resolved','Resolved'), ('closed','Closed')], widget=forms.Select(attrs={'class':'form-select'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['area'].queryset = Area.objects.all()
        self.fields['category'].queryset = Category.objects.all()
