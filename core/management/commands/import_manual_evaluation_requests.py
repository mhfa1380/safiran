"""وارد کردن دستی پرونده‌های ارزیابی (برای همگام‌سازی محیط توسعه با ادمین)."""

from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.evaluation_share import ensure_evaluation_share
from core.models import ConsultationRequest, EvaluationRequest
from core.referral_source import REFERRAL_AD, REFERRAL_GOOGLE

APPLICANTS = [
    {
        "full_name": "مریم ابوطالبیان",
        "phone": "09134612935",
        "email": "fatemehaboutalebian1282@gmail.com",
        "birth_year": 1377,
        "marital_status": EvaluationRequest.MARITAL_SINGLE,
        "apply_timeline": EvaluationRequest.APPLY_SOON,
        "has_financial_capacity": True,
        "current_degree": EvaluationRequest.DEGREE_MASTER,
        "field_of_study": "مهندسی پزشکی",
        "average_grade": "16.80",
        "graduation_year": "",
        "target_country": ConsultationRequest.COUNTRY_CANADA,
        "language_test_type": EvaluationRequest.TEST_NONE,
        "has_ielts": False,
        "language_score": "",
        "has_book": True,
        "desired_countries": "canada,spain,china,germany,uk,usa,australia,not_sure",
        "desired_major": "نوروساینس",
        "service_scope": EvaluationRequest.SERVICE_CONSULT,
        "preferred_intake": "پاییز 1406",
        "notes": "",
        "referral_source": REFERRAL_AD,
        "referral_detail": "",
        "created_at": datetime(2026, 5, 26, 13, 28, 0),
        "updated_at": datetime(2026, 5, 26, 13, 29, 0),
    },
    {
        "full_name": "سجاد نباتی",
        "phone": "09125425027",
        "email": "",
        "birth_year": 1361,
        "marital_status": EvaluationRequest.MARITAL_SINGLE,
        "apply_timeline": EvaluationRequest.APPLY_SOON,
        "has_financial_capacity": True,
        "current_degree": EvaluationRequest.DEGREE_MASTER,
        "field_of_study": "مدیریت بازرگانی",
        "average_grade": "17",
        "graduation_year": "1399",
        "target_country": ConsultationRequest.COUNTRY_CANADA,
        "language_test_type": EvaluationRequest.TEST_IELTS,
        "has_ielts": True,
        "language_score": "6",
        "desired_countries": "canada,spain,germany,uk",
        "desired_major": "مدیریت منابع انسانی",
        "service_scope": EvaluationRequest.SERVICE_FULL,
        "preferred_intake": "پاییز 1405",
        "notes": (
            "به ترتیب اولویت  :  اسپانیا - آلمان -  کانادا - انگلیس\n"
            "به دلیل مشکلات مالی فراوان   فقط به دنیال دانشگاه های فول فاند هستم"
        ),
        "referral_source": REFERRAL_GOOGLE,
        "referral_detail": "بورسیه تحصیلی دکتری",
        "created_at": datetime(2026, 5, 26, 12, 37, 0),
        "updated_at": datetime(2026, 5, 26, 12, 40, 0),
    },
]


class Command(BaseCommand):
    help = "وارد کردن دستی درخواست‌های ارزیابی مریم ابوطالبیان و سجاد نباتی"

    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        created_count = 0
        skipped = 0

        for item in APPLICANTS:
            raw = item.copy()
            phone = raw["phone"]
            existing = EvaluationRequest.objects.filter(phone=phone).first()
            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped existing pk={existing.pk} phone={phone}"
                    )
                )
                skipped += 1
                continue

            timestamps = {
                "created_at": timezone.make_aware(raw.pop("created_at"), tz),
                "updated_at": timezone.make_aware(raw.pop("updated_at"), tz),
            }
            obj = EvaluationRequest.objects.create(**raw)
            EvaluationRequest.objects.filter(pk=obj.pk).update(**timestamps)
            obj.refresh_from_db()
            share = ensure_evaluation_share(obj)
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created pk={obj.pk} phone={phone} share_token={share.token}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Done: created={created_count} skipped={skipped}")
        )
