import json
import logging
import requests
from decimal import Decimal
from uuid import uuid4, UUID

from fedow_connect.serializers import CardSerializer
from fedow_connect.utils import sign_message, verify_signature, data_to_b64
from fedow_connect.validators import AssetValidator, CardValidator, \
    TransactionValidator, WalletValidator

### DJANGO PARTS
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import localtime
from django.core.cache import cache
from APIcashless.models import CarteCashless, MoyenPaiement, Membre, ArticleVendu, Configuration, Wallet, Articles
from APIcashless.models import Wallet as WalletDb

logger = logging.getLogger(__name__)


### UTILS

def dround_fromcents(value):
    return Decimal(value / 100).quantize(Decimal('1.00'))


### FEDOW API

### GENERIC GET AND POST ###
def _put(config, path, data):
    fedow_domain = config.fedow_domain
    fedow_place_admin_apikey = config.fedow_place_admin_apikey

    # Signature de la requete
    private_key = config.get_private_key()
    signature = sign_message(
        data_to_b64(data),
        private_key,
    ).decode('utf-8')

    # Ici, on s'autovérifie :
    # Assert volontaire. Si non effectué en prod, ce n'est pas grave.
    assert verify_signature(config.get_public_key(),
                            data_to_b64(data),
                            signature)

    session = requests.Session()
    request_fedow = session.put(
        f"https://{fedow_domain}/{path}/",
        headers={
            "Authorization": f"Api-Key {fedow_place_admin_apikey}",
            "Signature": f"{signature}",
            "Content-type": "application/json",
        },
        data=json.dumps(data),
        verify=bool(not settings.DEBUG),
    )
    # TODO: Vérifier la signature de FEDOW
    session.close()
    return request_fedow


### GENERIC GET AND POST ###
def _post(config, path, data):
    fedow_domain = config.fedow_domain
    fedow_place_admin_apikey = config.fedow_place_admin_apikey

    # Signature de la requete
    private_key = config.get_private_key()
    signature = sign_message(
        data_to_b64(data),
        private_key,
    ).decode('utf-8')

    # Ici, on s'autovérifie :
    # Assert volontaire. Si non effectué en prod, ce n'est pas grave.
    # logger.debug("_post verify_signature start")
    assert verify_signature(config.get_public_key(),
                            data_to_b64(data),
                            signature)
    # logger.debug("_post verify_signature end")

    session = requests.Session()
    request_fedow = session.post(
        f"https://{fedow_domain}/{path}/",
        headers={
            "Authorization": f"Api-Key {fedow_place_admin_apikey}",
            "Signature": f"{signature}",
            "Content-type": "application/json",
        },
        data=json.dumps(data),
        verify=bool(not settings.DEBUG),
    )
    # TODO: Vérifier la signature de FEDOW
    session.close()
    return request_fedow


def _get(config, path: list, arg=None, param=None):
    fedow_domain = config.fedow_domain
    fedow_place_admin_apikey = config.fedow_place_admin_apikey
    PATH = f'/{"/".join(path)}/'

    # Signature de la requete : on signe le path
    private_key = config.get_private_key()
    # Signature de la requete : on signe la clé

    signature = sign_message(
        fedow_place_admin_apikey.encode('utf8'),
        private_key,
    ).decode('utf-8')

    # Ici, on s'autovérifie :
    # Assert volontaire. Si non effectué en prod, ce n'est pas grave.
    assert verify_signature(config.get_public_key(),
                            fedow_place_admin_apikey.encode('utf8'),
                            signature)

    session = requests.Session()
    request_fedow = session.get(
        f"https://{fedow_domain}{PATH}",
        headers={
            'Authorization': f'Api-Key {fedow_place_admin_apikey}',
            "Signature": f"{signature}",
        },
        verify=bool(not settings.DEBUG),
    )
    session.close()
    # TODO: Vérifier la signature de FEDOW
    return request_fedow


### END GENERIC GET AND POST ###


