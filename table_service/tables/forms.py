from django import forms
from .models import Table, Column, Cell, RowPermission


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['title']


class ColumnForm(forms.ModelForm):
    class Meta:
        model = Column
        fields = ['name']


class CellForm(forms.ModelForm):
    class Meta:
        model = Cell
        fields = ['value']


class ShareTableForm(forms.Form):
    email = forms.EmailField()
    can_edit = forms.BooleanField(required=False, initial=True)
