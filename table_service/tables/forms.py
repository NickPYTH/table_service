from django import forms
from .models import Table, Column, Cell, RowPermission, Row


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


class RowEditForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.row = kwargs.pop('row', None)
        super().__init__(*args, **kwargs)

        if self.row:
            for column in self.row.table.columns.all():
                cell = self.row.cells.filter(column=column).first()
                if cell:
                    initial_value = cell.value
                else:
                    initial_value = ''

                self.fields[f'col_{column.id}'] = forms.CharField(
                    label=column.name,
                    required=False,
                    initial=initial_value,
                    widget=forms.TextInput(attrs={'class': 'form-control'}))
