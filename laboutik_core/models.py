import json

import os
from uuid import uuid4
from decimal import Decimal

from django.forms import PasswordInput
from django.utils.html import format_html

# from epsonprinter.models import Printer
from laboutik_core.design_choices import FONT_ICONS_CHOICES, COLORS

from django.db import models
from datetime import datetime, timedelta
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from solo.models import SingletonModel
from django.db.models import Q, Sum
from django.conf import settings
from django.contrib.postgres.fields import JSONField

from stdimage import StdImageField, JPEGField
from stdimage.validators import MaxSizeValidator, MinSizeValidator
from django.utils.translation import gettext_lazy as _
from rest_framework_api_key.models import AbstractAPIKey, APIKey
from cryptography.hazmat.primitives import serialization
# from fedow_connect.utils import rsa_generator

from cryptography.hazmat.backends import default_backend
from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4

from dateutil import tz

runZone = tz.gettz(os.getenv('TZ'))
import logging

logger = logging.getLogger(__name__)


# Create your models here.


class TibiUser(AbstractUser):
    """
    Modèle de base pour les utilisateurs
    On utilise des uuid4 plutôt que des pk auto-incrementés
    """
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    email = models.EmailField(max_length=100, unique=True)
    image = JPEGField(upload_to="users_images", null=True, blank=True,
                      validators=[MinSizeValidator(540, 540)],
                      variations={
                          'bg_crop': (1080, 1080, True),
                          'md_crop': (540, 540, True),
                          'sm_crop': (270, 270, True)
                      },
                      delete_orphans=True,
                      verbose_name="Image de profil de l'utilisateur",
                      )

    LEVELING_CHOICES = (
        (1, "Commun"),
        (2, "Padawan"),
        (3, "Jedi"),
        (4, "Sith"),
    )
    leveling = models.PositiveIntegerField(choices=LEVELING_CHOICES, default=1)
    is_superstaff = models.BooleanField(default=False)


def dround(value):
    return Decimal(value).quantize(Decimal('1.00'))


class FrontDevice(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user: TibiUser = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, symmetrical=False, related_name="front_device")
    ip_lan = models.CharField(max_length=16, null=True, blank=True)
    hostname = models.CharField(max_length=100, null=True, blank=True)
    actif = models.BooleanField(default=False)

    DESKTOP, SMARTPHONE, RASPBERRY, NFC_SANS_FRONT, FRONT_SANS_NFC = 'FOR', 'FMO', 'FPI', 'SSF', 'FSN'
    PERIPH_CHOICES = [
        (DESKTOP, _('Front ordinateur')),
        (SMARTPHONE, _('Front smartphone')),
        (RASPBERRY, _('Front Raspberry')),
        (NFC_SANS_FRONT, _('Serveur NFC sans front')),
        (FRONT_SANS_NFC, _('Front sans lecteur NFC')),
    ]
    category = models.CharField(max_length=3, blank=True,
                                null=True, choices=PERIPH_CHOICES)

    def last_login(self):
        user: TibiUser = self.user
        return user.last_login

    last_login.allow_tags = True
    last_login.short_description = 'Last login'
    last_login.admin_order_field = 'user__last_login'

    # noinspection PyUnresolvedReferences
    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = _('Appareil')
        verbose_name_plural = _('Appareils')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.actif:
            self.user.is_active = True
            self.user.save()
        else:
            self.user.is_active = False
            self.user.save()
        super().save(force_insert, force_update, using, update_fields)


