from django.utils import timezone
from rest_framework import serializers
from APIcashless.models import CarteCashless, Configuration, Assets, Membre, MoyenPaiement
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework.generics import get_object_or_404
import logging
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
        if not self.fiche_membre.prenom :
            if not self.initial_data.get('first_name'):
                raise serializers.ValidationError(_(f'first_name est obligatoire'))
            self.fiche_membre.prenom = self.initial_data.get('first_name')
        if not self.fiche_membre.name :
            if not self.initial_data.get('last_name'):
                raise serializers.ValidationError(_(f'last_name est obligatoire'))
            self.fiche_membre.name = self.initial_data.get('last_name')
        if not self.fiche_membre.tel :
            if not self.initial_data.get('phone'):
                raise serializers.ValidationError(_(f'phone est obligatoire'))
            self.fiche_membre.tel = self.initial_data.get('phone')

        #not requiered
        if not self.fiche_membre.code_postal :
            self.fiche_membre.code_postal = self.initial_data.get('postal_code')
        if not self.fiche_membre.date_naissance :
            self.fiche_membre.date_naissance = self.initial_data.get('birth_date')
        if not self.fiche_membre.demarchage :
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