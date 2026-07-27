from django import forms

from djangolondon.models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ["name"]
        labels = {"name": "Your name"}
