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

from django.urls import path
from administration.views import TicketZhtml, InvoicePdf, TicketZapi, TicketZpdf, TicketZsimpleFromCloture, \
    RapportFromCloture, ClotureToPrinter, ClotureToMail, RecalculerCloture, TicketZToday, RapportToday, \
    test_new_terminal, test_email_activation, activate

urlpatterns = [
    path('<uuid:pk_uuid>', TicketZhtml.as_view()),
    path('TicketZapi/<uuid:pk_uuid>', TicketZapi.as_view()),
    path('TicketZpdf/<uuid:pk_uuid>', TicketZpdf.as_view()),
    path('invoice/<uuid:pk_uuid>', InvoicePdf.as_view()),

    # Ticket Z et rapport
    path('TicketZsimpleFromCloture/<uuid:pk_uuid>', TicketZsimpleFromCloture.as_view()),
    path('RapportFromCloture/<uuid:pk_uuid>', RapportFromCloture.as_view()),
    path('TicketZToday/', TicketZToday.as_view()),
    path('RapportToday/', RapportToday.as_view()),
    path('ClotureToPrinter/<uuid:pk_uuid>', ClotureToPrinter.as_view()),
    path('ClotureToMail/<uuid:pk_uuid>', ClotureToMail.as_view()),
    path('RecalculerCloture/<uuid:pk_uuid>', RecalculerCloture.as_view()),

    # path('badgeuse/<uuid:pk_uuid>/', badgeuse, name='badgeuse'),

    path('activate/<str:uid>/<str:token>/', activate, name='activate'),

    path('test_mail/test_new_terminal/', test_new_terminal, name='test_new_terminal'),
    path('test_mail/test_email_activation/', test_email_activation, name='test_email_activation')
]
