import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safiran_site.settings")
django.setup()

from core.models import BlogPost
from django.utils import timezone

tz = timezone.get_current_timezone()
posts = BlogPost.objects.filter(is_published=True).order_by("-created_at")
lines = []
for p in posts:
    local = p.created_at.astimezone(tz)
    lines.append(f"{local:%Y-%m-%d %H:%M} | {p.slug} | img={bool(p.image)}")
out = "\n".join(lines)
print(f"{posts.count()} posts")
print(out[:800])
