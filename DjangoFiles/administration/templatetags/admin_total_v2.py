# coding=utf-8
from __future__ import division, print_function, unicode_literals

from django.contrib.admin.templatetags.admin_list import (result_headers,
                                                          result_hidden_fields,
                                                          results)
from django.utils.safestring import mark_safe
import json
import decimal

from django.template import Library
register = Library()




@register.inclusion_tag("admin_totals_v2/change_list_results_totals.html")
def result_list_totals(cl):
    """
    Displays the headers, totals bar and data list together
    """
    cl.aggregations[0] = "TOTAL"

    headers = list(result_headers(cl))
    num_sorted_fields = 0
    for h in headers:
        if h['sortable'] and h['sorted']:
            num_sorted_fields += 1

    # querys = cl.queryset
    # print(querys)
    # list_pk = []
    # for query in querys:
    #     list_pk.append(query.pk)
    # import ipdb; ipdb.set_trace()

    return {'cl': cl,
            'result_hidden_fields': list(result_hidden_fields(cl)),
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'results': list(results(cl)),
            # 'list_pk': list_pk,
            }



class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

@register.filter(is_safe=True)
def js(obj):
    j_obj =json.dumps(obj, cls=DecimalEncoder)
    return mark_safe(j_obj)
