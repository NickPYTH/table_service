import datetime

from django import forms
from django.core.exceptions import ValidationError

from .models import Table, Column, Cell, RowPermission, Row


class RowPermissionForm(forms.ModelForm):
    class Meta:
        model = RowPermission
        fields = ['user', 'can_edit']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'can_edit': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['title']


class ColumnForm(forms.ModelForm):
    class Meta:
        model = Column
        fields = ['name', 'data_type']
        widgets = {
            'data_type': forms.Select(choices=Column.ColumnType.choices)
        }


class ShareTableForm(forms.Form):
    email = forms.EmailField(label="User Email")
    can_edit = forms.BooleanField(
        label="Can Edit",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_delete = forms.BooleanField(
        label="Can Delete",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


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
                field_name = f'col_{column.id}'
                if column.data_type == Column.ColumnType.INTEGER:
                    self.fields[field_name] = forms.IntegerField(
                        label=column.name,
                        required=False,
                        initial=initial_value,
                        widget=forms.NumberInput(attrs={'class': 'form-control'}),
                    )
                elif column.data_type == Column.ColumnType.FLOAT:
                    self.fields[field_name] = forms.FloatField(
                        label=column.name,
                        required=False,
                        initial=initial_value,
                        widget=forms.NumberInput(attrs={'class': 'form-control'}),
                    )
                elif column.data_type == Column.ColumnType.BOOLEAN:
                    self.fields[field_name] = forms.BooleanField(
                        label=column.name,
                        required=False,
                        initial=initial_value,
                    )
                elif column.data_type == Column.ColumnType.DATE:
                    self.fields[field_name] = forms.DateField(
                        label=column.name,
                        required=False,
                        initial=str(initial_value),
                        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                    )
                else:  # TEXT по умолчанию
                    self.fields[field_name] = forms.CharField(
                        label=column.name,
                        required=False,
                        initial=initial_value,
                        widget=forms.TextInput(attrs={'class': 'form-control'}),
                    )

    def clean(self):
        cleaned_data = super().clean()

        for field_name, value in cleaned_data.items():
            column_id = int(field_name.split('_')[1])
            column = Column.objects.get(id=column_id)
            value_type = type(value)
            if column.data_type == Column.ColumnType.FLOAT:
                if value_type is not float:
                    self.add_error(column, ValidationError('Invalid value', code='Должно быть float числом'))
            elif column.data_type == Column.ColumnType.INTEGER:
                if value_type is not int:
                    self.add_error(column, ValidationError('Invalid value', code='Должно быть int числом'))
            elif column.data_type == Column.ColumnType.BOOLEAN:
                if value_type is not bool:
                    self.add_error(column, ValidationError('Invalid value', code='Должно быть true/false'))
            elif column.data_type == Column.ColumnType.DATE:
                pass  # Пока не реализовано
