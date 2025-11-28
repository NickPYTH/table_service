from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.signals import request_finished

from tables.models import Cell

@receiver(post_save, sender=Cell)
def track_model_changes(sender, instance, created, **kwargs):
    if created:
        print(f"Создана новая запись: {instance}")
    else:
        print(f"Обновлена существующая запись: {instance}")

@receiver(post_delete, sender=Cell)
def track_model_deletion(sender, instance, **kwargs):
    print(f"Удалена запись: {instance}")