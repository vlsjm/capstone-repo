import os
import logging
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _delete_file(field):
    """Delete a FileField/ImageField file from disk, ignoring errors."""
    if field and field.name:
        path = field.path
        if os.path.isfile(path):
            try:
                os.remove(path)
                logger.debug("Deleted media file: %s", path)
            except OSError as e:
                logger.warning("Could not delete media file %s: %s", path, e)


# ── Supply ────────────────────────────────────────────────────────────────────

@receiver(post_delete, sender='app.Supply')
def delete_supply_barcode(sender, instance, **kwargs):
    """Remove barcode image from disk when a Supply is deleted."""
    _delete_file(instance.barcode_image)


@receiver(pre_save, sender='app.Supply')
def replace_supply_barcode(sender, instance, **kwargs):
    """
    Remove the old barcode image from disk when it is replaced with a new one
    (e.g. when the barcode is regenerated).
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.barcode_image and old.barcode_image != instance.barcode_image:
        _delete_file(old.barcode_image)


# ── Property ──────────────────────────────────────────────────────────────────

@receiver(post_delete, sender='app.Property')
def delete_property_barcode(sender, instance, **kwargs):
    """Remove barcode image from disk when a Property is deleted."""
    _delete_file(instance.barcode_image)


@receiver(pre_save, sender='app.Property')
def replace_property_barcode(sender, instance, **kwargs):
    """
    Remove the old barcode image from disk when it is replaced with a new one.
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.barcode_image and old.barcode_image != instance.barcode_image:
        _delete_file(old.barcode_image)


# ── PPMP ──────────────────────────────────────────────────────────────────────

@receiver(post_delete, sender='app.PPMP')
def delete_ppmp_file(sender, instance, **kwargs):
    """Remove the uploaded PPMP file from disk when the PPMP record is deleted."""
    _delete_file(instance.file)


@receiver(pre_save, sender='app.PPMP')
def replace_ppmp_file(sender, instance, **kwargs):
    """
    Remove the old PPMP file from disk when it is replaced by a new upload
    (e.g. re-uploading a PPMP for the same department/year).
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.file and old.file != instance.file:
        _delete_file(old.file)
