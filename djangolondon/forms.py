from django import forms
from django.core.validators import FileExtensionValidator

from djangolondon.models import Entry, Player, Prize


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ["name"]
        labels = {"name": "Your name"}


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["name"]
        labels = {"name": "Your name"}


class PrizeForm(forms.ModelForm):
    """
    Reads an uploaded voucher PDF into the prize's binary field.

    The model field is not editable, so the upload is a form field of its own.
    """

    MAX_VOUCHER_SIZE = 5 * 1024 * 1024

    voucher_upload = forms.FileField(
        label="Voucher",
        required=False,
        validators=[FileExtensionValidator(["pdf"])],
        help_text="PDF, stored in the database. Replaces any current voucher.",
    )

    class Meta:
        model = Prize
        fields = ["order", "name", "description"]

    def clean_voucher_upload(self):
        upload = self.cleaned_data["voucher_upload"]
        if upload is not None and upload.size > self.MAX_VOUCHER_SIZE:
            raise forms.ValidationError("Vouchers must be 5 MB or smaller.")
        return upload

    def save(self, commit=True):
        prize = super().save(commit=False)
        upload = self.cleaned_data["voucher_upload"]
        if upload is not None:
            prize.voucher = upload.read()
            prize.voucher_filename = upload.name
        if commit:
            prize.save()
            self.save_m2m()
        return prize
