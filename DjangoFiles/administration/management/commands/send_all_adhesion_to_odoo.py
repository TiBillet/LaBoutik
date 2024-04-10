from django.core.management.base import BaseCommand
from datetime import timedelta, datetime
import os
from APIcashless.models import Membre, ArticleVendu, Articles

from APIcashless.tasks import adhesion_to_odoo


'''
class Command(BaseCommand):
    def handle(self, *args, **options):
        for adhesion in ArticleVendu.objects.filter(article__methode_choices=Articles.ADHESIONS)[:10]:
            adhesion_to_odoo(adhesion.pk)
'''
