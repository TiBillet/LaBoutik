from django.urls import path
from rest_framework import routers
from htmxview import views

app_name = 'htmxview'

router = routers.DefaultRouter()

router.register(r'sales', views.Sales, basename='sales')
router.register(r'appsettings', views.AppSettings, basename='appsettings')

# router.register(r'membership', views.Membership, basename='membership')

router.register(r'kiosk', views.Kiosk, basename='kiosk')
router.register(r'print', views.Print, basename='print')
router.register(r'falseprinter', views.FalsePrinter, basename='falseprinter')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
                  # path('printer/<uuid:pos_uuid>/', views.tuto_htmx, name='printer'),
                  # path('tpe_stripe/', views.tuto_htmx, name='stripe_tpe'),

                  ## WEBSOCKET
                  ## TUTO WEBSOCKET
                  path('tuto_htmx/', views.tuto_htmx, name='stripe_tpe'),
                  path('tuto_js/<str:room_name>/', views.tuto_js, name='room'),

              ] + router.urls