class Subscription():
    def __init__(self, config: Configuration or None = None):
        self.config: Configuration = config
        if config is None:
            self.config = Configuration.get_solo()

    def create(self,
               wallet,
               amount: int,
               date=None,
               user_card_firstTagId=None,
               primary_card_fisrtTagId=None,
               article: Articles=None,
               ):

        if not date:
            date = localtime()

        if not article:
            raise ValueError('Article must be an Membership product')
        if article.methode_choices != Articles.ADHESIONS:
            raise ValueError('Article must be an Membership product')
        if not article.subscription_fedow_asset:
            raise ValueError('Fedow subscription_fedow_asset must be set')

        subscription = {
            "amount": int(amount),
            "sender": f"{self.config.fedow_place_wallet_uuid}",
            "receiver": f"{UUID(wallet)}",
            "asset": f"{article.subscription_fedow_asset.pk}",
            "subscription_start_datetime": date.isoformat(),
        }

        if user_card_firstTagId:
            subscription['user_card_firstTagId'] = f"{user_card_firstTagId}"
        if primary_card_fisrtTagId:
            subscription['primary_card_fisrtTagId'] = f"{primary_card_fisrtTagId}"

        response_subscription = _post(self.config, 'transaction', subscription)

        if response_subscription.status_code == 201:
            serialized_transaction = TransactionValidator(data=response_subscription.json())
            if serialized_transaction.is_valid():
                return serialized_transaction.validated_data

            logger.error(serialized_transaction.errors)
            return serialized_transaction.errors

        else:
            logger.error(response_subscription.json())
            import ipdb; ipdb.set_trace()
            return response_subscription.status_code

    def retrieve(self, wallet: uuid4 = None):
        response_sub = _get(self.config, ['subscription', f"{UUID(wallet)}"])
        if response_sub.status_code == 200:
            return response_sub

        raise Exception(f"{response_sub.status_code}")


