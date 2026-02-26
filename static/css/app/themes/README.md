# راهنمای تم‌ها

## افزودن تم جدید

۱. فایل `theme-نام.css` بسازید (مثال: `theme-ocean.css`)
۲. متغیرهای مورد نظر را override کنید:

```css
[data-theme="ocean"] {
  --color-primary: #0ea5e9;
  --color-accent: #06b6d4;
  /* ... */
}
```

۳. در قالب یا base.html تم را لود کنید:

```html
{% block theme_css %}
<link rel="stylesheet" href="{% static 'css/app/themes/theme-ocean.css' %}">
{% endblock %}
```

۴. به تگ `<html>` مقدار `data-theme="ocean"` بدهید (با JavaScript یا در قالب).

## متغیرهای موجود

| متغیر | کاربرد |
|-------|--------|
| `--color-primary` | رنگ اصلی |
| `--color-accent` | رنگ تاکید |
| `--color-text` | متن معمولی |
| `--color-heading` | عناوین |
| `--color-bg` | پس‌زمینه |
| `--gradient-primary` | گرادیان دکمه‌ها |
| `--shadow-*` | سایه‌ها |

لیست کامل در `variables.css` موجود است.
