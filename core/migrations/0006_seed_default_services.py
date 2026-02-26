"""داده‌های اولیه برای خدمات موسسه."""
from django.db import migrations


def create_default_services(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    defaults = [
        (1, "مشاوره رایگان", "ti-comments-smiley", "تیم ما با ارائه مشاوره‌های کامل و برگزاری جلسات متعدد، تمام تلاش خود را جهت رضایت و تسهیل روند مهاجرتتان می‌کند."),
        (2, "مکاتبه با دانشگاه‌ها و اساتید", "ti-email", "با برقراری ارتباط و مکاتبه با بهترین دانشگاه‌ها و اساتید مجرب، بهترین محل تحصیل را برای شما فراهم خواهیم کرد."),
        (3, "تایید و تکمیل مدارک", "ti-clipboard", "با شناخت دقیق مسیر مهاجرت، در روند اخذ مدارک و تکمیل پرونده در کنار شما خواهیم بود."),
        (4, "اخذ ویزای دانشجویی و همراهی", "ti-id-badge", "بدون دغدغه تعیین وقت سفارت و دریافت ویزا، همراهتان هستیم تا مراحل مهاجرت را با خیال آسوده طی کنید."),
        (5, "اخذ بورسیه", "ti-crown", "اخذ بورسیه تحصیلی از حساس‌ترین مراحل مهاجرت است و ما در این مسیر با تمام توان همراه شما خواهیم بود."),
        (6, "استقرار در مقصد", "ti-world", "با حضور نمایندگان ما در کشورهای مقصد، از اسکان و تأمین نیازهای اولیه شما اطمینان حاصل خواهید کرد."),
    ]
    for order, title, icon, description in defaults:
        Service.objects.get_or_create(
            title=title,
            defaults={"description": description, "icon": icon, "order": order},
        )


def reverse_func(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    Service.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_service_major_course"),
    ]

    operations = [
        migrations.RunPython(create_default_services, reverse_func),
    ]
