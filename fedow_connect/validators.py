from decimal import Decimal

from django.core.cache import cache
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from APIcashless.models import Origin, MoyenPaiement, CarteCashless, Assets, Place, Wallet
import logging

logger = logging.getLogger(__name__)


def dround(value):
    return Decimal(value).quantize(Decimal('1.00'))


class PlaceValidator(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    wallet = serializers.UUIDField()
    stripe_connect_valid = serializers.BooleanField()
    dokos_id = serializers.CharField(max_length=50, allow_null=True, required=False)

    def validate(self, attrs):
        wallet, created = Wallet.objects.get_or_create(uuid=attrs['wallet'])
        try:
            self.place = Place.objects.get(uuid=attrs['uuid'])
        except Place.DoesNotExist:
            self.place = Place.objects.create(
                uuid=attrs['uuid'],
                name=attrs['name'],
                dokos_id=attrs.get('dokos_id'),
                wallet=wallet,
            )
        except Exception as e:
            raise serializers.ValidationError(f"Erreur lors de la récupération du lieu : {e}")

        self.place.stripe_connect_valid = attrs['stripe_connect_valid']
        return attrs


class OriginValidator(serializers.Serializer):
    place = PlaceValidator(many=False, required=True)
    generation = serializers.IntegerField()
    img = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        place = self.fields['place'].place
        self.origin, created = Origin.objects.get_or_create(place=place, generation=attrs['generation'])
        return attrs


### SERIALIZER DE DONNEE RECEPTIONEES DEPUIS FEDOW ###
class AssetValidator(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    currency_code = serializers.CharField(max_length=3)
    place_origin = PlaceValidator(many=False, required=False, allow_null=True)

    STRIPE_FED_FIAT = 'FED'
    TOKEN_LOCAL_FIAT = 'TLF'
    TOKEN_LOCAL_NOT_FIAT = 'TNF'
    TIME = 'TIM'
    BADGE = 'BDG'
    SUBSCRIPTION = 'SUB'
    FIDELITY = 'FID'

    CATEGORIES = [
        (TOKEN_LOCAL_FIAT, _('Token équivalent euro')),
        (TOKEN_LOCAL_NOT_FIAT, _('Non fiduciaire')),
        (STRIPE_FED_FIAT, _('Stripe Connect')),
        (TIME, _("Monnaie temps, decompte d'utilisation")),
        (BADGE, _("Badgeuse/Pointeuse")),
        (SUBSCRIPTION, _('Adhésion ou abonnement')),
        (FIDELITY, _('Points de fidélités')),
    ]
    category = serializers.ChoiceField(choices=CATEGORIES)

    created_at = serializers.DateTimeField()
    last_update = serializers.DateTimeField()
    is_stripe_primary = serializers.BooleanField()

    total_token_value = serializers.IntegerField(required=False, allow_null=True)
    total_in_place = serializers.IntegerField(required=False, allow_null=True)
    total_in_wallet_not_place = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        place = self.fields['place_origin'].place if attrs.get('place_origin') else None
        try:
            moyen_paiement = MoyenPaiement.objects.get(pk=attrs['uuid'])
            if not moyen_paiement.is_federated:
                moyen_paiement.is_federated = True
                moyen_paiement.save()
            if not moyen_paiement.place_origin:
                moyen_paiement.place_origin = place
                moyen_paiement.save()

        except MoyenPaiement.DoesNotExist:
            # L'objet origin a été créé dans le serializer OriginValidator

            cat = MoyenPaiement.fedow_asset_category_to_moyen_paiement_category(attrs['category'])
            moyen_paiement = MoyenPaiement.objects.create(
                pk=attrs['uuid'],
                name=attrs['name'],
                categorie=cat,
                place_origin=place,
                blockchain=True,
                is_federated=True,
                cadeau=True if cat == MoyenPaiement.EXTERIEUR_GIFT else False,
            )

            logger.info(f"New asset created : {moyen_paiement}")
            # Le signal MoyenPaiement va s'enclencher si c'est une badgeuse
            # ou une adhésion pour aller chercher les articles correspondant dans Lespass
        except Exception as e:
            raise serializers.ValidationError(f"Erreur lors de la récupération du moyen de paiement : {e}")

        self.moyen_paiement = moyen_paiement
        return attrs


class TokenValidator(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    value = serializers.IntegerField()
    asset = AssetValidator(many=False)

    asset_uuid = serializers.UUIDField()
    asset_name = serializers.CharField()
    asset_category = serializers.ChoiceField(choices=AssetValidator.CATEGORIES)

    is_primary_stripe_token = serializers.BooleanField()
    last_transaction_datetime = serializers.DateTimeField(allow_null=True, required=False)

    @staticmethod
    def update_or_create(serilized_tokens, card):
        tokens_cashless = []
        #TODO: Virer les précédents tokens car fedow est sensé faire foi partout ?
        # Les tokens locaux sont créé avant d'être envoyé sur Fedow.
        # Du coup, le pk des tokens fedow et asset laboutik ne correspondent pas.
        # Revoir la methode Webview.view.Commande.asset_principal()
        for token in serilized_tokens:
            try:
                token_cashless = Assets.objects.get(monnaie__pk=token['asset']['uuid'], carte=card)
            except Assets.DoesNotExist:
                token_cashless = Assets.objects.create(
                    pk=token['uuid'],
                    monnaie_id=token['asset']['uuid'],
                    carte=card,
                )
            except Exception as e:
                raise serializers.ValidationError(f"Erreur lors de la mise à jour des assets de la carte : {e}")


            # Que cela soit du token fiat ou non fiat ou d'adhésion, on mets à jour la valeur. Fedow a toujours raison.
            token_cashless.qty = (token['value'] / 100)
            logger.info(f"FEDOW ASSET {token_cashless.monnaie.name} TO asset.qty {token_cashless.qty}")
            tokens_cashless.append(token_cashless)
            token_cashless.save()

        # Si il existe une autre carte avec le même wallet dans le serveur,
        # on met les token à zero car cela sera compté en double par le serveur cashless.
        wallet = card.get_wallet()
        if wallet :
            other_cards = wallet.cards.exclude(id=card.id)
            if other_cards.exists():
                for card in other_cards:
                    logger.info(f"DOUBLE CARD {card.tag_id} - WITH SAME FEDOW WALLET. Set all asset to 0")
                    card.assets.update(qty=0)

        return tokens_cashless

    @staticmethod
    def get_payment_tokens(serilized_tokens):
        fiat_tokens = {
            token['asset_uuid']: dround(token['value'] / 100)
            for token in serilized_tokens
            if token['asset_category'] in [
                AssetValidator.STRIPE_FED_FIAT,
                AssetValidator.TOKEN_LOCAL_FIAT,
                AssetValidator.TOKEN_LOCAL_NOT_FIAT,
            ]
        } if len(serilized_tokens) > 0 else {}
        return fiat_tokens


class WalletValidator(serializers.Serializer):
    uuid = serializers.UUIDField()
    tokens = TokenValidator(many=True)

    def validate(self, attrs):
        self.wallet, created = Wallet.objects.get_or_create(uuid=attrs['uuid'])

        # Simplification du dictionnaire pour avoir la correspondante asset cahsless <-> valeur token fedow
        # pour le validateur de paiement cashless (boucle for asset de methode_VT )
        self.payment_tokens = TokenValidator.get_payment_tokens(attrs['tokens'])
        attrs['payment_tokens'] = self.payment_tokens
        return attrs


class CardValidator(serializers.Serializer):
    wallet = WalletValidator(many=False)
    origin = OriginValidator()
    uuid = serializers.UUIDField()
    qrcode_uuid = serializers.UUIDField()
    first_tag_id = serializers.CharField(min_length=8, max_length=8)
    number_printed = serializers.CharField()
    is_wallet_ephemere = serializers.BooleanField()

    def validate(self, attrs):
        try:
            card = CarteCashless.objects.get(id=attrs['uuid'])
            card.wallet = self.fields['wallet'].wallet
            card.origin = self.fields['origin'].origin
            card.save()
            # elif card.wallet != self.fields.get('wallet').wallet:
            #     raise serializers.ValidationError("Wallet and card mismatch")

        # Création de la carte cashless si elle n'existe pas
        except CarteCashless.DoesNotExist:
            card = CarteCashless.objects.create(
                id=attrs['uuid'],
                tag_id=attrs['first_tag_id'],
                uuid_qrcode=attrs['qrcode_uuid'],
                number=attrs['number_printed'],
                wallet=self.fields['wallet'].wallet,
                origin=self.fields['origin'].origin,
            )
        except Exception as e:
            raise serializers.ValidationError(f"Erreur lors de la récupération de la carte : {e}")

        # Mise à jour des assets de la carte :
        # tokens_cashless = Assets
        tokens_cashless = TokenValidator.update_or_create(attrs['wallet']['tokens'], card)
        return attrs


class TransactionValidator(serializers.Serializer):
    uuid = serializers.UUIDField()
    hash = serializers.CharField(min_length=64, max_length=64)

    datetime = serializers.DateTimeField()
    subscription_start_datetime = serializers.DateTimeField(required=False, allow_null=True)
    sender = serializers.UUIDField()
    receiver = serializers.UUIDField()
    asset = serializers.UUIDField()
    amount = serializers.IntegerField()
    card = CardValidator(required=False, many=False, allow_null=True)
    primary_card = serializers.UUIDField(required=False, allow_null=True)
    previous_transaction = serializers.UUIDField()

    FIRST, SALE, CREATION, REFILL, TRANSFER, SUBSCRIBE, BADGE, FUSION, REFUND, VOID = 'FST', 'SAL', 'CRE', 'REF', 'TRF', 'SUB', 'BDG', 'FUS', 'RFD', 'VID'
    TYPE_ACTION = (
        (FIRST, "Premier bloc"),
        (SALE, "Vente d'article"),
        (CREATION, 'Creation monétaire'),
        (REFILL, 'Recharge'),
        (TRANSFER, 'Transfert'),
        (SUBSCRIBE, 'Abonnement ou adhésion'),
        (BADGE, 'Badgeuse'),
        (FUSION, 'Fusion de deux wallets'),
        (REFUND, 'Remboursement'),
        (VOID, 'Dissocciation de la carte et du wallet user'),
    )
    action = serializers.ChoiceField(choices=TYPE_ACTION)

    comment = serializers.CharField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, allow_null=True)
    verify_hash = serializers.BooleanField()

    def validate(self, attrs):
        # Après une transaction, s'il y a une carte, on mets à jour le cache pour l'affichage
        if attrs.get('card'):
            logger.info(f"cache SET for card {attrs['card']['first_tag_id']}")
            cache.set(f"serialized_card_{attrs['card']['first_tag_id']}", attrs['card'], 120)
        return attrs
