"""Cashless URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.conf.urls.static import static

from django.urls import path
from django.conf.urls import url, include

# from APIcashless import urls as APIcashlessUrl
from webview import views as webviewview
from webview import urls as webview_url

from APIcashless import urls as cashless_url
from administration import urls as administration_url

from fedow_connect import urls as fedow_connect_url
from administration.adminroot import root_admin_site
from administration.adminstaff import staff_admin_site
from administration.adminmembre import membre_admin_site

from APIcashless import views as APIcahsless_views
from django.conf import settings
# from django.contrib.auth import views as auth_views

# admin.autodiscover()
def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    url(r'^jet/', include('jet.urls', 'jet')),  # Django JET URLS
    url(r'^jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    # path('jet_api/', include('jet_django.urls')),
    # path('adminroot/', root_admin_site.urls, name="adminroot"),
    path('adminstaff/', staff_admin_site.urls, name="adminstaff"),
    path('adminmembre/', membre_admin_site.urls, name="adminmembre"),
    # path('helloasso_trigger/', APIcahsless_views.helloasso.as_view(), name="helloasso_trigger"),

    url('wv/', include(webview_url)),
    url('api/', include(cashless_url)),
    url('fedow/', include(fedow_connect_url)),
    url('rapport/', include(administration_url)),
    # path('rapport/<uuid:pk_uuid>', TableauJour.as_view()),

    #TODO: Utiliser le cache en prod
    path('i18n/', include('django.conf.urls.i18n')),

    path('sentry-debug/', trigger_error),

    # path('admin/', admin.site.urls),
    # path('accounts/', include('django.contrib.auth.urls')),
    # url(r'^', auth_views.LoginView.as_view(template_name='login.html')),
    path('', webviewview.login_admin),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#TODO : retirer cette fonction static old school ?

# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns = [
#         path('__debug__/', include(debug_toolbar.urls)),
#     ] + urlpatterns
#
