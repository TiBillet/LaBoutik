import logging
import os
import time

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.timezone import localtime
from sentry_sdk import capture_message

from APIcashless.models import Configuration, Place, CarteCashless, \
    Categorie, Articles, PointDeVente, Assets, CarteMaitresse
from fedow_connect.fedow_api import FedowAPI
from webview.validators import DataAchatDepuisClientValidator
from webview.views import Commande

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        User = get_user_model()