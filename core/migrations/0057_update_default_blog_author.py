"""به‌روزرسانی نویسنده پیش‌فرض وبلاگ — موژان الفیان."""

from django.db import migrations

OLD_AUTHOR_NAME = "تیم تحریریه سفیران"
NEW_AUTHOR_NAME = "موژان الفیان"
NEW_ROLE = "کارشناس مهاجرت تحصیلی"
NEW_BIO = (
    "کارشناس مهاجرت تحصیلی در موسسه سفیران آینده روشن؛ "
    "تولید محتوای تخصصی درباره اپلای، ویزا و زندگی دانشجویی."
)


def forwards(apps, schema_editor):
    BlogAuthor = apps.get_model("core", "BlogAuthor")
    BlogPost = apps.get_model("core", "BlogPost")

    target = BlogAuthor.objects.filter(name=NEW_AUTHOR_NAME).first()
    legacy = BlogAuthor.objects.filter(name=OLD_AUTHOR_NAME).first()

    if legacy and target and legacy.pk != target.pk:
        BlogPost.objects.filter(author_id=legacy.pk).update(author_id=target.pk)
        legacy.delete()
        legacy = None

    if legacy:
        legacy.name = NEW_AUTHOR_NAME
        legacy.role = NEW_ROLE
        legacy.bio = NEW_BIO
        legacy.is_active = True
        legacy.order = 0
        legacy.save(update_fields=["name", "role", "bio", "is_active", "order"])
    elif not target:
        BlogAuthor.objects.create(
            name=NEW_AUTHOR_NAME,
            role=NEW_ROLE,
            bio=NEW_BIO,
            is_active=True,
            order=0,
        )
    else:
        BlogAuthor.objects.filter(pk=target.pk).update(
            role=NEW_ROLE,
            bio=NEW_BIO,
            is_active=True,
            order=0,
        )


def backwards(apps, schema_editor):
    BlogAuthor = apps.get_model("core", "BlogAuthor")
    BlogAuthor.objects.filter(name=NEW_AUTHOR_NAME).update(
        name=OLD_AUTHOR_NAME,
        role="تیم تحریریه",
        bio="متخصصان موسسه سفیران آینده روشن در زمینه مهاجرت تحصیلی.",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0056_major_search_indexes"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
