# coding=utf-8
from __future__ import division, print_function, unicode_literals

from django.template import Library

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
