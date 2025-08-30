import logging
import os
from decimal import Decimal
from typing import List

from cryptography.exceptions import InvalidSignature
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty

from APIcashless.models import Articles, Membre, PointDeVente, Configuration, CarteCashless, MoyenPaiement, Table, \
    CommandeSauvegarde, CarteMaitresse, Assets, Appareil
from fedow_connect.utils import get_public_key, verify_signature
from tibiauth.models import TibiUser

logger = logging.getLogger(__name__)
from sentry_sdk import capture_message

from fedow_connect.fedow_api import FedowAPI


def dround(value):
    return Decimal(value).quantize(Decimal('1.00'))

class NewPeriphPinValidator(serializers.Serializer):
    username = serializers.CharField(max_length=512)
    password = serializers.CharField(max_length=512, write_only=True)

    periph = serializers.ChoiceField(Appareil.PERIPH_CHOICES)
    public_pem = serializers.CharField(max_length=512)

    hostname = serializers.CharField(max_length=512)
    version = serializers.CharField(max_length=50)

    pin_code = serializers.IntegerField()
    ip_lan = serializers.IPAddressField()


    def validate_username(self, value):
        if TibiUser.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("Nom d'utilisateur déjà utilisé"))
        return value

    def validate_password(self, value):
        # On utilise le validateur de mot de passe de Django :
        validate_password(value)
        self.password = value
        return value

    def validate_public_pem(self, value):
        try:
            public_key = get_public_key(value)
            if public_key.key_size < 2048:
                raise serializers.ValidationError(_("Clé publique trop petite"))
        except Exception as e:
            raise serializers.ValidationError(_(f"Erreur get rsa key : {e}"))

        print(f"public_key is_valid")
        self.sended_public_key = public_key
        return value

    def validate_pin_code(self, value):
        try :
            self.appareil = Appareil.objects.get(pin_code=value)
        except Appareil.DoesNotExist:
            raise serializers.ValidationError(_("Code pin invalide"))
        return value

class LoginHardwareValidator(serializers.Serializer):
    username = serializers.CharField(max_length=512)
    password = serializers.CharField(max_length=512, write_only=True)
    ip_lan = serializers.IPAddressField()

    signature = serializers.CharField(max_length=512)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        signature = attrs.get('signature')

        # Utilisateur existe et mot de passe correct ?
        user: TibiUser = authenticate(username=username, password=password)
        if user is None:
            raise serializers.ValidationError(_("Utilisateur ou mot de passe incorrect."))

        try:
            user_public_key = user.get_public_key()
            verify_signature(user_public_key, password.encode('utf-8'), signature)
        except AttributeError:
            raise serializers.ValidationError(_("Clé publique non trouvée pour cet utilisateur. Relancez l'appairage."))
        except InvalidSignature:
            raise serializers.ValidationError(_("Signature non valide."))
        except Exception as e:
            raise serializers.ValidationError(f"Erreur de validation : {e}")

        self.user = user
        return attrs

class ArticleValidator(serializers.Serializer):
    pk = serializers.PrimaryKeyRelatedField(queryset=Articles.objects.all())
    qty = serializers.DecimalField(required=True, max_digits=6, decimal_places=2)
    uuid_commande = serializers.PrimaryKeyRelatedField(queryset=CommandeSauvegarde.objects.all(), required=False)