class NFCCard():
    def __init__(self, config: Configuration or None = None):
        self.config: Configuration = config
        if config is None:
            self.config = Configuration.get_solo()

    def badge(self, article_vendu: ArticleVendu = None, data: dict = None):
        if not data and not article_vendu:
            raise ValueError('data or article_vendu must be set')

        if article_vendu:
            # On va chercher la carte du responsable
            responsable: Membre = article_vendu.responsable
            primary_card_firstTagId = responsable.CarteCashless_Membre.first().tag_id

            # On va chercher l'uuid de l'asset
            article = article_vendu.article
            if article.subscription_fedow_asset:
                asset_uuid = article.subscription_fedow_asset.pk
            else:
                asset_uuid = MoyenPaiement.objects.get(categorie=MoyenPaiement.BADGE).pk

            data = {
                'first_tag_id': article_vendu.carte.tag_id,
                'primary_card_firstTagId': primary_card_firstTagId,
                'asset': f"{asset_uuid}",
                'pos_uuid': f"{article_vendu.pos.id}",
                'pos_name': f"{article_vendu.pos.name}",
            }

        try :
            request_badgeuse = _post(self.config, 'card/badge', data)
            if request_badgeuse.status_code == 201:

                # La badgeuse fedow a créé un transaction sur l'asset. On le valide.
                serialized_transaction = TransactionValidator(data=request_badgeuse.json())
                if serialized_transaction.is_valid():
                    validated_data = serialized_transaction.validated_data

                    # On met à jours l'article vendu avec le hash de la transaction
                    if article_vendu:
                        ArticleVendu.objects.filter(pk=article_vendu.pk).update(
                            hash_fedow=validated_data['hash'],
                            sync_fedow=True
                        )

                    return validated_data
                logger.error(serialized_transaction.errors)
                return serialized_transaction.errors
            raise Exception(f"cards create error {request_badgeuse.status_code} {request_badgeuse.json()}")
        except Exception as e:
            logger.error(e)
            raise Exception(f"request_badgeuse : {e}")

    def set_primary(self, card):
        data = {'first_tag_id': card.tag_id}
        request_create_cards_list = _post(self.config, 'card/set_primary', data)
        return request_create_cards_list.status_code

    def create(self, cards: list):
        print("batch create NFCCards")
        # Création d'une carte.
        # Le wallet est forcément celui du lieu.
        serializer = CardSerializer(cards, many=True)
        request_create_cards_list = _post(self.config, 'card', serializer.data)
        if request_create_cards_list.status_code == 201:
            return request_create_cards_list
        raise Exception(f"cards create error {request_create_cards_list.status_code}")

    def retrieve(self, user_card_firstTagId: str = None):
        request_fedow = _get(self.config, ['card', f"{user_card_firstTagId.upper()}"])

        if request_fedow.status_code == 200:
            # logger.info(f"NFCCard retrieve. Réponse FEDOW :")
            # logger.info(f"{request_fedow.json()}")

            serialized_card = CardValidator(data=request_fedow.json())

            if serialized_card.is_valid():
                cache.set(f"serialized_card_{user_card_firstTagId}", serialized_card.validated_data, 60)
                return serialized_card.validated_data

            logger.error(f"NFCCard retrieve. ERROR :  :")
            logger.error(serialized_card.errors)
            raise ValueError(serialized_card.errors)

        elif request_fedow.status_code == 403:
            logger.error("bad fedow auth")
            raise PermissionError("Fedow auth error")

        elif request_fedow.status_code == 502:
            logger.error("bad gateway, nginx up but fedow down ?")
            raise ConnectionError("Fedow is down ?")

        elif request_fedow.status_code == 404:
            logger.error(request_fedow.content)
            raise FileNotFoundError(f"Carte inconnue")

        else:
            logger.error(request_fedow)
            raise Exception(f"{request_fedow.status_code} {request_fedow.content}")

    def cached_retrieve(self, user_card_firstTagId: str = None):
        serialized_and_validated_card = cache.get(f"serialized_card_{user_card_firstTagId}")
        if serialized_and_validated_card:
            logger.info(f"cache GET for card {user_card_firstTagId}")
        else:
            serialized_and_validated_card = self.retrieve(user_card_firstTagId)
            logger.info(f"cache SET for card {user_card_firstTagId}")
            cache.set(f"serialized_card_{user_card_firstTagId}", serialized_and_validated_card, 10)

        return serialized_and_validated_card

    def refund(self,
               user_card_firstTagId: str = None,
               primary_card_fisrtTagId: str = None,
               void: bool = False, ):

        refund_data = {
            "user_card_firstTagId": user_card_firstTagId.upper(),
            "primary_card_fisrtTagId": primary_card_fisrtTagId.upper(),
            "action": TransactionValidator.VOID if void else TransactionValidator.REFUND,
        }
        request_refund = _post(self.config, f'card/refund', refund_data)

        if request_refund.status_code == 205:
            refund_data = request_refund.json()

            serialized_transactions = TransactionValidator(
                data=refund_data.get('serialized_transactions'),
                many=True)
            if not serialized_transactions.is_valid():
                print(serialized_transactions.errors)
                raise Exception(f"cards refund error : {serialized_transactions.errors}")

            if void:
                # Si void, on a besoin de supprimer le wallet sinon le Serialiser de carte aura deux valeurs différentes.
                # Le mettre a None va permettre de le mettre à jour avec le nouveau wallet ephemere
                # A faire après le is_valid du serialized_transactions car un nouveau wallet est recréé
                carte = CarteCashless.objects.get(tag_id=user_card_firstTagId)
                carte.wallet = None
                carte.membre = None
                carte.assets.all().delete()
                carte.cartes_maitresses.all().delete()
                carte.save()
                cache.delete(f"serialized_card_{user_card_firstTagId}")
                logger.debug(f"cache DELETED for card {user_card_firstTagId}")
                logger.info(f"void card number {carte.number} tag {user_card_firstTagId} - cache deleted")

            before_refund_serialized_wallet = WalletValidator(
                data=refund_data.get('before_refund_serialized_wallet'))
            if not before_refund_serialized_wallet.is_valid():
                print(before_refund_serialized_wallet.errors)
                raise Exception(f"cards refund error : {before_refund_serialized_wallet.errors}")

            # On mets le is_valid avant le void car les serializers créent les wallets s'ils n'existent pas.
            serialized_card = CardValidator(data=refund_data.get('serialized_card'))
            if not serialized_card.is_valid():
                print(serialized_card.errors)
                raise Exception(f"cards refund error : {serialized_card.errors}")

            return {
                "serialized_card": serialized_card.validated_data,
                "before_refund_serialized_wallet": before_refund_serialized_wallet.validated_data,
                "serialized_transactions": serialized_transactions.validated_data,
            }

    def void(self,
             user_card_firstTagId: str = None,
             primary_card_fisrtTagId: str = None):
        return self.refund(user_card_firstTagId, primary_card_fisrtTagId, void=True)

    def link_user(self, email: str = None, card: CarteCashless = None):
        create_wallet_with_tag_id = {
            "email": email,
            "card_first_tag_id": card.tag_id,
        }
        response_link = _post(self.config, 'wallet', create_wallet_with_tag_id)
        if response_link.status_code == 201:
            wallet, created = WalletDb.objects.get_or_create(uuid=UUID(response_link.json()))
            card.wallet = wallet
            card.save()
            return card.wallet

        logger.error(response_link.json())
        raise Exception(response_link.json())

    def get_checkout(self, email: str = None, tag_id: str = None):
        data = {
            "email": email,
            "card_first_tag_id": tag_id,
        }
        response_link = _post(self.config, 'card/get_checkout', data)
        if response_link.status_code == 202:
            return response_link.json()

        logger.error(response_link.json())
        raise Exception(response_link.json())


