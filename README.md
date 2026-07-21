# سفیران آینده روشن — safiran_site

وب‌سایت رسمی موسسه اعزام دانشجو (Django) — مشاوره مهاجرت تحصیلی، ارزیابی هوشمند، وبلاگ، دانشگاه‌ها و خدمات.

## پیش‌نیاز

- Python 3.11+ (تست‌شده با 3.13)
- `pip` و ترجیحاً `venv`

## نصب سریع

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
copy .env.example .env         # Windows — سپس مقادیر را ویرایش کنید
# cp .env.example .env         # Linux/macOS

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

سایت: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) — پنل: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## فایل `.env`

تنظیمات از `safiran_site/settings.py` با `python-dotenv` از `.env` در ریشه پروژه خوانده می‌شود.

| متغیر | توضیح |
|--------|--------|
| `DJANGO_DEBUG` | `1` توسعه، `0` production |
| `DJANGO_SECRET_KEY` | کلید امنیتی جنگو |
| `DJANGO_ALLOWED_HOSTS` | دامنه‌ها با ویرگول |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | مبدأهای CSRF (با پورت لوکال) |
| `SITE_URL` | آدرس پایه canonical و سئو — لوکال: `http://127.0.0.1:8000` |
| `BALE_*` | اعلان بله (اختیاری) |
| `MHFA_*` | پنل live.mhfa.ir و فوتر متمرکز (اختیاری) |

نمونه کامل: `.env.example` (بدون توکن واقعی — قابل commit).

```bash
# بررسی بارگذاری تنظیمات
python manage.py check
```

## داده نمونه (اختیاری)

```bash
python manage.py seed_fixture_data
python manage.py seed_blog_posts --force
python manage.py seed_study_countries
python manage.py seed_universities_majors
```

## دستورات نگهداری

```bash
python manage.py maintain_database
python manage.py collectstatic --noinput   # قبل از deploy
```

## صفحات مهم (URL فارسی)

| مسیر | صفحه |
|------|------|
| `/` | صفحه اصلی |
| `/درباره-ما/` | درباره ما |
| `/تماس-با-ما/` | تماس |
| `/ارزیابی-مهاجرت/` | ارزیابی رایگان آنلاین |
| `/رزرو-مشاوره/` | رزرو مشاوره |
| `/تعرفه-خدمات/` | تعرفه و ماشین‌حساب |
| `/سوالات-متداول/` | FAQ |
| `/blog/` | وبلاگ |
| `/دانشگاه-های-خارج/` | دانشگاه‌ها |
| `/رشته-های-تحصیلی/` | رشته‌ها |
| `/خدمات-با-ما/` | خدمات |

آدرس‌های قدیمی انگلیسی با ریدایرکت ۳۰۱ به مسیر فارسی هدایت می‌شوند.

## ساختار پروژه

```
safiran_site/
├── core/                 # اپ اصلی (مدل‌ها، ویوها، سئو، ارزیابی)
├── safiran_site/         # settings، urls
├── templates/
├── static/
├── media/
├── scripts/              # deploy و mhfa-agent
├── docs/                 # ASSETS.md، SEO.md
├── manage.py
├── requirements.txt
├── requirements-agent.txt
├── .env.example
└── .env                  # محلی — در git نیست
```

## عامل سرور MHFA (اختیاری)

```bash
pip install -r requirements-agent.txt
# نمونه env: scripts/mhfa-agent.env.example
python scripts/mhfa_agent.py
```

## Production

- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY` تصادفی و قوی
- `SITE_URL=https://www.saroshan.ir`
- PostgreSQL یا SQLite با پشتیبان‌گیری
- `collectstatic` + Gunicorn/uWSGI + Nginx
- Redis برای کش در ترافیک بالا (`DJANGO_CACHE_BACKEND=redis`)
- Celery برای کارهای سنگین (`CELERY_ENABLED=1` + worker)
- بررسی: `python manage.py check_runtime`
- سرویس‌های نمونه: `scripts/systemd/safiran.service` و `safiran-celery.service`

## مستندات بیشتر

- [docs/ASSETS.md](docs/ASSETS.md) — تصاویر
- [docs/SEO.md](docs/SEO.md) — سئو و sitemap

## موسسه

- **نام:** سفیران آینده روشن  
- **شهر:** بابل، مازندران  
- **وب‌سایت:** [www.saroshan.ir](https://www.saroshan.ir)
