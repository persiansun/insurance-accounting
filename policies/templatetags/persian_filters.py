from django import template
from django.template.defaultfilters import stringfilter
import re

register = template.Library()


@register.filter(is_safe=True)
def intcomma_fa(value):
    """
    Format a number with commas as thousands separators, regardless of locale.
    Works with int, float, string, or None.
    Returns the formatted string.
    """
    if value is None:
        return '0'

    try:
        # Convert to int if possible (handles float, string, Decimal)
        if isinstance(value, float):
            value = int(value)
        else:
            value = int(value)
    except (ValueError, TypeError):
        try:
            value = int(float(str(value)))
        except (ValueError, TypeError):
            return str(value)

    # Format with commas
    result = f'{value:,}'
    return result


@register.filter(is_safe=True)
def currency_fa(value):
    """
    Format a number with commas and add 'ریال' suffix.
    """
    formatted = intcomma_fa(value)
    if formatted and formatted != '0':
        return f'{formatted} ریال'
    return '0 ریال'
