from APIcashless.models import *
from django.core.management.base import BaseCommand, CommandError
from datetime import timedelta, datetime


class Command(BaseCommand):
    def handle(self, *args, **options):
        for x in Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_GIFT):
            if x.qty > 0 :
                x.qty = 0
                x.save()
