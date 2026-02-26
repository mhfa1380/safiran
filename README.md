# safiran

وب‌سایت «سفیران آینده روشن» – پروژه Django
# موسسه اعزام دانشجوی سفیران آینده روشن

وب‌سایت رسمی موسسه اعزام دانشجو به خارج - بابل، مازندران

## نصب و اجرا

```bash
# ایجاد محیط مجازی
python -m venv venv

# فعال‌سازی مجازی (Windows)
venv\Scripts\activate

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای migrations
python manage.py migrate

# ایجاد ادمین (اولین بار)
python manage.py createsuperuser

# اجرای سرور
python manage.py runserver
```

سایت در آدرس http://127.0.0.1:8000 در دسترس است.

## ساختار پروژه

```
safiran_site/
├── core/                 # اپلیکیشن اصلی
│   ├── admin.py          # ثبت مدل‌ها در پنل ادمین
│   ├── context_processors.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── safiran_site/         # تنظیمات پروژه Django
├── templates/
│   ├── base.html
│   ├── 404.html
│   ├── layout/           # header, footer
│   ├── core/             # index, about, contact, appointment, evaluation, faq
│   ├── blog/             # list, single
│   ├── content/          # services, majors, courses_list, course_details
│   └── schools/          # list, detail
├── static/
│   ├── css/
│   ├── js/
│   └── img/
├── media/                # فایل‌های آپلودشده (در صورت استفاده)
├── manage.py
├── requirements.txt
└── .gitignore
```

## صفحات و مسیرها

| مسیر | توضیح |
|------|-------|
| `/` | صفحه اصلی |
| `/about/` | درباره ما |
| `/contact/` | تماس با ما (فرم داینامیک) |
| `/blog/` | لیست وبلاگ |
| `/blog/<slug>/` | جزئیات پست وبلاگ |
| `/schools/` | لیست دانشگاه‌ها |
| `/schools/<slug>/` | جزئیات دانشگاه |
| `/services/` | خدمات موسسه |
| `/majors/` | رشته‌های تحصیلی |
| `/courses/` | لیست دوره‌ها |
| `/course/<slug>/` | جزئیات دوره |
| `/appointment/` | رزرو مشاوره |
| `/evaluation/` | فرم ارزیابی |
| `/faq/` | سوالات متداول |
| `/admin/` | پنل مدیریت |

## تغییرات اخیر (UI)

- بهبود آیکون باز/بسته شدن سوالات متداول در صفحه FAQ (چورون مینیمال و هماهنگ با هویت بصری سایت)

## مدل‌های دیتابیس

- **ContactMessage** – پیام‌های تماس با ما
- **BlogPost** – پست‌های وبلاگ
- **Service** – خدمات موسسه
- **Major** – رشته‌های تحصیلی
- **Course** – دوره‌ها
- **University** – دانشگاه‌ها و موسسات
- **ConsultationRequest** – درخواست‌های رزرو مشاوره
- **EvaluationRequest** – درخواست‌های ارزیابی

## اطلاعات موسسه

- **نام:** سفیران آینده روشن
- **استان:** مازندران
- **شهر:** بابل
- **تلفن:** 011-32350320
- **ایمیل:** saroshanbbl@gmail.com
- **آدرس:** کمربند امیر کلا، جنب موسسه آموزش عالی علوم و فناوری آریان، مجتمع ایرانیکا، طبقه اول
- **وب‌سایت:** www.saroshan.ir

## تصاویر مورد نیاز

فهرست کامل تصاویر در فایل `docs/ASSETS.md` درج شده است.
