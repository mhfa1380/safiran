"""Path converters for Persian/Unicode URL segments."""


class UnicodeSlugConverter:
    """Slug با حروف فارسی و یونیکد (مطابق slugify(..., allow_unicode=True))."""

    regex = r"[-\w]+"

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return value