class DataAchatDepuisClientValidator(serializers.Serializer):
    uuid_commande_exterieur = serializers.UUIDField(required=False)

    pk_responsable = serializers.PrimaryKeyRelatedField(queryset=Membre.objects.all())
    pk_pdv = serializers.PrimaryKeyRelatedField(queryset=PointDeVente.objects.all())
    hostnameClient = serializers.CharField(max_length=60, required=False)

    articles = ArticleValidator(many=True)
    tag_id = serializers.CharField(max_length=8, min_length=8, required=False)
    moyen_paiement = serializers.CharField(max_length=14)

    total = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    ardoise = serializers.BooleanField(default=False, required=False)

    nouvelle_table = serializers.CharField(max_length=50, required=False)
    pk_table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), required=False)

    commentaire = serializers.CharField(max_length=400, required=False, allow_blank=True)

    complementaire = serializers.JSONField(required=False)

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.config = Configuration.get_solo()

    # On vérifie les décimales et les valeurs envoyées.
    def validate_articles(self, value):
        # Set total to quantized decimal : 0.00
        total_sended = self.initial_data.get('total')
        if total_sended:
            # On vérifie que le total envoyé ne contient pas plus de 2 décimales
            if len(str(total_sended).partition('.')[-1]) > 2:
                error_msg = f"Le total envoyé contient plus de 2 décimales /wv/paiement -> SERIALIZER DataAchatDepuisClientValidator -> validate_articles() -> total_sended : {total_sended} - self.initial_data : {self.initial_data}"
                # Pour envoyer un message a sentry :
                if os.environ.get('SENTRY_DNS'):
                    capture_message(f"{error_msg}")
                logger.error(f"{error_msg}")
            total_sended = dround(total_sended)
            self.initial_data['total'] = total_sended

        total_temp = Decimal(0)
        for art in value:
            total_temp += dround(art.get('pk').prix * art.get('qty'))

        # On vérifie que les virgules du total soit max 0.00
        if total_sended:
            # valuer absolue pour les retour consigne négatives
            if abs(total_sended) != abs(total_temp):
                error_msg = _(
                    f"ERREUR /wv/paiement -> SERIALIZER DataAchatDepuisClientValidator -> validate_articles() -> total_temp : {total_temp} - total_sended : {total_sended} - self.initial_data : {self.initial_data}")
                logger.error(f"{error_msg}")
                raise serializers.ValidationError(error_msg)

        return value

    def validate_total(self, value):
        if value:
            if value < 0:
                raise serializers.ValidationError(_("Le total ne peut pas être négatif"))
        return value

    # Première Carte
    def validate_tag_id(self, value):
        if value:
            if self.config.can_fedow():
                fedowAPI = FedowAPI()
                self.fedow_serialized_card = fedowAPI.NFCcard.retrieve(value.upper())

            # On va chercher l'objet après la requete Fedow pour l'avoir à jour des modifs (création wallet, assets, etc ...)
            self.card = CarteCashless.objects.get(tag_id=value.upper())
        return value.upper() if value else None

    # Seconde Carte si complémentaire
    def validate_complementaire(self, value):
        if value:
            manque = dround(value.get('manque'))
            if value.get('moyen_paiement') == 'nfc' and value.get('tag_id'):
                tag_id_card2 = value.get('tag_id').upper()
                if self.config.can_fedow():
                    fedowAPI = FedowAPI()
                    self.fedow_serialized_card2 = fedowAPI.NFCcard.retrieve(tag_id_card2)

                    # Premiere et seconde carte ne peuvent pas avoir le même wallet
                    if str(self.fedow_serialized_card2['wallet']['uuid']) == str(self.card.get_wallet().uuid):
                        raise serializers.ValidationError(_("Les deux cartes ont le même portefeuille."))

                # On va chercher l'objet après la requete Fedow pour l'avoir à jour des modifs (création wallet, assets, etc ...)
                self.card2 = CarteCashless.objects.get(tag_id=tag_id_card2)


            elif value.get('moyen_paiement') == 'espece':
                # On rajoute à la carte un token espece qui sera pris en compte par la boucle de paiement
                try:
                    complementaire_cash_carte = self.card.assets.get(monnaie__categorie=MoyenPaiement.CASH)
                    complementaire_cash_carte.qty = manque
                    complementaire_cash_carte.save()
                except Assets.DoesNotExist:
                    mp_espece = MoyenPaiement.objects.get(categorie=MoyenPaiement.CASH)
                    complementaire_cash_carte = self.card.assets.create(monnaie=mp_espece, qty=manque)
                except Exception as e:
                    raise serializers.ValidationError(f"validate_complementaire espece {e}")
                self.complementaire_cash_carte = complementaire_cash_carte

            elif value.get('moyen_paiement') == 'carte_bancaire':
                # On rajoute à la carte un token CB qui sera pris en compte par la boucle de paiement
                try:
                    complementaire_cb_carte = self.card.assets.get(monnaie__categorie=MoyenPaiement.CREDIT_CARD_NOFED)
                    complementaire_cb_carte.qty = manque
                    complementaire_cb_carte.save()
                except Assets.DoesNotExist:
                    mp_cb = MoyenPaiement.objects.get(categorie=MoyenPaiement.CREDIT_CARD_NOFED)
                    complementaire_cb_carte = self.card.assets.create(monnaie=mp_cb, qty=manque)
                except Exception as e:
                    raise serializers.ValidationError(f"validate_complementaire cb {e}")

                self.complementaire_cb_carte = complementaire_cb_carte

        # import ipdb; ipdb.set_trace()
        return value

    def payments_wallets(self):
        # Retourne tout les wallets de la commande si Fedow et paiment complémentaire
        # return all token from all wallet ( 2 if payement with 2 cards )
        wallets = {}
        if hasattr(self, "fedow_serialized_card"):
            wallets[self.fedow_serialized_card['wallet']['uuid']] = self.fedow_serialized_card['wallet']
        if hasattr(self, "fedow_serialized_card2"):
            wallets[self.fedow_serialized_card2['wallet']['uuid']] = self.fedow_serialized_card2['wallet']

        return wallets

    def get_payments_assets(self) -> List[Assets]:
        # Fabrication de la liste ordonnée de tout les assets utilisés pour un paiement.
        # Cela peut être pour une carte, pour deux cartes,
        # ou une carte + espèce ou CB en cas de paiement complémentaire
        payments_assets = []

        if hasattr(self, "card"):
            card: CarteCashless = self.card
            card_one_payments_assets = card.get_payment_assets()

            payments_assets += card_one_payments_assets

        if hasattr(self, "card2"):
            card_two: CarteCashless = self.card2
            card_two_payments_assets = card_two.get_payment_assets()

            payments_assets += card_two_payments_assets

        if hasattr(self, "complementaire_cash_carte"):
            payments_assets.append(self.complementaire_cash_carte)

        if hasattr(self, "complementaire_cb_carte"):
            payments_assets.append(self.complementaire_cb_carte)

        # On range par ordre de priorité
        payments_assets = MoyenPaiement.sort_assets(payments_assets)
        return payments_assets

    @staticmethod
    def total_in_payments_assets(assets: List[Assets]) -> Decimal:
        total_qty = dround(sum(asset.qty for asset in assets))
        return total_qty

    def validate_moyen_paiement(self, value):
        """
        return MoyenPaiement object database
        """
        if value == 'espece':
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.CASH)

        elif value == 'carte_bancaire':
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.CREDIT_CARD_NOFED)

        elif value == 'Web (Stripe)':
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.STRIPE_NOFED)

        elif value == "commande":
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.COMMANDE)

        elif value == "Oceco":
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.OCECO)

        elif value == "nfc":
            if not self.initial_data.get('tag_id'):
                raise serializers.ValidationError(
                    _(f"Moyen de paiement indiqué NFC mais pas de tag id dans la requete. self.initial_data : {self.initial_data}"))
            # Pas uniquement des tokens local euro, mais tout ce qui touche au cashless
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)

        elif value == "gift":
            # Mode gerant : offert
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)

        elif value == "SF":
            return MoyenPaiement.objects.get(categorie=MoyenPaiement.STRIPE_FED)

        else :
            try:
                return MoyenPaiement.objects.get(categorie=value)
            except Exception as e:
                raise serializers.ValidationError(
                    f"Le moyen de paiement n'est pas valide : {value} - self.initial_data : {self.initial_data}")

    def validate(self, attrs):
        # On vérifie, si on a des articles qui ne sont pas des ventes normales,
        # configuration = Configuration.get_solo()
        for item in attrs.get('articles'):
            article: Articles = item.get('pk')

            # Articles qui ont besoin d'un tag id obligatoire :
            if article.methode_choices not in [
                Articles.VENTE,
                Articles.RETOUR_CONSIGNE,
                Articles.CASHBACK,
                Articles.FRACTIONNE,
            ]:
                if not attrs.get('tag_id'):
                    raise serializers.ValidationError(_("Pas de tag id !"))

            # On vérifie que la mehtode des articles vendus soit dans un point de vente.
            # Pas de cashless dans vente, et pas de repas dans cashless
            # if article.methode_choices == Articles.VENTE:
            #     pdv = attrs.get('pk_pdv')
            #     if pdv.comportement != PointDeVente.VENTE:
            #         raise serializers.ValidationError(_("Comportement du point de vente invalide"))

        # On check si nouvelle table est présente.
        # Si oui, on la crée et on renseigne le pk_table

        if attrs.get('nouvelle_table'):
            nouvelle_table = attrs.get('nouvelle_table')

            try:
                carte = CarteCashless.objects.get(tag_id=nouvelle_table.upper())
                if carte.membre:
                    nouvelle_table = f"{carte.membre} {carte.number}"
            except CarteCashless.DoesNotExist:
                serializers.ValidationError(_("Cette carte n'existe pas, Néo."))
            except Exception as e:
                raise serializers.ValidationError(f"{e}")

            try:
                nouvelle_table_ephemere, created = Table.objects.get_or_create(
                    name=nouvelle_table,
                    ephemere=True
                )
                if not created:
                    nouvelle_table_ephemere.archive = False
                    nouvelle_table_ephemere.save()
                attrs['pk_table'] = nouvelle_table_ephemere
            except IntegrityError:
                raise serializers.ValidationError(_("Une table non éphémère avec ce nom existe déja."))
            except Exception as e:
                raise serializers.ValidationError(f"{e}")

        if hasattr(self, "card"):
            attrs['card'] = self.card
        if hasattr(self, "card2"):
            attrs['card2'] = self.card2

        # On ajoute tout les wallets des serializers fedow
        attrs['wallets'] = self.payments_wallets()
        # On construit la liste des assets pour d'éventuels paiements
        payment_assets = self.get_payments_assets()
        attrs['payments_assets'] = payment_assets
        attrs['total_in_payments_assets'] = self.total_in_payments_assets(payment_assets)

        return attrs


class ArticlePourPreparationValidator(serializers.Serializer):
    pk = serializers.PrimaryKeyRelatedField(queryset=Articles.objects.all())
    qty = serializers.FloatField(required=True)
    void = serializers.BooleanField(required=False)
    gift = serializers.BooleanField(required=False)


class PreparationValidator(serializers.Serializer):
    articles = ArticlePourPreparationValidator(many=True)
    uuid_commande = serializers.PrimaryKeyRelatedField(queryset=CommandeSauvegarde.objects.all(), required=True)
    pk_responsable = serializers.PrimaryKeyRelatedField(queryset=Membre.objects.all())
    tag_id_cm = serializers.CharField(max_length=8, min_length=8, required=True)

    def validate_tag_id_cm(self, value):
        try:
            carte = CarteMaitresse.objects.get(carte__tag_id=value)
        except CarteMaitresse.DoesNotExist:
            raise serializers.ValidationError(_("Carte maitresse inconnue."))

        return carte
