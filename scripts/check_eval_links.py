import os
import re

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safiran_site.settings")
django.setup()

from core.models import Major

bad = Major.objects.filter(description__icontains="/ارزیابی/").exclude(
    description__icontains="/ارزیابی-مهاجرت/"
)
print("majors with bad /ارزیابی/ link:", bad.count())
for m in bad[:3]:
    print(m.slug, m.title)
    for link in re.findall(r'href="([^"]+)"', m.description or ""):
        if "ارزیابی" in link:
            print(" ", link)
