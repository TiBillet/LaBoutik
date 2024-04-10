# coding=utf-8
from __future__ import division, print_function, unicode_literals
import datetime
import decimal

from django.utils.safestring import mark_safe
import json
from django.contrib.admin.templatetags.admin_list import (result_headers,
                                                          result_hidden_fields,
                                                          results)
from django.template import Library
register = Library()
from APIcashless.models import ArticleVendu



@register.inclusion_tag("bouton_all_page/button_form.html")
def set_button(cl):

    querys = cl.queryset
    params = cl.params

    ecart_temps_mois = "Pas besoin"
    if len(querys) > 0:
        if type(querys[0]) == ArticleVendu :
            ecart_temps_mois = None

            if params.get('date_time__range__gte') and params.get('date_time__range__lte') :
                min = datetime.datetime.strptime(params.get('date_time__range__gte'), "%d/%m/%Y")
                max = datetime.datetime.strptime(params.get('date_time__range__lte'), "%d/%m/%Y")
                ecart_temps_mois = ( max - min ) < datetime.timedelta(days=31)

    list_pk = []
    for query in querys:
        list_pk.append(str(query.pk))

    # import ipdb; ipdb.set_trace()

    return {'cl': cl,
            'ecart_temps_mois': ecart_temps_mois,
            'list_pk': list_pk,
            'len_list_pk': len(list_pk)
            }


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


@register.filter(is_safe=True)
def js(obj):
    # import ipdb; ipdb.set_trace()
    ms = mark_safe(json.dumps(obj, cls=DecimalEncoder))
    return ms