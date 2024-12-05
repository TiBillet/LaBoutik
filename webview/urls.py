
from django.conf.urls import url
from django.urls import path

from webview import views


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url('new_hardware', views.new_hardware),
    url('login_hardware', views.login_hardware),

    # url('annulation_derniere_action', views.annulation_derniere_action),
    url('paiement', views.paiement),
    url('check_carte', views.check_carte),

    path('tables', views.tables),
    path('tables_et_commandes', views.tables_et_commandes),
    path('table_solo_et_commande/<str:table>', views.table_solo_et_commande),
    path('preparation/<str:table>', views.preparation),
    url('preparation', views.preparation),
    # nico all orders
    # url('allOrders', views.allOrders),

    url('reprint', views.reprint),
    path('ticket_client/<str:tagid>', views.ticket_client),
    url('close_all_pos', views.close_all_pos),

    # url('nfc_reader', views.nfc_reader),
    # path('nfc_reader', views.NfcReader.as_view(), name="nfc_reader"),

    # path('printer/<uuid:pos_uuid>/', views.tuto_htmx, name='printer'),

    ## WEBSOCKET
    ## TUTO WEBSOCKET
    path('tuto_htmx/<str:pos_uuid>/', views.tuto_htmx, name='stripe_tpe'),
    path('tuto_js/<str:room_name>/', views.tuto_js, name='room'),


    # La vue de l'application :
    url('', views.index),
]
