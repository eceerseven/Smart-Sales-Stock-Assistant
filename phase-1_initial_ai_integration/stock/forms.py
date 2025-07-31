from django import forms

class StokForm(forms.Form):
    stok_dosyasi = forms.FileField(
        label="Stok Excel Dosyası | Stock Excel File",
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
