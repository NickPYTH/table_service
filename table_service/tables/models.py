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
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.table.title} - {self.name}"


class Row(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='rows')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def get_cell_value(self, column_id):
        cell = self.cells.filter(column_id=column_id).first()
        if cell:
            return cell.value
        else:
            return ''

    def __str__(self):
        return f"Row {self.order} in {self.table.title}"


class Cell(models.Model):
    row = models.ForeignKey(Row, on_delete=models.CASCADE, related_name='cells')
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    value = models.TextField(blank=True)

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
