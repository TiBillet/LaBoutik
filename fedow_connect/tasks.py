import logging
from time import sleep

from django.core.cache import cache
from django.core.paginator import Paginator

from django.conf import settings

from APIcashless.models import CarteCashless, Membre, CarteMaitresse, Configuration, Wallet, ArticleVendu, \
    MoyenPaiement, Origin, Place
from Cashless.celery import app
from fedow_connect.fedow_api import FedowAPI

logger = logging.getLogger(__name__)
from django.core.management import call_command



def get_fedow():
    """
    Une fois le Hanshake effectué via l'admin, on lance un celery async pour envoyer les infos d'assets et de cartes cashless

    @return:
    """
    fedowAPI = FedowAPI()
    config = Configuration.get_solo()
    fedow_domain = fedowAPI.config.fedow_domain
    fedow_place_admin_apikey = config.fedow_place_admin_apikey
    logger.info(f"fedow domain : {fedow_domain}")
    count = 0
    while not fedow_domain or not fedow_place_admin_apikey:
        config.clear_cache()
        config = Configuration.get_solo()
        config.refresh_from_db()
        fedowAPI = FedowAPI(config)
        logger.info(f"fedow domain from config : {fedowAPI.config.fedow_domain}")
        logger.info(f"fedow domain from api : {fedowAPI.config.fedow_domain}")
        fedow_domain = fedowAPI.config.fedow_domain
        fedow_place_admin_apikey = config.fedow_place_admin_apikey
        logger.info("Waiting for handshake to be done")
        count += 1
        sleep(1)
        if count == 20:
            raise Exception("Waiting for handshake to be done")

    logger.info(f"fedow domain : {fedow_domain}")
    return fedowAPI

def send_assets():
    # Envoie des assets et de l'adhésion
    fedowAPI = FedowAPI()
    responses = fedowAPI.send_assets_from_cashless()
    for response in responses:
        if response.status_code != 201:
            raise Exception(f"Erreur lors de l'envoi des assets : {responses}")

    # Vérification que les assets sont présent.
    # Si Origin et Place n'existent pas, c'est ici qu'ils sont créé :
    assets_acc = fedowAPI.place.get_accepted_assets()
    assets = [MoyenPaiement.objects.get(pk=asset.get('uuid')) for asset in assets_acc]

    return assets



def create_cards_and_pre_token():
    # Envoie des cartes et des uuid des tokens
    fedowAPI = FedowAPI()
    cartes = CarteCashless.objects.all()
    for carte in cartes:
        print(f"send carte number : {carte.number}")
        response = fedowAPI.NFCcard.create([carte,])
        if response.status_code == 201:
            pass
        elif response.status_code == 206:
            logger.warning(f"Partial content, cards already exist, created {len(response.json())} only")
        else:
            raise Exception(f"Erreur lors de l'envoi des cartes : {response}")

def send_existing_tokens():
    # Envoi des tokens
    fedowAPI = FedowAPI()
    cartes = CarteCashless.objects.all()
    carte_primaire = CarteMaitresse.objects.filter(carte__membre__isnull=False).first()
    for carte in cartes:
        assets = [asset for asset in carte.assets.filter(
            monnaie__categorie__in=[MoyenPaiement.LOCAL_EURO, MoyenPaiement.LOCAL_GIFT])]

        wallet = carte.get_wallet()
        if not wallet:
            # Ce serializer créé le wallet avec l'uuid de Fedow, mais remets à ZERO le solde
            serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
            wallet_uuid = serialized_card['wallet']['uuid']
        else :
            wallet_uuid = wallet.uuid

        for asset in assets:
            if asset.qty > 0:
                serialized_transaction = fedowAPI.transaction.refill_wallet(
                    amount=int(asset.qty*100),
                    wallet=f"{wallet_uuid}",
                    asset=f"{asset.monnaie.pk}",
                    user_card_firstTagId=f"{carte.tag_id}",
                    primary_card_fisrtTagId=carte_primaire.carte.tag_id,
                )

        # # On lance un fedow retrieve, et si on est en TEST, on accepte les monnaies automatiquement
        # call_command('import_assets')

"""
def send_existing_members():
    # Envoie des comptes membres
    fedowAPI = FedowAPI()

    # refaire ça en mode atomique !!!!
    for membre in Membre.objects.filter(email__isnull=False).exclude(email=""):
        carte = None
        wallet = None
        if membre.CarteCashless_Membre.count() > 0:
            for carte in membre.CarteCashless_Membre.all():
                wallet = fedowAPI.NFCcard.link_user(email=membre.email, card=carte)
        if membre.date_derniere_cotisation:
            if not wallet:
                wallet, created = fedowAPI.wallet.get_or_create_wallet_from_email(email=membre.email)
                if not membre.wallet:
                    membre.wallet = wallet
                    membre.save()
                elif membre.wallet != wallet:
                    raise Exception("Wallet and member mismatch")
            adh = fedowAPI.subscription.create(
                wallet=f"{wallet.uuid}",
                amount=int(membre.cotisation * 100),
                date=membre.date_derniere_cotisation,
                user_card_firstTagId=carte.tag_id if carte else None,
            )
"""

@app.task
def set_primary_card(card_pk, delete=False):
    cache.clear()
    config = Configuration.get_solo()
    if config.can_fedow():
        carte = CarteCashless.objects.get(pk=card_pk)
        fedowAPI = FedowAPI()
        response = fedowAPI.NFCcard.set_primary(carte, delete=delete)
        logger.info(f"set_primary_card ->{carte.membre} {carte.number} : {response}")


@app.task
def create_card_to_fedow(card_pk):
    cache.clear()
    config = Configuration.get_solo()

    if config.can_fedow():
        carte = CarteCashless.objects.get(pk=card_pk)
        fedowAPI = FedowAPI()
        response = fedowAPI.NFCcard.create([carte])
        logger.info(f"create_card_to_fedow ->{carte.membre} {carte.number} : {response}")



@app.task
def after_handshake():
    Origin.objects.all().delete()
    Place.objects.all().delete()
    MoyenPaiement.objects.filter(categorie=MoyenPaiement.STRIPE_FED).delete()

    # Va récupérer les assets adhésions/badge
    fedowAPI = FedowAPI()
    fedowAPI.place.get_accepted_assets()

    config = Configuration.get_solo()
    # Le bolléen qui indique que tout s'est bien passé
    config.fedow_synced = True
    config.save()
    cache.clear()


@app.task
def badgeuse_to_fedow(article_vendu_pk):
    logger.info(f"badgeuse_to_fedow {article_vendu_pk}")
    article_vendu = ArticleVendu.objects.get(pk=article_vendu_pk)
    fedowAPI = FedowAPI()
    transaction = fedowAPI.NFCcard.badge(article_vendu)

    return transaction



