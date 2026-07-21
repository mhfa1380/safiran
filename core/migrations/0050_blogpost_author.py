from django.db import migrations, models


DEFAULT_AUTHOR_NAME = "تیم تحریریه سفیران"
DEFAULT_AUTHOR_BIO = (
    "متخصصان موسسه سفیران آینده روشن در زمینه مهاجرت تحصیلی و اخبار بین‌المللی."
)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_ckeditor_asset"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="author_name",
            field=models.CharField(
                default=DEFAULT_AUTHOR_NAME,
                max_length=120,
                verbose_name="نام نویسنده",
                help_text="نام نویسنده برای نمایش در انتهای مطلب (اجباری).",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="blogpost",
            name="author_bio",
            field=models.CharField(
                default=DEFAULT_AUTHOR_BIO,
                max_length=300,
                verbose_name="معرفی کوتاه نویسنده",
                help_text="یک یا دو جمله درباره نویسنده (اجباری).",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="blogpost",
            name="author_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="blog/authors/",
                verbose_name="عکس نویسنده",
                help_text="اختیاری؛ در صورت خالی بودن آواتار پیش‌فرض نمایش داده می‌شود.",
            ),
        ),
    ]
