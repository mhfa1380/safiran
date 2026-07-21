"""Agent API endpoints for MHFA Live panel (backup export)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .agent_auth import verify_agent_token


@csrf_exempt
@require_GET
def db_export(request: HttpRequest):
    """SQLite backup for live.mhfa.ir run_backups command."""
    if not verify_agent_token(request):
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)

    db_path = Path(settings.DATABASES["default"]["NAME"])
    if not db_path.is_file():
        return JsonResponse({"ok": False, "error": "database_not_found"}, status=404)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3")
    tmp.close()
    try:
        shutil.copy2(db_path, tmp.name)
        response = FileResponse(
            open(tmp.name, "rb"),  # noqa: SIM115
            as_attachment=True,
            filename="database.bin",
            content_type="application/octet-stream",
        )
        response["Cache-Control"] = "no-store"
        return response
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        return JsonResponse({"ok": False, "error": "export_failed"}, status=500)