class Member(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    wallet = models.ForeignKey('Wallet', on_delete=models.PROTECT,
                               related_name='members', blank=True, null=True)
    pseudo = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(max_length=50, unique=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.pseudo:
            self.pseudo = self.pseudo.capitalize()
        if self.email:
            self.email = self.email.lower()

        super().save(force_insert, force_update, using, update_fields)


class PointOfSale(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(db_index=True, max_length=30,
                            verbose_name=_('nom'), unique=True)

    products = models.ManyToManyField(
        'Product', blank=True, verbose_name=_("articles"), related_name='pos')

    afficher_les_prix = models.BooleanField(default=True)
    accepte_especes = models.BooleanField(default=True)
    accepte_carte_bancaire = models.BooleanField(default=True)

    accepte_commandes = models.BooleanField(default=True)
    service_direct = models.BooleanField(default=True, verbose_name="Service direct ( vente au comptoir )")

    SALE, BADGE, CASHLESS = 'S', 'B', 'C'
    BEHAVIOR_CHOICES = [
        (SALE, _('Vente')),
        (BADGE, _('Badgeuse')),
        (CASHLESS, _('Rechargement')),
    ]

    behavior = models.CharField(
        max_length=1, choices=BEHAVIOR_CHOICES, default=SALE)

    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)

    # weight in the list. Heaviest at the bottom. Cashless always the last
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('weight', 'name')
        verbose_name = _('Point de vente')
        verbose_name_plural = _('Points de vente')


@receiver(post_save, sender=PointOfSale)
def pointOfSale_trigger(sender, instance: PointOfSale, created, **kwargs):
    if created:
        instance.weight = PointOfSale.objects.all().count() + 1
        instance.save()

        # Les cashless toujours à la fin
        for pdv in PointOfSale.objects.filter(comportement=PointOfSale.CASHLESS):
            pdv.weight = 2000
            pdv.save()


### OBJETS DU POINTS DE VENTE ###


class VAT(models.Model):
    name = models.CharField(max_length=30, null=False, blank=False)
    rate = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name=_("Taux"))

    def __str__(self):
        return f"{self.rate}%"

    def ht_from_ttc(self, prix):
        return dround(prix / (1 + (self.rate / 100)))

    def tva_from_ttc(self, prix):
        return dround(prix - self.ht_from_ttc(prix))

    class Meta:
        verbose_name = _("Taux TVA")
        verbose_name_plural = _("Taux TVA")


class Category(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Nom"), unique=True)
    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)
    bg_color = models.CharField(max_length=30, blank=True,
                                null=True, choices=COLORS,
                                verbose_name=_("Couleur de fond"))
    txt_color = models.CharField(max_length=30, blank=True,
                                 null=True, choices=COLORS,
                                 verbose_name=_("Couleur du texte"))
    img = JPEGField(upload_to="categories", null=True, blank=True,
                    validators=[MinSizeValidator(540, 540)],
                    variations={
                        'bg_crop': (1080, 1080, True),
                        'md_crop': (540, 540, True),
                        'sm_crop': (270, 270, True)
                    },
                    delete_orphans=True,
                    verbose_name="Image de la catégorie",
                    )

    cashless = models.BooleanField(default=False)
    # weight in the list. Heaviest at the bottom.
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('weight',)
        verbose_name = _("Catégorie d'articles")
        verbose_name_plural = _("Catégories d'articles")


@receiver(post_save, sender=Category)
def category_trigger(sender, instance: Category, created, **kwargs):
    if created:
        # poids d'apparition
        instance.weight = Category.objects.all().count() + 1
        instance.save()


class Option(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('weight',)
        verbose_name = _('Option')
        verbose_name_plural = _('Options')


class Product(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100)
    cost = models.PositiveIntegerField(default=0, verbose_name=("Couts"))
    category = models.ForeignKey(Category,
                                 on_delete=models.SET_NULL,
                                 related_name="products",
                                 null=True, blank=True,
                                 verbose_name="Catégorie")

    options = models.ManyToManyField(Option,
                                     blank=True,
                                     related_name="products",
                                     verbose_name="Options")

    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))
    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)
    bg_color = models.CharField(max_length=30, blank=True,
                                null=True, choices=COLORS,
                                verbose_name=_("Couleur de fond"))
    txt_color = models.CharField(max_length=30, blank=True,
                                 null=True, choices=COLORS,
                                 verbose_name=_("Couleur du texte"))
    img = JPEGField(upload_to="images/product/", null=True, blank=True,
                    validators=[MinSizeValidator(540, 540)],
                    variations={
                        'bg_crop': (1080, 1080, True),
                        'md_crop': (540, 540, True),
                        'sm_crop': (270, 270, True)
                    },
                    delete_orphans=True,
                    verbose_name=_("Image du produit"),
                    )

    SALE = 'VT'
    REFILL_EUROS = 'RE'
    REFILL_GIFT = 'RC'
    REFILL_FED = 'FD'
    ADHESIONS = 'AD'
    RETOUR_CONSIGNE = 'CR'
    VIDER_CARTE = 'VC'
    VOID_CARTE = 'VV'
    FRACTIONNE = 'FR'
    BILLET = 'BI'
    BADGEUSE = 'BG'

    METHOD_CHOICES = [
        (SALE, _('Vente')),
        (REFILL_EUROS, _('Recharge €')),
        (REFILL_GIFT, _('Recharge Cadeau')),
        (REFILL_FED, _('Recharge monnaie locale')),
        (ADHESIONS, _('Adhésions')),
        (RETOUR_CONSIGNE, _('Retour de consigne')),
        (VIDER_CARTE, _('Vider Carte')),
        (VOID_CARTE, _('Void Carte')),
        (FRACTIONNE, _('Fractionné')),
        (BILLET, _('Billet de concert')),
        (BADGEUSE, _('Badgeuse')),
    ]

    method = models.CharField(
        max_length=2,
        choices=METHOD_CHOICES,
        default=SALE,
    )

    archive = models.BooleanField(default=False,
                                  verbose_name=_("Archiver"))

    direct_to_printer = models.ForeignKey("Printer",
                                          null=True, blank=True,
                                          on_delete=models.SET_NULL)

    def petit_uuid(self):
        return str(self.uuid)[:8]

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('weight', 'method',)
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'


