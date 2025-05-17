from django import forms

class ItemImportForm(forms.Form):
    file = forms.FileField(label="Chọn file Excel (.xlsx)")
