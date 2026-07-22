from panel.ai import ai_enabled


def panel_ai(request):
    return {"panel_ai_enabled": ai_enabled()}
