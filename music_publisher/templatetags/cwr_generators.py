"""Filters used in generation of CWR files.
"""
from decimal import Decimal, ROUND_HALF_UP

from django import template
from django.conf import settings

from music_publisher import models
from music_metadata.territories.territory import Territory

register = template.Library()


@register.filter(name="rjust")
def rjust(value, length):
    """Format general numeric fields."""
    if value is None or value == "":
        value = "0"
    else:
        value = str(value)
    value = value.rjust(length, "0")[0:length]
    return value


@register.filter(name="ljust")
def ljust(value, length):
    """Format general alphanumeric fields."""
    if value is None:
        value = ""
    else:
        value = str(value)
    value = value.ljust(length, " ")[0:length]
    return value


@register.filter(name="soc")
def soc(value):
    """Format society fields."""
    if not value:
        return " "
    value = value.rjust(3, "0")
    return value


@register.filter(name="cwrparty")
def cwrparty(value):
    """Format IPI Name Number as the 9-digit CWR party identifier.

    SADAIC expects the HDR sender identifier as Sender Type + 9-digit IP.
    Examples:
    01135451385 -> 113545138
    00803318077 -> 803318077
    """
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    digits = digits.lstrip("0")
    return digits[:9].rjust(9, "0")


@register.filter(name="cwrshare")
def cwrshare(value):
    """Get CWR-compatible output for share fields"""
    value = (value * Decimal("10000")).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )
    value = int(value)
    return "{:05d}".format(value)