class Transaction():
    def __init__(self, config: Configuration or None = None):
        self.config: Configuration = config
        if config is None:
            self.config = Configuration.get_solo()

    def get_from_hash(self, hash_fedow: str = None):
        response_hash = _get(self.config, [f'transaction/{hash_fedow}'])
        if response_hash.status_code == 200:
            serialized_transaction = TransactionValidator(data=response_hash.json())
            if serialized_transaction.is_valid():
                validated_data = serialized_transaction.validated_data
                return validated_data
            logger.error(serialized_transaction.errors)
            return serialized_transaction.errors

        else:
            logger.error(response_hash.json())
            return response_hash.status_code

    def refill_wallet(self,
                      amount: int = None,
                      asset: uuid4 = None,
                      wallet: uuid4 = None,
                      user_card_firstTagId: str = None,
                      primary_card_fisrtTagId: str = None, ):

        # Transaction de recharge de wallet ( cashless )
        # only possible from a place and with the origin asset
        transaction_refill = {
            "amount": amount,
            "sender": f"{self.config.fedow_place_wallet_uuid}",
            "receiver": f"{UUID(wallet)}",
            "asset": f"{UUID(asset)}",
            "user_card_firstTagId": f"{user_card_firstTagId}",
            "primary_card_fisrtTagId": f"{primary_card_fisrtTagId}",
        }

        response_refill = _post(self.config, 'transaction', transaction_refill)
        if response_refill.status_code == 201:
            serialized_transaction = TransactionValidator(data=response_refill.json())
            if serialized_transaction.is_valid():
                validated_data = serialized_transaction.validated_data
                logger.debug(f"cache SET for card {user_card_firstTagId}")
                cache.set(f"serialized_card_{user_card_firstTagId}", validated_data['card'], 10)
                return validated_data

            logger.error(serialized_transaction.errors)
            return serialized_transaction.errors

        else:
            logger.error(response_refill.json())
            return response_refill.status_code

    def to_place(self,
                 amount: int = None,
                 asset: uuid4 = None,
                 wallet: uuid4 = None,
                 user_card_firstTagId: str = None,
                 primary_card_fisrtTagId: str = None,
                 comment: str = None,
                 metadata: json = None,
                 ):
        # Transaction depuis une carte cashless vers un lieu

        transaction_w2w = {
            "amount": amount,
            "sender": f"{UUID(wallet)}",
            "receiver": f"{self.config.fedow_place_wallet_uuid}",
            "asset": f"{UUID(asset)}",
            "comment": comment,
            "metadata": metadata,
            "user_card_firstTagId": f"{user_card_firstTagId}",
            "primary_card_fisrtTagId": f"{primary_card_fisrtTagId}",
        }

        response_w2w = _post(self.config, 'transaction', transaction_w2w)
        if response_w2w.status_code == 201:
            serialized_transaction = TransactionValidator(data=response_w2w.json())
            if serialized_transaction.is_valid():
                return serialized_transaction.validated_data

            logger.error(serialized_transaction.errors)
            return serialized_transaction.errors

        else:
            logger.error(response_w2w.json())
            return response_w2w.json()


