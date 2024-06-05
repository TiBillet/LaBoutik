import logging
import os
import time

from dateutil.relativedelta import relativedelta
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
        config = Configuration.get_solo()
        fedowAPI = FedowAPI()

        self_place: Place = Place.objects.get(uuid=config.fedow_place_uuid)

        # Toute les cartes utilisées depuis 26h
        self_cards_26h = CarteCashless.objects.filter(
            origin__place=self_place,
            cartes_maitresses__isnull=True,
            articles_vendus__date_time__gt=localtime() - relativedelta(hours=26),
        ).distinct()

        self_cards_spp0 = CarteCashless.objects.filter(
            origin__place=self_place,
            cartes_maitresses__isnull=True,
            assets__qty__gt=0,
        ).distinct()

        import ipdb; ipdb.set_trace()

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
            # Update from fedow
            # Ptit time pour éviter de DDOS
            time.sleep(0.1)
            fedowAPI.NFCcard.retrieve(card.tag_id)
            time_bomb_qty = 0
            for asset in card.get_payment_assets():
                asset: Assets
                if asset.monnaie.place_origin == self_place and asset.qty > 0:
                    time_bomb_qty += asset.qty

            if time_bomb_qty > 0:
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
                else:
                    error_msg = f"Time Bomb validator error : {validator_transaction.errors}"
                    # Pour envoyer un message a sentry :
                    if os.environ.get('SENTRY_DNS'):
                        capture_message(f"{error_msg}")
                    logger.error(f"{error_msg}")

            # Void card : Remove user wallet from card
            void_data = fedowAPI.NFCcard.void(
                user_card_firstTagId=card.tag_id,
                primary_card_fisrtTagId=responsable_card.carte.tag_id,
            )

