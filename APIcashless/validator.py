from collections import OrderedDict
from random import choices

from IPython.utils.coloransi import value
from django.utils import timezone
from rest_framework import serializers
from werkzeug.routing import ValidationError

from APIcashless.models import CarteCashless, Configuration, Assets, Membre, MoyenPaiement, Articles, Categorie, Wallet, \
    ArticleVendu
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework.generics import get_object_or_404
import logging

from fedow_connect.fedow_api import FedowAPI

logger = logging.getLogger(__name__)


# pour l'api recharge de carte
class RechargeCardValidator(serializers.Serializer):
    card_uuid = serializers.UUIDField()
    qty = serializers.IntegerField()
    uuid_commande = serializers.UUIDField()
    email = serializers.EmailField(required=False)

    def validate_card_uuid(self, value):
        self.card = get_object_or_404(CarteCashless, uuid_qrcode=value)
        return self.card.uuid_qrcode

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['card'] = self.card
        return representation


# POUR l'api Check membre
class EmailMembreValidator(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email').lower()
        membre = Membre.objects.filter(email=email).first()
        logger.info(membre)
        if not membre:
            raise serializers.ValidationError("email inconnu")
        else:
            self.membre = membre
        return super().validate(attrs)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['membre'] = self.membre
        return representation


### FROM LESPASS

class PriceFromLespassValidator(serializers.Serializer):
    adhesion_obligatoire = serializers.BooleanField(allow_null=True)
    name = serializers.CharField(max_length=250)
    short_description = serializers.CharField(max_length=250, allow_null=True, allow_blank=True)
    long_description = serializers.CharField(max_length=2500, allow_null=True, allow_blank=True)
    max_per_user = serializers.IntegerField()
    prix = serializers.DecimalField(max_digits=8, decimal_places=2)
    free_price = serializers.BooleanField()
    product = serializers.UUIDField()
    recurring_payment = serializers.BooleanField()
    stock = serializers.BooleanField(allow_null=True)
    uuid = serializers.UUIDField()

    NA, YEAR, MONTH, DAY, HOUR, CIVIL = 'N', 'Y', 'M', 'D', 'H', 'C'
    SUB_CHOICES = [
        (NA, _('Non applicable')),
        (YEAR, _("365 Jours")),
        (MONTH, _('30 Jours')),
        (DAY, _('1 Jour')),
        (HOUR, _('1 Heure')),
        (CIVIL, _('Civile')),
    ]
    subscription_type = serializers.CharField(max_length=1)

    NA, DIX, VINGT, HUITCINQ, DEUXDEUX = 'NA', 'DX', 'VG', 'HC', 'DD'
    TVA_CHOICES = [
        (NA, _('Non applicable')),
        (DIX, _("10 %")),
        (VINGT, _('20 %')),
        (HUITCINQ, _('8.5 %')),
        (DEUXDEUX, _('2.2 %')),
    ]
    vat = serializers.CharField(max_length=2)


class PriceSoldFromLespassValidator(serializers.Serializer):
    price = PriceFromLespassValidator()
    prix = serializers.DecimalField(max_digits=8, decimal_places=2)


class SaleFromLespassValidator(serializers.Serializer):
    # paiement_stripe_uuid = serializers.UUIDField()
    payment_method = serializers.ChoiceField(choices=MoyenPaiement.CATEGORIES)
    amount = serializers.IntegerField()
    uuid = serializers.UUIDField()
    datetime = serializers.DateTimeField()
    pricesold = PriceSoldFromLespassValidator()
    qty = serializers.DecimalField(max_digits=8, decimal_places=2)
    vat = serializers.DecimalField(max_digits=4, decimal_places=2)
    # user_uuid_wallet = serializers.UUIDField()

    def validate_uuid(self, value):
        # uuid_paiement = uuid LigneArticle sur Lespass
        if ArticleVendu.objects.filter(uuid=value).exists():
            raise serializers.ValidationError("Sale already recorded : uuid")
        return value

    # def validate_paiement_stripe_uuid(self, value):
    #     # uuid_paiement = uuid LigneArticle sur Lespass
    #     if ArticleVendu.objects.filter(uuid_paiement=value).exists():
    #         raise serializers.ValidationError("Sale already recorded : uuid_paiement")
    #     return value

    def validate_user_uuid_wallet(self, value):
        try :
            wallet = Wallet.objects.get(pk=value)
        except Wallet.DoesNotExist:
            fedowAPI = FedowAPI()
            fedowAPI.wallet.retrieve(f"{value}")
            wallet = Wallet.objects.get(pk=value)

        return wallet


class ProductFromLespassValidator(serializers.Serializer):
    NONE, BILLET, PACK, RECHARGE_CASHLESS = 'N', 'B', 'P', 'R'
    RECHARGE_FEDERATED, VETEMENT, MERCH, ADHESION, BADGE = 'S', 'T', 'M', 'A', 'G'
    DON, FREERES, NEED_VALIDATION = 'D', 'F', 'V'

    CATEGORIE_ARTICLE_CHOICES = [
        (NONE, _('Selectionnez une catégorie')),
        (BILLET, _('Billet payant')),
        (PACK, _("Pack d'objets")),
        (RECHARGE_CASHLESS, _('Recharge cashless')),
        (RECHARGE_FEDERATED, _('Recharge suspendue')),
        (VETEMENT, _('Vetement')),
        (MERCH, _('Merchandasing')),
        (ADHESION, _('Abonnement et/ou adhésion associative')),
        (BADGE, _('Badgeuse')),
        (DON, _('Don')),
        (FREERES, _('Reservation gratuite')),
        (NEED_VALIDATION, _('Nécessite une validation manuelle'))
    ]

    categorie_article = serializers.ChoiceField(choices=CATEGORIE_ARTICLE_CHOICES)
    prices = PriceFromLespassValidator(many=True)
    img = serializers.URLField(allow_null=True)
    legal_link = serializers.URLField(allow_null=True)
    long_description = serializers.CharField(max_length=2500, allow_null=True, allow_blank=True)
    short_description = serializers.CharField(max_length=250, allow_null=True, allow_blank=True)
    name = serializers.CharField(max_length=500)
    nominative = serializers.BooleanField(allow_null=True)
    option_generale_checkbox = serializers.ListField()
    option_generale_radio = serializers.ListField()
    publish = serializers.BooleanField(allow_null=True)
    tag = serializers.ListField()
    terms_and_conditions_document = serializers.URLField(allow_null=True)
    uuid = serializers.UUIDField()

    def validate(self, attrs):
        product = attrs
        categorie = product['categorie_article']
        prices = product['prices']
        dict_cat_name = {
            'G': (_('Badge'), Articles.BADGEUSE),
            'A': (_('Adhésions'), Articles.ADHESIONS),
            'B': (_('Billet'), Articles.BILLET),
        }
        asset_fedow = MoyenPaiement.objects.get(pk=product['uuid']) if categorie in ['G','A'] else None

        # Si c'est un billet, une adhésion ou un article badge :
        # Création de la catégorie d'article
        if categorie in dict_cat_name:
            cat, created = Categorie.objects.get_or_create(name=dict_cat_name[categorie][0])
            logger.info(f"Categorie {cat.name} - created {created}")
            for price in prices :
                article, created = Articles.objects.get_or_create(id=price['uuid'])
                # créé ou pas, on met à jour l'article avec les infos de la billetterie
                article.name=f"{product['name']} {price['name']}"
                article.methode_choices=dict_cat_name[categorie][1]
                article.prix=price['prix'] if not price['free_price'] else 1
                article.categorie=cat
                article.subscription_type=price['subscription_type']
                article.fedow_asset=asset_fedow
                article.save()

        return attrs

    ### END FROM LESPASS

    ### START OLD BILLETTERIE


class BilletterieValidator(serializers.Serializer):
    uuid = serializers.UUIDField()
    uuid_commande = serializers.UUIDField(required=False)
    recharge_qty = serializers.FloatField(required=False)
    tarif_adhesion = serializers.FloatField(required=False)
    carte = None

    def validate_uuid(self, value):
        try:
            self.carte = CarteCashless.objects.get(uuid_qrcode=value)
            return value
        except CarteCashless.DoesNotExist:
            raise serializers.ValidationError("uuid inconnu")
        except Exception as e:
            raise serializers.ValidationError(e)


# pour l'API adhesion
class MembreshipValidator(serializers.Serializer):
    email = serializers.EmailField()

    first_name = serializers.CharField(max_length=200, required=False)
    last_name = serializers.CharField(max_length=200, required=False)

    phone = serializers.CharField(max_length=20, required=False)
    postal_code = serializers.IntegerField(required=False)
    birth_date = serializers.DateField(required=False)
    newsletter = serializers.BooleanField(required=False)

    uuid_carte = serializers.UUIDField(required=False)

    adhesion = serializers.DecimalField(max_digits=10, decimal_places=2)
    card = None
    uuid_commande = serializers.UUIDField()

    def validate_email(self, value):
        membre, created = Membre.objects.get_or_create(email=value.lower())
        if created:
            membre.date_inscription = timezone.now().date()
            membre.adhesion_origine = Membre.BILLETTERIE
            membre.save()

        self.fiche_membre: Membre = membre
        return self.fiche_membre.email

    def validate_uuid_carte(self, value):
        self.card = get_object_or_404(CarteCashless, uuid_qrcode=value)
        if self.card.membre != self.fiche_membre:
            raise serializers.ValidationError(_(f"Cette carte est au nom d'une autre personne"))
        return self.card.uuid_qrcode

    def validate(self, attrs):
        if not self.fiche_membre.prenom:
            if not self.initial_data.get('first_name'):
                raise serializers.ValidationError(_(f'first_name est obligatoire'))
            self.fiche_membre.prenom = self.initial_data.get('first_name')
        if not self.fiche_membre.name:
            if not self.initial_data.get('last_name'):
                raise serializers.ValidationError(_(f'last_name est obligatoire'))
            self.fiche_membre.name = self.initial_data.get('last_name')
        if not self.fiche_membre.tel:
            if not self.initial_data.get('phone'):
                raise serializers.ValidationError(_(f'phone est obligatoire'))
            self.fiche_membre.tel = self.initial_data.get('phone')

        # not requiered
        if not self.fiche_membre.code_postal:
            self.fiche_membre.code_postal = self.initial_data.get('postal_code')
        if not self.fiche_membre.date_naissance:
            self.fiche_membre.date_naissance = self.initial_data.get('birth_date')
        if not self.fiche_membre.demarchage:
            self.fiche_membre.demarchage = self.initial_data.get('newsletter')

        print(self.fiche_membre.prenom)
        self.fiche_membre.save()

        return super().validate(attrs)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['membre'] = self.fiche_membre
        representation['card'] = self.card

        return representation


# pour le qr code adhésion
class AdhesionValidator(serializers.Serializer):
    email = serializers.EmailField()
    prenom = serializers.CharField(max_length=50, required=False)
    name = serializers.CharField(max_length=50, required=False)
    tel = serializers.CharField(max_length=50, required=False)
    uuid_carte = serializers.UUIDField(required=True)
    carte = None

    def validate_uuid_carte(self, value):
        try:
            self.carte = CarteCashless.objects.get(uuid_qrcode=value)
            return value
        except CarteCashless.DoesNotExist:
            raise serializers.ValidationError("uuid inconnu")
        except Exception as e:
            raise serializers.ValidationError(e)


class UpdateFedWalletValidator(serializers.Serializer):
    card_uuid = serializers.UUIDField()
    uuid_sync_log = serializers.UUIDField()
    # email = serializers.EmailField()
    old_qty = serializers.DecimalField(max_digits=10, decimal_places=2)
    new_qty = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_card_uuid(self, value):
        try:
            self.carte = CarteCashless.objects.get(uuid_qrcode=value)
            return value
        except CarteCashless.DoesNotExist:
            raise serializers.ValidationError("uuid inconnu")
        except Exception as e:
            raise serializers.ValidationError(e)

    # def validate_email(self, value):
    #     try:
    #         self.membre = Membre.objects.get(email=value)
    #         return value
    #     except Membre.DoesNotExist:
    #         raise serializers.ValidationError("email inconnu")
    #     except Exception as e:
    #         raise serializers.ValidationError(e)

    def validate(self, attrs):
        logger.info(f"UpdateFedWalletValidator validate {attrs}")
        return super().validate(attrs)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['card'] = self.carte
        return representation


class DataOcecoValidator(serializers.Serializer):
    '''
    return number -> Assets instance
    qqt -> Float
    '''

    number_printed = serializers.CharField(min_length=5, max_length=8)
    qty_oceco = serializers.FloatField()

    def validate_number_printed(self, value):
        # On vérifie avec le validator que la qty soit bien un chiffre, et que le numéro existe bien en carte
        # Le validator renvoie l'asset cadeau correspondant a la carte directement.
        try:
            carte = CarteCashless.objects.get(number=value.upper())
            mp_local_gift = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
            asset_cadeau, created = carte.assets.get_or_create(monnaie=mp_local_gift)

        except CarteCashless.DoesNotExist:
            raise serializers.ValidationError("Carte inconnue.")
        except Exception as e:
            raise serializers.ValidationError(e)

        else:
            return asset_cadeau

    def validate_qty_oceco(self, value):
        if value > 0:
            return value
        else:
            raise serializers.ValidationError("Valeur positive siouplé !")
