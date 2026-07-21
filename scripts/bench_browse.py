import os
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safiran_site.settings")
django.setup()

from django.conf import settings
from django.db import connection, reset_queries

from core.major_search import list_majors_browse, split_search_results as major_split
from core.university_search import list_universities_browse, split_search_results as uni_split

settings.DEBUG = True


def bench(name, fn, **kw):
    reset_queries()
    t0 = time.perf_counter()
    result = fn(**kw)
    dt = (time.perf_counter() - t0) * 1000
    if isinstance(result, tuple):
        if len(result) == 3 and isinstance(result[2], bool):
            items, total, has_more = result
            print(
                f"{name}: {dt:.1f}ms, queries={len(connection.queries)}, "
                f"items={len(items)}, total={total}, has_more={has_more}"
            )
        else:
            print(
                f"{name}: {dt:.1f}ms, queries={len(connection.queries)}, "
                f"primary={len(result[0])}, related={len(result[1] or [])}"
            )
    else:
        print(f"{name}: {dt:.1f}ms, queries={len(connection.queries)}, result={type(result).__name__}")


cases = [
    ("majors browse other", list_majors_browse, {"country_code": "other", "offset": 0}),
    ("majors browse uk", list_majors_browse, {"country_code": "uk", "offset": 0}),
    (
        "majors search",
        major_split,
        {
            "q": "computer",
            "country_code": "other",
            "primary_limit": 1,
            "related_limit": 8,
        },
    ),
    ("schools browse other", list_universities_browse, {"country_code": "other", "offset": 0}),
    ("schools browse uk", list_universities_browse, {"country_code": "uk", "offset": 0}),
    (
        "schools search",
        uni_split,
        {
            "q": "toronto",
            "country_code": "other",
            "primary_limit": 1,
            "related_limit": 8,
        },
    ),
]

for name, fn, kw in cases:
    bench(name, fn, **kw)

print("--- cached counts ---")
bench("majors browse other (2)", list_majors_browse, {"country_code": "other", "offset": 0})
bench("schools browse other (2)", list_universities_browse, {"country_code": "other", "offset": 0})
