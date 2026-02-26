"""
ویجت ویرایشگر غنی (WYSIWYG) با CKEditor 4 (لوکال).
بدون CDN؛ متن و تصویر تو در تو مثل وردپرس.
"""
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe


class RichTextEditorWidget(forms.Textarea):
    """
    ویجت ویرایشگر غنی با CKEditor 4.
    پشتیبانی از متن، تصویر، جدول، لینک و سایر المان‌های HTML.
    """

    class Media:
        js = (
            "js/vendors/ckeditor/ckeditor.js",
        )

    def __init__(self, attrs=None, upload_url=None):
        super().__init__(attrs)
        self.upload_url = upload_url or "/admin/ckeditor-upload/"

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault("class", "")
        if "ckeditor-widget" not in attrs["class"]:
            attrs["class"] = (attrs["class"] + " ckeditor-widget").strip()
        attrs.setdefault("dir", "rtl")
        html = super().render(name, value, attrs, renderer)
        upload_url = getattr(settings, "CKEDITOR_UPLOAD_URL", self.upload_url)
        config = {
            "height": 400,
            "language": "fa",
            "contentsLangDirection": "rtl",
            "filebrowserUploadUrl": upload_url,
            "filebrowserImageUploadUrl": upload_url,
            "extraPlugins": "uploadimage",
            "uploadUrl": upload_url,
            "removePlugins": "elementspath",
            "fillEmptyBlocks": False,
            "toolbar": [
                {"name": "document", "items": ["Source"]},
                {"name": "clipboard", "items": ["Cut", "Copy", "Paste", "PasteText", "PasteFromWord", "-", "Undo", "Redo"]},
                {"name": "editing", "items": ["Find", "Replace", "-", "SelectAll"]},
                {"name": "basicstyles", "items": ["Bold", "Italic", "Underline", "Strike", "Subscript", "Superscript", "-", "RemoveFormat"]},
                {"name": "paragraph", "items": ["NumberedList", "BulletedList", "-", "Outdent", "Indent", "-", "Blockquote", "CreateDiv", "-", "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock", "-", "BidiLtr", "BidiRtl"]},
                {"name": "links", "items": ["Link", "Unlink", "Anchor"]},
                {"name": "insert", "items": ["Image", "Table", "HorizontalRule", "SpecialChar", "PageBreak", "Iframe"]},
                {"name": "styles", "items": ["Styles", "Format", "Font", "FontSize"]},
                {"name": "colors", "items": ["TextColor", "BGColor"]},
                {"name": "tools", "items": ["Maximize", "ShowBlocks"]},
            ],
        }
        import json
        config_json = json.dumps(config, ensure_ascii=False)
        init_script = f"""
<script>
(function() {{
    function initCKEditor() {{
        if (typeof CKEDITOR === 'undefined') return;
        var textareas = document.querySelectorAll('textarea.ckeditor-widget');
        textareas.forEach(function(ta) {{
            if (ta.id && !CKEDITOR.instances[ta.id]) {{
                CKEDITOR.replace(ta.id, {config_json});
            }}
        }});
    }}
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initCKEditor);
    }} else {{
        initCKEditor();
    }}
}})();
</script>
"""
        return mark_safe(html + init_script)
