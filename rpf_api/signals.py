from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import EventSignUp

IMAGE_FIELDS = ("document_front_picture", "document_back_picture")

def _delete_file_on_commit(file_field):
    if not file_field or not file_field.name:
        return
    storage, name = file_field.storage, file_field.name

    def delete():
        if storage.exists(name):
            storage.delete(name)

    transaction.on_commit(delete)

@receiver(post_delete, sender=EventSignUp)
def delete_images_with_record(sender, instance, **kwargs):
    for field in IMAGE_FIELDS:
        _delete_file_on_commit(getattr(instance, field))

@receiver(pre_save, sender=EventSignUp)
def delete_replaced_images(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = sender.objects.filter(pk=instance.pk).first()
    if old is None:
        return
    for field in IMAGE_FIELDS:
        old_file, new_file = getattr(old, field), getattr(instance, field)
        if old_file and old_file.name != (new_file.name if new_file else None):
            _delete_file_on_commit(old_file)