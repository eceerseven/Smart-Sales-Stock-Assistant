from django import forms

class SalesDataForm(forms.Form):
    start_month = forms.DateField(
        label="Başlangıç Ayı / Start Month",
        widget=forms.DateInput(attrs={'type': 'month', 'class': 'form-control'}),
        input_formats=['%Y-%m']
    )
    end_month = forms.DateField(
        label="Bitiş Ayı / End Month",
        widget=forms.DateInput(attrs={'type': 'month', 'class': 'form-control'}),
        input_formats=['%Y-%m']
    )
    sales_excel = forms.FileField(
        label="Satış Verisi (Excel .xlsx)",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text="Lütfen Excel (.xlsx) formatında dosya yükleyin."
    )
    target_excel = forms.FileField(
        label="Hedef Verisi (Excel .xlsx)",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text="Lütfen Excel (.xlsx) formatında dosya yükleyin."
    )
