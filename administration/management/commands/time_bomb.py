import os

from django.utils import timezone
from sentry_sdk import capture_message

from APIcashless.models import CommandeSauvegarde, Table, Configuration, GroupementCategorie, Place, CarteCashless, \
    Categorie, Articles, Membre, PointDeVente, Assets, CarteMaitresse
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from APIcashless.tasks import GetOrCreateRapportFromDate
import logging

from webview.validators import DataAchatDepuisClientValidator
from webview.views import Commande

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        config = Configuration.get_solo()
        self_place: Place = Place.objects.get(uuid=config.fedow_place_uuid)
        self_cards = CarteCashless.objects.filter(
            origin__place=self_place,
            assets__qty__gt=0,
        ).distinct()

        cat_time_bomb, created = Categorie.objects.get_or_create(name='TIME BOMB')
        # L'article TIME BOMB est considéré comme une vente,
        # afin de bien le voir dans le rapport comptable comment entrée.
        art_time_bomb, created = Articles.objects.get_or_create(
            name='TIME BOMB',
            categorie=cat_time_bomb,
            prix=1
        )
        responsable_card = CarteMaitresse.objects.filter(
            carte__membre__isnull=False,
        ).first()
        responsable = responsable_card.carte.membre
        if not responsable:
            raise Exception("No Primary card for Time Bomb")

        pos_time_bomb, created = PointDeVente.objects.get_or_create(name="TIME BOMB")

        for card in self_cards:
            card: CarteCashless
            time_bomb_qty = 0
            for asset in card.get_payment_assets():
                asset: Assets
                # seulement les asset de cette place :
                if asset.monnaie.place_origin == self_place and asset.qty > 0 :
                    time_bomb_qty += asset.qty

            if time_bomb_qty > 0 :
                # Fabrication de la requete pour incrémenter
                # On passe par la même méthode que tout le reste
                data_ext = {
                    "pk_responsable": responsable.pk,
                    "pk_pdv": pos_time_bomb.pk,
                    "tag_id": card.tag_id,
                    "moyen_paiement": "nfc",
                    "total": time_bomb_qty,
                    "articles": [{
                        'pk': art_time_bomb.pk,
                        'qty': time_bomb_qty,
                    }, ],
                }
                validator_transaction = DataAchatDepuisClientValidator(data=data_ext)
                if validator_transaction.is_valid():
                    data = validator_transaction.validated_data
                    commande = Commande(data)
                    commande_valide = commande.validation()
                else :
                    error_msg = f"Time Bomb validator error : {validator_transaction.errors}"
                    # Pour envoyer un message a sentry :
                    if os.environ.get('SENTRY_DNS'):
                        capture_message(f"{error_msg}")
                    logger.error(f"{error_msg}")

