"""
سیگنال‌ها برای فشرده‌سازی خودکار تصاویر و بهینه‌سازی دیتابیس.
"""

from django.db.backends.signals import connection_created
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from .models import TeamMember, University, UniversityGalleryImage
from .utils import compress_image_file


def _compress_if_image(instance, field_name):
    """اگر فیلد حاوی فایل تصویری است، فشرده‌سازی کن."""
    file_field = getattr(instance, field_name, None)
    if file_field:
        compress_image_file(file_field)


def _delete_file_safely(file_field):
    """
    حذف امن فایل روی دیسک بدون خطا در صورت نبودن فایل.
    این تابع فقط فایل قدیمی را پاک می‌کند و به رکورد دیتابیس کاری ندارد.
    """
    if not file_field:
        return
    try:
        storage = file_field.storage
        path = file_field.path
    except (ValueError, AttributeError):
        return
    if not path:
        return
    try:
        if storage.exists(path):
            storage.delete(path)
    except Exception:
        # در صورت هر خطای غیرمنتظره، نگذاریم ذخیره مدل fail شود
        return


@receiver(post_save, sender=TeamMember)
def compress_team_member_image(sender, instance, created, **kwargs):
    if instance.image:
        _compress_if_image(instance, "image")


@receiver(post_save, sender=University)
def compress_university_image(sender, instance, created, **kwargs):
    if instance.image:
        _compress_if_image(instance, "image")


@receiver(post_save, sender=UniversityGalleryImage)
def compress_gallery_image(sender, instance, created, **kwargs):
    if instance.image:
        _compress_if_image(instance, "image")


# --- مدیریت حذف و تعویض فایل‌های تصویری در مدل‌ها ---

@receiver(pre_save, sender=TeamMember)
def delete_old_team_member_image_on_change(sender, instance, **kwargs):
    """
    اگر تصویر عضو تیم در حال ویرایش عوض شود یا خالی شود،
    فایل قبلی از روی دیسک پاک می‌شود.
    """
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = old_instance.image
    new_file = instance.image

    # اگر قبلاً فایل داشتیم و الان یا حذف شده یا فایل دیگری است، قبلی را پاک کن
    if old_file and (not new_file or old_file.name != new_file.name):
        _delete_file_safely(old_file)


@receiver(post_delete, sender=TeamMember)
def delete_team_member_image_on_delete(sender, instance, **kwargs):
    """با حذف عضو تیم، فایل تصویر هم از روی دیسک پاک شود."""
    if instance.image:
        _delete_file_safely(instance.image)


@receiver(pre_save, sender=University)
def delete_old_university_image_on_change(sender, instance, **kwargs):
    """
    اگر تصویر دانشگاه در حال ویرایش عوض شود یا خالی شود،
    فایل قبلی از روی دیسک پاک می‌شود.
    """
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = old_instance.image
    new_file = instance.image

    if old_file and (not new_file or old_file.name != new_file.name):
        _delete_file_safely(old_file)


@receiver(post_delete, sender=University)
def delete_university_image_on_delete(sender, instance, **kwargs):
    """با حذف دانشگاه، فایل تصویر هم از روی دیسک پاک شود."""
    if instance.image:
        _delete_file_safely(instance.image)


@receiver(pre_save, sender=UniversityGalleryImage)
def delete_old_gallery_image_on_change(sender, instance, **kwargs):
    """
    اگر فایل تصویر گالری در حال ویرایش عوض شود یا خالی شود،
    فایل قبلی از روی دیسک پاک می‌شود.
    """
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = old_instance.image
    new_file = instance.image

    if old_file and (not new_file or old_file.name != new_file.name):
        _delete_file_safely(old_file)


@receiver(post_delete, sender=UniversityGalleryImage)
def delete_gallery_image_on_delete(sender, instance, **kwargs):
    """با حذف رکورد گالری، فایل تصویر هم از روی دیسک پاک شود."""
    if instance.image:
        _delete_file_safely(instance.image)


@receiver(connection_created)
def setup_sqlite_pragmas(sender, connection, **kwargs):
    """فعال‌سازی WAL و بهینه‌سازی SQLite برای ترافیک بالا و جلوگیری از قفل دیتابیس."""
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA cache_size=-2000;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.close()
