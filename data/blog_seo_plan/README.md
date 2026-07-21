# نقشه محتوای SEO — ۲۰۰ مقاله وبلاگ

## فایل‌ها

| فایل | توضیح |
|------|--------|
| `plan_200.json` | لیست ۲۰۰ مقاله با عنوان، slug، متا، کلمات کلیدی و brief تصویر |
| `summary.txt` | تعداد مقالات به تفکیک دسته |
| `samples/001-*.md` | نمونه مقاله کامل (#1 کانادا) |

## تولید مجدد

```bash
python scripts/generate_blog_seo_plan.py
```

## انتشار در Django

مدل `BlogPost` در `core/models.py` فیلدهای: `title`, `slug`, `excerpt`, `content`, `image`, `country_tag`, `meta_*`.

برای وارد کردن دسته‌ای می‌توان management command ساخت که از `plan_200.json` بخواند.

## تولید و وارد کردن ۲۰۰ مقاله

```bash
python manage.py import_blog_plan_200
python manage.py import_blog_plan_200 --force   # به‌روزرسانی محتوا
python manage.py stagger_blog_publish           # فقط تاریخ و کاور
```

- موتور محتوا: `core/blog_content/generator.py` (هر مقاله ۱۵۰۰+ کلمه، FAQ، جدول، CTA)
- کاور: `static/img/blog/covers/{slug}.jpg`
- **۲۳۲ پست** منتشرشده (۳۲ قبلی + ۲۰۰ جدید) با تاریخ‌های پلکانی ۲ پست/روز
