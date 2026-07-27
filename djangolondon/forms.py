from django import forms

from djangolondon.models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ["name"]
        labels = {"name": "Your name"}


class EntryEmailForm(forms.ModelForm):
    email = forms.EmailField(label="Your email address")

    class Meta:
        model = Entry
        fields = ["email"]