# noinspection PyUnusedLocal
@receiver(post_save, sender=Product)
def product_trigger(sender, instance: Product, created, **kwargs):
    """
    met par default la methode Vente Article lors de la création dans la page admin
    """
    if created:
        # poids d'apparition
        if instance.weight == 0:
            instance.weight = len(Product.objects.all()) + 1

        instance.save()

    if instance.archive:
        for pos in instance.pos.all():
            pos.products.remove(instance)


class Price(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    name = models.CharField(max_length=100, null=True, blank=True)
    price = models.PositiveIntegerField(verbose_name=_("Tarif"))

    def decimal(self):
        return dround(self.price / 100)

    def __str__(self):
        if self.name:
            return f"{self.name} : {self.price}€"
        else:
            return f"{self.product.name} : {self.price}€"


### MOYEN DE PAIEMENTS


class Asset(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    currency_code = models.CharField(max_length=3, null=True, blank=True)
    name = models.CharField(db_index=True, max_length=30, unique=True)

    # Is euro/dollar equivalent ?
    fiat = models.BooleanField(default=False)

    TOKEN_LOCAL_FIAT = 'LF'
    TOKEN_LOCAL_NOT_FIAT = 'LNF'
    EXTERNAL_FIAT = 'XF'
    EXTERNAL_NON_FIAT = 'XNF'
    FRACTION = 'FRC'
    STRIPE_LOCAL_FIAT = 'STP'
    STRIPE_FED_FIAT = 'FED'
    CASH = 'CA'
    CREDIT_CARD = 'CC'
    CHEQUE = 'CH'
    BADGE = 'BG'
    MEMBERSHIP = 'MS'

    CATEGORIES = [
        (TOKEN_LOCAL_FIAT, _('Token local €')),
        (TOKEN_LOCAL_NOT_FIAT, _('Token local cadeau')),
        (EXTERNAL_FIAT, _('Token fédéré exterieur €')),
        (EXTERNAL_NON_FIAT, _('Token fédéré cadeau')),
        (FRACTION, _('Fractionné')),
        (STRIPE_LOCAL_FIAT, _('Stripe local')),
        (STRIPE_FED_FIAT, _('Stripe Fedow')),
        (CASH, _('Espèces')),
        (CREDIT_CARD, _('Carte bancaire')),
        (CHEQUE, _('Cheque')),
        (BADGE, _('Badgeuse')),
        (MEMBERSHIP, _('Abonnement')),
    ]

    category = models.CharField(
        max_length=2,
        choices=CATEGORIES
    )

    def __str__(self):
        return f"{self.name}"


### CARTE CASHLESS
class Wallet(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)


class Origin(models.Model):
    place = models.CharField(max_length=50, blank=True, null=True)
    generation = models.IntegerField()
    img = JPEGField(upload_to='images/',
                    validators=[
                        MinSizeValidator(720, 720),
                        MaxSizeValidator(1920, 1920)
                    ],
                    blank=True, null=True,
                    variations={
                        'hdr': (720, 720),
                        'med': (480, 480),
                        'thumbnail': (150, 90),
                        'crop': (480, 270, True),
                    },
                    delete_orphans=True,
                    verbose_name='img',
                    )


class Card(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    tag_id = models.CharField(db_index=True,
                              max_length=8,
                              unique=True,
                              verbose_name="RFID First TagID"
                              )

    uuid_qrcode = models.UUIDField(blank=True, null=True,
                                   db_index=True,
                                   verbose_name='QrCode Uuid')

    number = models.CharField(db_index=True,
                              max_length=8,
                              blank=True, null=True,
                              verbose_name="Numéro imprimé")

    origin = models.ForeignKey(Origin, on_delete=models.PROTECT,
                               related_name='cards', blank=True, null=True)

    wallet = models.ForeignKey('Wallet', on_delete=models.PROTECT,
                               related_name='cards', blank=True, null=True)


### PREPARATION

class PreparationGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)

    categories = models.ManyToManyField(
        Category,
        related_name="preparation_groups",
        verbose_name=_("Catégories d'articles")
    )

    pos = models.ManyToManyField(
        PointOfSale,
        related_name="preparation_groups",
        verbose_name=_("Points de ventes")
    )
    counter = models.PositiveSmallIntegerField(default=0, verbose_name=_("Compteur de ticket"))


#### PRINTER

class Printer(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)

    thermal_printer_adress = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Adresse de l'imprimante",
        help_text="USB ex: 0x04b8,0x0e28 ou ip locale"
    )

    TM20, TM30 = "TM20", "TM30"
    PRINTERS = [
        (TM20, _('Epson TM20')),
        (TM30, _('Epson TM30')),
    ]
    model = models.CharField(max_length=5, choices=PRINTERS, default=TM20)

    serveur_impression = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Adresse du serveur d'impression"
    )

    api_serveur_impression = models.CharField(
        max_length=50,
        blank=True, null=True,
        verbose_name="Clé d'api pour serveur d'impression"
    )

    revoquer_api_serveur_impression = models.BooleanField(
        default=False,
        verbose_name='Révoquer la clé API',
        help_text="Selectionnez et validez pour supprimer la clé API et entrer une nouvelle."
    )

    def _api_serveur_impression(self):
        if self.api_serveur_impression:
            return f"{self.api_serveur_impression[:3]}{'*' * (len(self.api_serveur_impression) - 3)}"
        else:
            return None

    def __str__(self):
        return self.name


class PrintingGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)

    categories = models.ManyToManyField(
        Category,
        related_name="printing_groups",
        verbose_name=_("Catégories d'articles")
    )

    pos = models.ManyToManyField(
        PointOfSale,
        related_name="printing_groups",
        verbose_name=_("Points de ventes")
    )

    printer = models.ForeignKey('Printer',
                                on_delete=models.CASCADE,
                                verbose_name=_("Imprimante"))

    counter = models.PositiveSmallIntegerField(default=0, verbose_name=_("Compteur de ticket"))
    qty_ticket = models.PositiveSmallIntegerField(default=1, verbose_name=_("Nombre de copie à imprimer"))

    class Meta:
        verbose_name = "Groupe d'impression"
        verbose_name_plural = "Groupes d'impressions"