class PlaceFedow():
    def __init__(self, config: Configuration or None = None):
        self.config: Configuration = config
        if config is None:
            self.config = Configuration.get_solo()

    def get_accepted_assets(self):
        accepted_assets = _get(self.config, ['asset', ])
        if accepted_assets.status_code == 200:
            serialized_assets = AssetValidator(data=accepted_assets.json(), many=True)
            if serialized_assets.is_valid():
                return serialized_assets.validated_data
            logger.error(serialized_assets.errors)
            raise Exception(f"{serialized_assets.errors}")
        logger.error(accepted_assets)
        raise Exception(f"{accepted_assets.status_code}")



class AssetFedow():
    def __init__(self, config: Configuration or None = None):
        self.config: Configuration = config
        if config is None:
            self.config = Configuration.get_solo()

    def list(self):
        response_asset = _get(self.config, ['asset', ])
        if response_asset.status_code == 200:
            serialized_assets = AssetValidator(data=response_asset.json(), many=True)
            if serialized_assets.is_valid():
                return serialized_assets.validated_data
            logger.error(serialized_assets.errors)
            raise Exception(f"{serialized_assets.errors}")

    def retrieve(self, uuid: uuid4 = None):
        response_asset = _get(self.config, ['asset', f"{UUID(uuid)}"])
        if response_asset.status_code == 200:
            serialized_assets = AssetValidator(data=response_asset.json(), many=False)
            if serialized_assets.is_valid():
                return serialized_assets.validated_data
            logger.error(serialized_assets.errors)
            raise Exception(f"{serialized_assets.errors}")
        logger.error(response_asset)
        raise Exception(f"{response_asset.status_code}")

    def get_or_create_asset(self, mp: MoyenPaiement):
        try :
            asset_serialized = self.retrieve(f"{mp.pk}")
            return asset_serialized, False
        except Exception as e:
            asset = {
                    "uuid": f"{mp.pk}",
                    "name": f"{mp.name} {self.config.structure}",
                    "currency_code": f"{mp.name[:2]}{mp.categorie[1:]}".upper(),
                    "category": f"{mp.fedow_category()}",
                    "created_at": ArticleVendu.objects.filter(moyen_paiement=mp).order_by(
                        'date_time').first().date_time.isoformat() if ArticleVendu.objects.filter(
                        moyen_paiement=mp) else timezone.now().isoformat()
                }

            response_asset = _post(self.config, 'asset', asset)
            if response_asset.status_code == 201:
                serialized_assets = AssetValidator(data=response_asset.json(), many=False)
                if serialized_assets.is_valid():
                    return serialized_assets.validated_data, True
                logger.error(serialized_assets.errors)
                raise Exception(f"{serialized_assets.errors}")
            logger.error(response_asset)
            raise Exception(f"{response_asset.status_code}")

class WalletFedow():
    def __init__(self, config: Configuration or None = None):
        self.config: Configuration = config
        if config is None:
            self.config = Configuration.get_solo()

    # def get_or_create_wallet_from_email(self, email: str = None, save=True):
    #     response_link = _post(self.config, 'wallet', {"email": email})
    #     if response_link.status_code == 201:
    #         wallet, created = Wallet.objects.get_or_create(uuid=UUID(response_link.json()))
    #         return wallet, created
    #
    #     raise Exception(f"Wallet FedowAPI create_from_email response : {response_link.status_code}")


    def retrieve(self, wallet: uuid4 = None):
        response_wallet = _get(self.config, ['wallet', f"{UUID(wallet)}"])
        if response_wallet.status_code == 200:
            serialized_wallet = WalletValidator(data=response_wallet.json())
            if serialized_wallet.is_valid():
                return serialized_wallet.validated_data

        raise Exception(f"{response_wallet.status_code}")



