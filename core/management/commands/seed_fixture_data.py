"""
دستور مدیریت برای تولید و بارگذاری داده‌های فیک در دیتابیس.
استفاده: python manage.py seed_fixture_data
"""
from django.core.management.base import BaseCommand

from core.models import (
    BlogPost,
    ConsultationRequest,
    ConsultationSlot,
    ContactMessage,
    Course,
    CourseSyllabus,
    EvaluationRequest,
    FAQ,
    Institute,
    Major,
    Service,
    University,
)


class Command(BaseCommand):
    help = "تولید و بارگذاری داده‌های فیک برای تمام مدل‌های اصلی"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="پاک کردن داده‌های قبلی قبل از تولید (به جز Institute و User)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_data()

        self._seed_institute()
        self._seed_services()
        self._seed_faqs()
        self._seed_majors()
        self._seed_courses()
        self._seed_universities()
        self._seed_blog_posts()
        self._seed_sample_requests()

        self.stdout.write(self.style.SUCCESS("Fixture data seeded successfully."))

    def _clear_data(self):
        """پاک کردن داده‌ها (به ترتیب وابستگی)."""
        ConsultationRequest.objects.all().delete()
        EvaluationRequest.objects.all().delete()
        ContactMessage.objects.all().delete()
        ConsultationSlot.objects.all().delete()
        CourseSyllabus.objects.all().delete()
        Course.objects.all().delete()
        Major.objects.all().delete()
        BlogPost.objects.all().delete()
        University.objects.all().delete()
        FAQ.objects.all().delete()
        Service.objects.all().delete()
        self.stdout.write("Previous data cleared.")

    def _seed_institute(self):
        Institute.objects.get_or_create(
            id=1,
            defaults={
                "name": "سفیران آینده روشن",
                "province": "مازندران",
                "city": "بابل",
                "type_title": "فرآیند صدور مجوز موسسات اعزام دانشجو به خارج",
                "phone": "01132350320",
                "email": "saroshanbbl@gmail.com",
                "address": "کمربند امیر کلا، جنب موسسه آموزش عالی علوم و فناوری آریان، مجتمع ایرانیکا، طبقه اول",
                "website": "www.saroshan.ir",
                "license_issue_date": "1403/05/22",
                "license_expiry_date": "1403/05/22",
                "students_sent": 0,
                "countries_count": 3,
            },
        )
        self.stdout.write("  Institute: OK")

    def _seed_services(self):
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
                defaults={"description": description, "icon": icon, "order": order, "is_active": True},
            )
        self.stdout.write("  Services: OK")

    def _seed_faqs(self):
        faqs = [
            (1, "آیا مشاوره غیرحضوری هم ممکن است؟", "بله؛ مشاوره می‌تواند به صورت تلفنی، واتساپ صوتی یا تصویری انجام شود. کافی است در فرم رزرو مشاوره نوع مشاوره را «غیرحضوری / آنلاین» انتخاب کنید تا در زمان تعیین‌شده با شما تماس گرفته شود."),
            (2, "آیا مدارک صادر شده از دانشگاه‌های ایران برای اپلای دانشگاه‌های خارجی معتبر است؟", "بله؛ مدارک تحصیلی صادرشده از دانشگاه‌های مورد تأیید وزارت علوم ایران برای اپلای بسیاری از دانشگاه‌های معتبر دنیا قابل قبول است."),
            (3, "بهترین زمان برای شروع فرایند مهاجرت تحصیلی چه زمانی است؟", "هرچه زودتر اقدام کنید، شانس بیشتری برای پذیرش و بورسیه دارید. معمولاً بهتر است حداقل ۶ تا ۱۲ ماه قبل از شروع ترم تحصیلی اقدام کنید."),
            (4, "آیا بدون مدرک زبان هم می‌توان اقدام کرد؟", "در بعضی دانشگاه‌ها امکان دریافت پذیرش مشروط بدون مدرک زبان وجود دارد، اما برای موفقیت در گرفتن ویزا و تحصیل، داشتن مدرک زبان معتبر به شدت توصیه می‌شود."),
            (5, "آیا امکان کار همزمان با تحصیل در کشور مقصد وجود دارد؟", "قوانین هر کشور متفاوت است، اما در بسیاری از کشورها مانند کانادا و برخی کشورهای اروپایی، دانشجویان بین‌المللی مجاز به کار پاره‌وقت هستند."),
            (6, "برای شروع، از کجا باید اقدام کنم؟", "بهترین نقطه شروع، تکمیل فرم ارزیابی آنلاین است. پس از ثبت فرم، اطلاعات شما توسط کارشناسان موسسه بررسی می‌شود."),
        ]
        for order, question, answer in faqs:
            FAQ.objects.get_or_create(
                question=question,
                defaults={"answer": answer, "order": order, "is_active": True},
            )
        self.stdout.write("  FAQs: OK")

    def _seed_majors(self):
        majors = [
            ("پزشکی", "medicine", "china", "رشته پزشکی در چین با بورسیه تحصیلی"),
            ("دندانپزشکی", "dentistry", "china", "دندانپزشکی در دانشگاه‌های چین"),
            ("کامپیوتر", "computer-science", "canada", "رشته کامپیوتر و مهندسی نرم‌افزار در کانادا"),
            ("مکانیک", "mechanical-engineering", "spain", "مهندسی مکانیک در اسپانیا"),
        ]
        for title, slug, country, short_desc in majors:
            Major.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "short_description": short_desc, "country": country, "order": 0, "is_active": True},
            )
        self.stdout.write("  Majors: OK")

    def _seed_courses(self):
        courses_data = [
            ("پیش‌نیاز زبان چینی", "chinese-preparation", "پیش‌نیاز زبان چینی برای اپلای", "china"),
            ("آمادگی برای آزمون آیلتس", "ielts-preparation", "دوره آمادگی برای آزمون آیلتس", "canada"),
            ("مکانیک پیشرفته", "advanced-mechanics", "دوره مکانیک پیشرفته برای اسپانیا", "spain"),
        ]
        for title, slug, short_desc, country in courses_data:
            course, created = Course.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "short_description": short_desc,
                    "order": 0,
                    "is_active": True,
                    "country": country,
                },
            )
            if created:
                CourseSyllabus.objects.bulk_create([
                    CourseSyllabus(course=course, title="سرفصل ۱", description="توضیحات سرفصل اول", order=1),
                    CourseSyllabus(course=course, title="سرفصل ۲", description="توضیحات سرفصل دوم", order=2),
                    CourseSyllabus(course=course, title="سرفصل ۳", description="توضیحات سرفصل سوم", order=3),
                ])
        self.stdout.write("  Courses: OK")

    def _seed_universities(self):
        unis = [
            ("tsinghua-university", "دانشگاه چینگوا", "Tsinghua University", "china", "پکن", "دانشگاه برتر چین"),
            ("ubc", "دانشگاه بریتیش کلمبیا", "University of British Columbia", "canada", "ونکوور", "دانشگاه برتر کانادا"),
            ("ub-barcelona", "دانشگاه بارسلونا", "Universitat de Barcelona", "spain", "بارسلونا", "دانشگاه معتبر اسپانیا"),
        ]
        for slug, name_fa, name_en, country, city, short_desc in unis:
            University.objects.get_or_create(
                slug=slug,
                defaults={
                    "name_fa": name_fa,
                    "name_en": name_en,
                    "country": country,
                    "city": city,
                    "short_description": short_desc,
                    "is_approved_by_mo_science": True,
                },
            )
        self.stdout.write("  Universities: OK")

    def _seed_blog_posts(self):
        posts = [
            ("news-china-2025", "اخبار پذیرش چین ۱۴۰۴", "خلاصه اخبار پذیرش در چین", "<p>متن اخبار پذیرش چین.</p>", "چین"),
            ("news-canada-2025", "اخبار ویزای کانادا", "به‌روزرسانی ویزای کانادا", "<p>متن اخبار ویزای کانادا.</p>", "کانادا"),
            ("services-intro", "معرفی خدمات موسسه", "خدمات موسسه سفیران", "<p>موسسه سفیران آینده روشن خدمات متنوعی ارائه می‌دهد.</p>", "خدمات موسسه"),
        ]
        for slug, title, excerpt, content, tag in posts:
            BlogPost.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "excerpt": excerpt, "content": content, "country_tag": tag, "is_published": True},
            )
        self.stdout.write("  BlogPosts: OK")

    def _seed_sample_requests(self):
        if not ConsultationRequest.objects.exists():
            slot = ConsultationSlot.objects.filter(is_booked=False).first()
            uni = University.objects.first()
            if slot and uni:
                ConsultationRequest.objects.create(
                    full_name="کاربر نمونه",
                    phone="09123456789",
                    email="sample@example.com",
                    consultation_type=ConsultationRequest.ONLINE,
                    country=ConsultationRequest.COUNTRY_CANADA,
                    slot=slot,
                    interest_university=uni,
                    description="درخواست تست",
                )
                slot.is_booked = True
                slot.save(update_fields=["is_booked"])

        if not EvaluationRequest.objects.exists():
            EvaluationRequest.objects.create(
                full_name="متقاضی نمونه",
                phone="09123456789",
                email="eval@example.com",
                current_degree=EvaluationRequest.DEGREE_BACHELOR,
                field_of_study="کامپیوتر",
                average_grade="۱۷.۵",
                target_country=ConsultationRequest.COUNTRY_CANADA,
            )

        if not ContactMessage.objects.exists():
            ContactMessage.objects.create(
                full_name="فرستنده نمونه",
                email="contact@example.com",
                subject="سوال درباره موسسه",
                message="این یک پیام نمونه است.",
            )

        self.stdout.write("  Sample requests: OK")
