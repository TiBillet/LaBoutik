from django.urls import path
from rest_framework import routers
from htmxview import views

router = routers.DefaultRouter()

router.register(r'sales', views.Sales, basename='sales')
router.register(r'membership', views.Membership, basename='membership')
router.register(r'tpe_stripe', views.TpeStripe, basename='tpe_stripe')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
                  # path('printer/<uuid:pos_uuid>/', views.tuto_htmx, name='printer'),
                  path('tpe_stripe/', views.tuto_htmx, name='stripe_tpe'),

                  ## WEBSOCKET
                  ## TUTO WEBSOCKET
                  path('tuto_htmx/', views.tuto_htmx, name='stripe_tpe'),
                  path('tuto_js/<str:room_name>/', views.tuto_js, name='room'),

              ] + router.urls