class FedowAPI():

    def __init__(self, wallet_uuid=None, config=None):
        self.config = config
        if config is None:
            self.config = Configuration.get_solo()
        # assert self.config.fedow_domain
        # assert self.config.fedow_place_admin_apikey

        # Sub Class as method
        self.subscription = Subscription(self.config)
        # self.asset = Asset(self.config)
        self.NFCcard = NFCCard(self.config)
        self.wallet = WalletFedow(self.config)
        self.asset = AssetFedow(self.config)
        self.transaction = Transaction(self.config)
        self.place = PlaceFedow(self.config)

        super().__init__()

    def is_active(self):
        return self.config.stripe_connect_valid

    def send_assets_from_cashless(self):
        # Envoie les moyens de paiements cashless, badge et adhésion déja existant à Fedow

        assets_to_send = []

        # Sera utilisé que pour les instances CASHLESS en cours
        asset = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        assets_to_send.append({
            "uuid": str(asset.pk),
            "name": asset.name,
            "currency_code": f"{asset.name[:2]}{asset.categorie[1:]}".upper(),
            "category": "TLF",
            "created_at": ArticleVendu.objects.filter(moyen_paiement=asset).order_by(
                'date_time').first().date_time.isoformat() if ArticleVendu.objects.filter(
                moyen_paiement=asset) else timezone.now().isoformat()
        })

        # Les cadeaux
        asset_g = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        assets_to_send.append({
            "uuid": str(asset_g.pk),
            "name": asset_g.name,
            "currency_code": f"{asset_g.name[:2]}{asset_g.categorie[1:]}".upper(),
            "category": "TNF",
            "created_at": ArticleVendu.objects.filter(moyen_paiement=asset_g).order_by(
                'date_time').first().date_time.isoformat() if ArticleVendu.objects.filter(
                moyen_paiement=asset_g) else timezone.now().isoformat()
        })

        # On ajoute l'adhésion associative
        uuid_adhesion = f"{uuid4()}"
        if self.config.methode_adhesion:
            uuid_adhesion = f"{self.config.methode_adhesion.pk}"

        assets_to_send.append({
            "uuid": uuid_adhesion,
            "name": f"Adhésion {self.config.structure}",
            "currency_code": f"M{self.config.structure[:2].upper()}",
            "category": "SUB",
            "created_at": Membre.objects.all().order_by(
                'date_ajout').first().date_ajout.isoformat() if Membre.objects.count() > 0 else timezone.now().isoformat()
        })

        # La Badgeuse si elle existe
        try:
            asset_b = MoyenPaiement.objects.get(categorie=MoyenPaiement.BADGE)
            assets_to_send.append({
                "uuid": str(asset_b.pk),
                "name": f"Badgeuse {self.config.structure}",
                "currency_code": f"{asset_b.name[:2]}{asset_b.categorie[1:]}".upper(),
                "category": "BDG",
                "created_at": ArticleVendu.objects.filter(moyen_paiement=asset_b).order_by(
                    'date_time').first().date_time.isoformat() if ArticleVendu.objects.filter(
                    moyen_paiement=asset_b) else timezone.now().isoformat()
            })

        except MoyenPaiement.DoesNotExist:
            pass
        except Exception as e:
            print(e)
            raise e

        responses = []
        for message in assets_to_send:
            request_fedow = _post(self.config, 'asset', message)
            if request_fedow.status_code != 201:
                raise Exception(f"Erreur lors de l'envoi des assets : {request_fedow.content} - POUR : {message}")
            responses.append(request_fedow)

        return responses

    def card_wallet_to_laboutik(self, cardserialized: dict = None):
        data = {'total_monnaie': dround_fromcents(0)}
        wallet = cardserialized['wallet']
        if wallet:
            data['cotisation_membre_a_jour'] = "Pas d'adhésion"
            data['cotisation_membre_a_jour_booleen'] = False
            tokens_serialized = []
            for token in wallet.get('tokens'):
                # On affiche les adhésions à part
                if token.get('asset_category') != 'SUB':
                    qty = dround_fromcents(token.get('value'))
                    data['total_monnaie'] += qty
                    tokens_serialized.append({'monnaie': token.get('asset'),
                                              'monnaie_name': token.get('asset_name'),
                                              'qty': f"{qty}"})
                else:
                    if token.get('is_sub_valid'):
                        data['cotisation_membre_a_jour'] = f"{token.get('asset_name')} OK"
                        data['cotisation_membre_a_jour_booleen'] = token.get('is_sub_valid')

            data['assets'] = tokens_serialized
            data['membre_name'] = f"***"
            data['first_tag_id'] = f"{cardserialized['first_tag_id']}"
            data['origin'] = cardserialized['origin']

            return data

        raise Exception("Wallet not found")
