"""Parse university world_rank for numeric sorting."""
from __future__ import annotations


def parse_world_rank_num(value: object) -> int:
    raw = str(value or "").strip()
    if not raw:
        return 9999
    try:
        return min(max(int(raw.split("-")[0].strip()), 1), 9999)
    except (TypeError, ValueError):
        return 9999
