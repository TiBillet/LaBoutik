# coding=utf-8
from __future__ import division, print_function, unicode_literals

from django.template import Library
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, get_current_timezone

register = Library()


@register.filter(is_safe=True)
def abs(obj):
    return abs(obj)


@register.filter(is_safe=True)
def catname(obj):
    return obj.get_display_name()


@register.filter(is_safe=True)
def getvalue(obj, value):
    return obj.get(value, None)


@register.filter
def format_iso_date(value):
    """
    Convertit une date ISO en une date lisible.
    Exemple d'entrée : "2025-01-27T16:20:39.379+01:00"
    Exemple de sortie : "27 jan. 2025 16:20"
    """
    try:
        # Parser la date ISO
        date_obj = parse_datetime(value)
        if date_obj and date_obj.tzinfo is None:
            # Ajouter le fuseau horaire si manquant
            date_obj = make_aware(date_obj, get_current_timezone())

        # Formater la date
        return date_obj.strftime('%d %b %Y %H:%M') if date_obj else value
    except Exception:
        return value