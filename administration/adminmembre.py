from django.contrib import admin
from APIcashless.models import Membre, Configuration, CarteCashless
from jet.admin import CompactInline
from django import forms
from django.contrib.admin import AdminSite
from .admin_commun import *

# try:
#     configuration = Configuration.get_solo()
# except Exception:
#     print('pas de config')
#     pass


class MembreAdminSite(AdminSite):
    site_header = "TiBillet Membre Admin"
    site_title = "TiBillet Membre Admin"
    site_url = '/adminmembre'

    # index_title = "Welcome to TiBillet Admin Portal"

    def has_permission(self, request):
        """
        Removed check for is_staff.
        """
        return request.user.is_active


membre_admin_site = MembreAdminSite(name='adminmembre')




membre_admin_site.register(Membre, MembresAdmin)
