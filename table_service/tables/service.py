from django.db import transaction
from .models import RowLock


def lock_row(row, user):
    """Блокирует строку для редактирования"""
    with transaction.atomic():
        # Создаем новую блокировку
        lock, created = RowLock.objects.get_or_create(
            row=row,
            defaults={'user': user}
        )

        if not created and lock.user != user:
            return False  # Уже заблокировано другим пользователем
        return True


def unlock_row(row, user):
    """Снимает блокировку строки"""
    try:
        lock = RowLock.objects.get(row=row, user=user)
        lock.delete()
        return True
    except RowLock.DoesNotExist:
        return False
