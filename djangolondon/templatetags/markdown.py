from django.template import Library
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = Library()

_md = MarkdownIt()


@register.filter
def markdown(value):
    return mark_safe(_md.render(value))


@register.filter
def markdown_inline(value):
    """Render Markdown that sits within a line, like a quiz question."""
    return mark_safe(_md.renderInline(value))
