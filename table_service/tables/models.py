from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.crypto import get_random_string


class Table(models.Model):
    title = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_token = models.CharField(max_length=32, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = get_random_string(32)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('table_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.title


class Column(models.Model):
    class ColumnType(models.TextChoices):
        TEXT = 'text', 'Текст'
        INTEGER = 'integer', 'Целое число'
        FLOAT = 'float', 'Число с плавающей точкой'
        BOOLEAN = 'boolean', 'Логическое'
        DATE = 'date', 'Дата'

    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    data_type = models.CharField(
        max_length=10,
        choices=ColumnType.choices,
        default=ColumnType.TEXT
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.table.title} - {self.name}"


class Row(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='rows')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    @property
    def cell_values(self):
        if not hasattr(self, '_cell_values_cache'):
            self._cell_values_cache = {
                cell.column_id: cell.value
                for cell in self.cells.all()
            }
        return self._cell_values_cache

    def __str__(self):
        return f"Row {self.order} in {self.table.title}"


class Cell(models.Model):
    row = models.ForeignKey(Row, on_delete=models.CASCADE, related_name='cells')
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    # Поля для разных типов данных
    text_value = models.TextField(blank=True, null=True)
    integer_value = models.IntegerField(blank=True, null=True)
    float_value = models.FloatField(blank=True, null=True)
    boolean_value = models.BooleanField(blank=True, null=True)
    date_value = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('row', 'column')

    @property
    def value(self):
        """Возвращает значение в зависимости от типа колонки"""
        if self.column.data_type == Column.ColumnType.INTEGER:
            return self.integer_value
        elif self.column.data_type == Column.ColumnType.FLOAT:
            return self.float_value
        elif self.column.data_type == Column.ColumnType.BOOLEAN:
            return self.boolean_value
        elif self.column.data_type == Column.ColumnType.DATE:
            return self.date_value
        else:  # TEXT
            return self.text_value

    @value.setter
    def value(self, val):
        """Устанавливает значение в правильное поле"""
        if self.column.data_type == Column.ColumnType.INTEGER:
            self.integer_value = int(val) if val is not None else None
        elif self.column.data_type == Column.ColumnType.FLOAT:
            self.float_value = float(val) if val is not None else None
        elif self.column.data_type == Column.ColumnType.BOOLEAN:
            self.boolean_value = bool(val) if val is not None else None
        elif self.column.data_type == Column.ColumnType.DATE:
            self.date_value = val if val is not None else None  # Здесь val уже datetime.date
        else:  # TEXT
            self.text_value = str(val) if val is not None else ''

    class Meta:
        unique_together = ('row', 'column')

    def __str__(self):
        return f"{self.row} - {self.column}: {self.value}"


class RowPermission(models.Model):
    row = models.ForeignKey(Row, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    can_edit = models.BooleanField(default=True)

    class Meta:
        unique_together = ('row', 'user')

    def __str__(self):
        if self.can_edit:
            arg = 'edit'
        else:
            arg = 'view'
        return f"{self.user.username} can {arg} {self.row}"
