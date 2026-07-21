"""
ویجت ویرایشگر غنی (WYSIWYG) با CKEditor 4 (لوکال).
بدون CDN؛ متن و تصویر تو در تو مثل وردپرس.
"""
import json

from django import forms
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from core.ckeditor_views import get_ckeditor_upload_url


CKEDITOR_DEFAULT_CONFIG = {
    "height": 400,
    "language": "fa",
    "contentsLangDirection": "rtl",
    "bodyClass": "ck-content",
    "stylesSet": "safiran",
    "removePlugins": "elementspath,exportpdf",
    "versionCheck": False,
    "fillEmptyBlocks": False,
    "clipboard_handleImages": False,
    "filebrowserUploadMethod": "xhr",
    "image_previewText": " ",
    "disableObjectResizing": False,
    "extraAllowedContent": (
        "img[alt,src,width,height,class,style,align]{float,margin,display,max-width}; "
        "p div span h2 h3 h4 ul ol li table tr td th blockquote"
    ),
    "toolbar": [
        {"name": "document", "items": ["Source"]},
        {"name": "clipboard", "items": ["Cut", "Copy", "Paste", "PasteText", "PasteFromWord", "-", "Undo", "Redo"]},
        {"name": "editing", "items": ["Find", "Replace", "-", "SelectAll"]},
        {"name": "basicstyles", "items": ["Bold", "Italic", "Underline", "Strike", "Subscript", "Superscript", "-", "RemoveFormat"]},
        {"name": "paragraph", "items": ["NumberedList", "BulletedList", "-", "Outdent", "Indent", "-", "Blockquote", "-", "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock", "-", "BidiLtr", "BidiRtl"]},
        {"name": "links", "items": ["Link", "Unlink", "Anchor"]},
        {"name": "insert", "items": ["Image", "Table", "HorizontalRule", "SpecialChar"]},
        {"name": "imagestyles", "items": ["Styles"]},
        {"name": "styles", "items": ["Format", "Font", "FontSize"]},
        {"name": "colors", "items": ["TextColor", "BGColor"]},
        {"name": "tools", "items": ["Maximize", "ShowBlocks"]},
    ],
}


class RichTextEditorWidget(forms.Textarea):
    """ویجت ویرایشگر غنی با CKEditor 4."""

    class Media:
        js = (
            "js/vendors/ckeditor/ckeditor.js",
            "js/app/ckeditor-safiran.js",
        )

    def __init__(self, attrs=None, upload_url=None, ckeditor_config=None, request=None):
        super().__init__(attrs)
        self.request = request
        self.upload_url = upload_url
        self.ckeditor_config = ckeditor_config or {}

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault("class", "")
        if "ckeditor-widget" not in attrs["class"]:
            attrs["class"] = (attrs["class"] + " ckeditor-widget").strip()
        attrs.setdefault("dir", "rtl")
        html = super().render(name, value, attrs, renderer)
        editor_hint = (
            '<p class="ckeditor-field-hint" style="font-size:.8rem;color:#6b7280;'
            'margin:0 0 .5rem;">'
            "تصویر: دوبارکلیک → پنجره Image (عرض و تراز) | یا انتخاب عکس → منوی "
            "<strong>Styles</strong> (کوچک/متوسط/وسط‌چین)"
            "</p>"
        )
        upload_url = self.upload_url or get_ckeditor_upload_url(self.request)
        config = {
            **CKEDITOR_DEFAULT_CONFIG,
            **self.ckeditor_config,
            "contentsCss": [static("css/ck-content.css")],
            "uploadUrl": upload_url,
            "imageUploadUrl": upload_url,
            "filebrowserUploadUrl": upload_url,
            "filebrowserImageUploadUrl": upload_url,
            "extraPlugins": "uploadimage",
        }
        config_json = json.dumps(config, ensure_ascii=False)
        init_script = f"""
<script>
(function() {{
    function getCsrfToken() {{
        var match = document.cookie.match(/(?:^|;\\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }}

    if (typeof CKEDITOR !== 'undefined' && !window.__safiranCkUploadCsrf) {{
        window.__safiranCkUploadCsrf = true;
        CKEDITOR.on('instanceReady', function(evt) {{
            evt.editor.on('fileUploadRequest', function(ev) {{
                var xhr = ev.data.fileLoader.xhr;
                var token = getCsrfToken();
                if (token) xhr.setRequestHeader('X-CSRFToken', token);
            }});
            evt.editor.on('fileUploadResponse', function(ev) {{
                var data = ev.data;
                var loader = data.fileLoader;
                try {{
                    var parsed = JSON.parse(loader.xhr.responseText || '{{}}');
                    if (parsed.url) {{
                        loader.url = parsed.url;
                        data.url = parsed.url;
                    }}
                    if (parsed.error && parsed.error.message) {{
                        data.message = parsed.error.message;
                    }}
                }} catch (e) {{}}
            }});
        }});
    }}

    function initCKEditor() {{
        if (typeof CKEDITOR === 'undefined') return;
        document.querySelectorAll('textarea.ckeditor-widget').forEach(function(ta) {{
            if (!ta.id) return;
            if (CKEDITOR.instances[ta.id]) {{
                CKEDITOR.instances[ta.id].destroy(true);
            }}
            CKEDITOR.replace(ta.id, {config_json});
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
        return mark_safe(editor_hint + html + init_script)


def rich_text_widget(request=None, **kwargs):
    """ساخت ویجت با URL آپلود مطلق بر اساس درخواست ادمین."""
    return RichTextEditorWidget(request=request, **kwargs)
