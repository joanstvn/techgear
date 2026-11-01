from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name, css_class=""):
    """Renderiza un icono del sprite SVG local (Material Symbols)."""
    return format_html(
        '<svg class="icon {}" aria-hidden="true" focusable="false">'
        '<use href="{}#{}"></use></svg>',
        css_class,
        static("store/img/icons.svg"),
        name,
    )
