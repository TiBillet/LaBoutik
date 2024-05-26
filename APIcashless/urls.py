"""cashlessDjango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

# from django.conf.urls import url, include
from rest_framework import routers
from APIcashless import views
# from django.contrib import admin
# from django.conf import settings
from django.urls import include, path, re_path


router = routers.DefaultRouter()
router.register(r'checkcarteqruuid', views.CheckCarteQrUuid, basename='checkcarteqruuid')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('check_apikey', views.check_apikey.as_view(),
         name="check_apikey"),
    path('oceco_endpoint', views.oceco_endpoint.as_view(),
         name="oceco_endpoint"),
    path('billetterie_endpoint', views.billetterie_endpoint.as_view(),
         name="billetterie_endpoint"),

    path('salefromlespass', views.SaleFromLespass.as_view(),
         name="salefromlespass"),

    path('billetterie_qrcode_adhesion', views.billetterie_qrcode_adhesion.as_view(),
         name="billetterie_qrcode_adhesion"),
    path('preparations', views.preparations.as_view(),
         name="preparations"),
    path('membre_check', views.membre_check.as_view(),
         name="membre_check"),
    path('chargecard', views.ChargeCard.as_view(),
         name="chargecard"),
    # path('updatefedwallet', views.UpdateFedWalletFromBilletterie.as_view(),
    #      name="updatefedwallet"),
    path('membership', views.Membership.as_view(),
         name="membership"),
    path('onboard_stripe_return/<str:id_acc_connect>/', views.OnboardStripeReturn.as_view(),
         name="onboard_stripe_return"),

    path('signed_key/', views.signed_key.as_view(), name="signed_key"),

    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

]
