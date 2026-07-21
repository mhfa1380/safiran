from django.db import migrations, models
import django.db.models.deletion


DEFAULT_NAME = "تیم تحریریه سفیران"
DEFAULT_BIO = (
    "متخصصان موسسه سفیران آینده روشن در زمینه مهاجرت تحصیلی و اخبار بین‌المللی."
)
DEFAULT_ROLE = "تیم تحریریه"


def migrate_post_authors(apps, schema_editor):
    BlogPost = apps.get_model("core", "BlogPost")
    BlogAuthor = apps.get_model("core", "BlogAuthor")

    default_author = BlogAuthor.objects.create(
        name=DEFAULT_NAME,
        bio=DEFAULT_BIO,
        role=DEFAULT_ROLE,
        is_active=True,
        order=0,
    )

    authors_by_key: dict[tuple[str, str], int] = {
        (DEFAULT_NAME, DEFAULT_BIO): default_author.pk,
    }

    for post in BlogPost.objects.all().iterator():
        name = (getattr(post, "author_name", None) or DEFAULT_NAME).strip() or DEFAULT_NAME
        bio = (getattr(post, "author_bio", None) or DEFAULT_BIO).strip() or DEFAULT_BIO
        key = (name, bio)

        if key not in authors_by_key:
            author = BlogAuthor.objects.create(
                name=name,
                bio=bio,
                role="",
                is_active=True,
                order=len(authors_by_key),
            )
            photo = getattr(post, "author_photo", None)
            if photo:
                author.photo = photo
                author.save(update_fields=["photo"])
            authors_by_key[key] = author.pk
        else:
            author = BlogAuthor.objects.get(pk=authors_by_key[key])
            photo = getattr(post, "author_photo", None)
            if photo and not author.photo:
                author.photo = photo
                author.save(update_fields=["photo"])

        post.author_id = authors_by_key[key]
        post.save(update_fields=["author_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0051_seed_admin_staff_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogAuthor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="نام")),
                (
                    "role",
                    models.CharField(
                        blank=True,
                        help_text="مثلاً کارشناس مهاجرت تحصیلی یا تیم تحریریه (اختیاری).",
                        max_length=120,
                        verbose_name="سمت / برچسب",
                    ),
                ),
                (
                    "bio",
                    models.CharField(
                        help_text="یک یا دو جمله درباره نویسنده.",
                        max_length=400,
                        verbose_name="معرفی کوتاه",
                    ),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="blog/authors/",
                        verbose_name="عکس",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")),
            ],
            options={
                "verbose_name": "نویسنده وبلاگ",
                "verbose_name_plural": "نویسندگان وبلاگ",
                "db_table": "core_blogauthor",
                "ordering": ["order", "name"],
            },
        ),
        migrations.AddField(
            model_name="blogpost",
            name="author",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="posts",
                to="core.blogauthor",
                verbose_name="نویسنده",
            ),
        ),
        migrations.RunPython(migrate_post_authors, migrations.RunPython.noop),
        migrations.RemoveField(model_name="blogpost", name="author_name"),
        migrations.RemoveField(model_name="blogpost", name="author_bio"),
        migrations.RemoveField(model_name="blogpost", name="author_photo"),
        migrations.AlterField(
            model_name="blogpost",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="posts",
                to="core.blogauthor",
                verbose_name="نویسنده",
                help_text="نویسنده این مطلب (اجباری).",
            ),
        ),
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(fields=["author"], name="blog_author_idx"),
        ),
    ]
