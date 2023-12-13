import json

import os
from uuid import uuid4
from decimal import Decimal

from django.apps import apps
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


def dround(value):
    return Decimal(value).quantize(Decimal('1.00'))


class IpUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ip = models.GenericIPAddressField()


# Create your models here.

## CONFIGURATION SOLO

class Configuration(SingletonModel):
    ### Preparation and service options
    service_validation = models.BooleanField(default=False, verbose_name=_("Validation manuelle des services"),
                                             help_text=_(
                                                 "Mécanisme de validation d'état de service manuel. Si activé, vous devez indiquer chaque commande comme servie manuellement."))


## USER AND AUTH MODELS

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
    wallet = models.OneToOneField('Wallet', on_delete=models.PROTECT, related_name='member',
                                  verbose_name=_("Portefeille"), blank=True, null=True)
    username = models.CharField(max_length=150, null=True, blank=True, verbose_name=_("Pseudo"))
    email = models.EmailField(max_length=50, unique=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.username:
            self.username = self.username.capitalize()
        if self.email:
            self.email = self.email.lower()

        super().save(force_insert, force_update, using, update_fields)


class PointOfSale(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(db_index=True, max_length=30,
                            verbose_name=_('nom'), unique=True)

    products = models.ManyToManyField(
        'Product', blank=True, verbose_name=_("articles"), related_name='pos')

    show_price = models.BooleanField(default=True)
    cash = models.BooleanField(default=True)
    credit_card = models.BooleanField(default=True)
    cashless_card = models.BooleanField(default=True)

    send_command = models.BooleanField(default=True)
    direct_service = models.BooleanField(default=True, verbose_name=_("Service direct ( vente au comptoir )"))

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
    FRACTIONAL = 'FR'
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
        (FRACTIONAL, _('Fractionné')),
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
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="prices")
    asset = models.ForeignKey("Asset", on_delete=models.SET_NULL,
                              blank=True, null=True,
                              related_name="prices", verbose_name=_("Tarif spécial pour"),
                              help_text=_(
                                  "Si non vide, alors l'article aura un tarif différent pour ce moyen de paiement."))
    name = models.CharField(max_length=100, null=True, blank=True)
    value = models.PositiveIntegerField(verbose_name=_("Tarif (en centimes)"))

    def decimal(self):
        return dround(self.value / 100)

    def __str__(self):
        if self.name:
            return f"{self.name} : {self.value}€"
        else:
            return f"{self.product.name} : {self.value}€"

    class Meta:
        verbose_name = 'Tarif'
        verbose_name_plural = 'Tarifs'


class PriceSold(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    payment_uuid = models.UUIDField(editable=False, default=uuid4)

    price = models.ForeignKey(Price, on_delete=models.PROTECT, related_name="prices_sold")
    value = models.IntegerField(verbose_name=_("Tarif en centimes"))
    qty = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True)

    # Can be external, not only command object
    command = models.UUIDField(editable=False)
    table = models.ForeignKey("Table", null=True, on_delete=models.PROTECT)

    pos = models.ForeignKey("PointOfSale", null=True, on_delete=models.PROTECT)
    card = models.ForeignKey("Card", null=True, on_delete=models.PROTECT)
    wallet = models.ForeignKey("Wallet", null=True, on_delete=models.PROTECT)
    asset = models.ForeignKey("Asset", null=True, on_delete=models.PROTECT)
    responsible = models.ForeignKey("Member", null=True, on_delete=models.PROTECT)

    from_fractional = models.BooleanField(default=False)

    ip_user = models.ForeignKey("IpUser", on_delete=models.PROTECT,
                                null=True, blank=True)
    logs = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Article vendu'
        verbose_name_plural = 'Articles vendus'


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


class Token(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=False)
    value = models.PositiveIntegerField(default=0, help_text=_("Valeur, en centimes."))
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='tokens')
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='tokens')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['wallet', 'asset'], name="unique_token_for_wallet_and_asset"),
        ]

    def __str__(self):
        return f"{self.asset.name} : {dround(self.value)}"


class PrimaryCard(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    wallet = models.OneToOneField(Wallet, on_delete=models.PROTECT, related_name='primary_wallet')
    pos = models.ForeignKey(PointOfSale, on_delete=models.PROTECT, related_name='primary_wallets')
    edit_mode = models.BooleanField(default=False, verbose_name=_("Mode gérant.e"))


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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # Upper tag_id and number
        # If uuid for qrcode is not set, generate one
        self.tag_id = self.tag_id.upper()
        if not self.uuid_qrcode:
            self.uuid_qrcode = uuid4()
        if not self.number:
            self.number = str(self.uuid_qrcode)[:8]
        self.number = self.number.upper()
        super().save(force_insert, force_update, using, update_fields)


### TABLES, COMMANDS and PREPARATIONS

class SavedCommand(models.Model):
    uuid = models.UUIDField(primary_key=True,
                            default=uuid4,
                            editable=False)

    service = models.UUIDField(default=uuid4)

    responsible = models.ForeignKey("Member",
                                    on_delete=models.SET_NULL,
                                    null=True)

    table = models.ForeignKey("Table",
                              on_delete=models.SET_NULL,
                              related_name="commands",
                              null=True)

    datetime = models.DateTimeField(auto_now_add=True)

    ticket_number = JSONField(default=dict)

    OPEN, SERVED, PAID, SERVED_PAID, CANCELLED = "O", "S", "P", "SP", "CA"
    COMMAND_STATE = [
        (OPEN, _('Ouverte')),
        (SERVED, _('Servie')),
        (PAID, _('Payée')),
        (SERVED_PAID, _('Servie et payée')),
        (CANCELLED, _('Annulée')),
    ]
    state = models.CharField(
        max_length=2, choices=COMMAND_STATE, default=OPEN)

    comment = models.TextField(blank=True, null=True)

    archived = models.BooleanField(default=False)

    def outstanding_balance(self):
        # Reste à payer
        total = 0
        for article in self.articles \
                .exclude(state__in=[self.PAID, self.SERVED_PAID, self.CANCELLED]):
            total += article.reste_a_payer * article.article.prix

        return total

    def command_id(self):
        return str(self.uuid).split('-')[0]

    def service_id(self):
        return str(self.service).split('-')[0]

    def __str__(self):
        return (f"{str(self.uuid).split('-')[0]}")

    def check_state(self):
        articles = self.articles.all()
        article_non_payees = articles.exclude(reste_a_payer=0).count()
        article_non_servis = articles.exclude(reste_a_servir=0).count()

        if article_non_payees == 0 and article_non_servis == 0:
            if self.state != self.SERVED_PAID:
                self.state = self.SERVED_PAID
                self.save()

        elif article_non_payees == 0:
            if self.state != self.PAID:
                self.state = self.PAID
                self.save()

        elif article_non_servis == 0:
            if self.state != self.SERVED:
                self.state = self.SERVED
                self.save()

    class Meta:
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")
        ordering = ("-datetime",)


class SavedArticle(models.Model):
    command = models.ForeignKey("SavedCommand",
                                on_delete=models.CASCADE,
                                related_name='articles',
                                verbose_name=_("Commande"))

    price = models.ForeignKey(Price, on_delete=models.PROTECT)

    qty = models.DecimalField(max_digits=6, decimal_places=2)
    reste_a_payer = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reste_a_servir = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    PREP, READY, SERVED, PAID, SERVED_PAID, CANCELED, GIFT = "PP", "RD", "SV", "PA", "SP", "CA", "GF"
    ARTICLE_STATE = [
        (PREP, _('En préparation')),
        (READY, _('Prêt à servir')),
        (SERVED, _('Servi')),
        (PAID, _('Payé')),
        (SERVED_PAID, _('Servi et payé')),
        (CANCELED, _('Annulé')),
        (GIFT, _('Offert')),
    ]
    state = models.CharField(
        max_length=2, choices=ARTICLE_STATE, default=PREP)
    #
    # def table(self):
    #     return self.command.table
    #
    # def __str__(self):
    #     return f"{self.article.name} {self.pk} {str(self.command.uuid).split('-')[0]}"


@receiver(post_save, sender=SavedArticle)
def reste_a_check(sender, instance: SavedArticle, created, **kwargs):
    logger.info(f'--- function reste_a_check : post_save SavedArticle pour {instance}')
    config = Configuration.get_solo()
    saved_article: SavedArticle = instance
    price: Price = saved_article.price
    product: Product = price.product
    command: SavedCommand = instance.command
    table = command.table

    if created:
        # On incrémente la valeur du reste à payer à la création de la commande.
        # L'aticle vient d'être commandé : il n'est pas encore payé
        saved_article.reste_a_payer = saved_article.qty

        if product.method == Product.SALE:
            # Le produit est-il dans un groupement de préparation ?
            # Si oui, nous vérifions la configuration pour indiquer le comportement d'état servi/non servi.
            if product.category:
                if product.category.preparation_groups.count() > 0:
                    if config.service_validation:
                        if instance.qty > 0:
                            instance.reste_a_servir = instance.qty

        instance.save()


    elif command.state != SavedCommand.CANCELLED:
        # Si tout a été payé et tout est servi, on passe les articles en SERVED_PAID
        if instance.reste_a_payer == 0 and instance.reste_a_servir == 0 \
                and instance.state != SavedArticle.SERVED_PAID:
            instance.state = SavedArticle.SERVED_PAID
            instance.save()
            command.check_state()


        # Si il reste a servir, mais que tout est payé :
        elif instance.reste_a_payer == 0 \
                and instance.state not in [SavedArticle.PAID, SavedArticle.SERVED_PAID]:

            # Tous les articles de cette ligne sont payés,
            # Mise à jour du state de la commande.
            instance.state = SavedArticle.PAID
            instance.save()
            command.check_state()


        # Si tout est servi mais qu'il reste a payer :
        elif instance.reste_a_servir == 0 \
                and instance.statut not in [SavedArticle.SERVED, SavedArticle.SERVED_PAID]:

            # Tous les articles de cette ligne sont servis,
            # on vérifie et mets à jour le status de la commande.
            instance.statut = SavedArticle.SERVED
            instance.save()
            command.check_state()

        # Si toutes les commandes de la table sont terminées,
        # on vérifie et mets à jour le reste à payer des articles et des commandes.
        # Au cas où un paiement fractionné a été effectué.
        if table:
            if table.reste_a_payer() == 0:
                logger.info(f"Table {table.name} TOUT PAYEE ! {instance}")

                payment_list = []
                paiements_fractionnes_meme_service = SavedArticle.objects.filter(
                    price__product___method=Product.FRACTIONAL,
                    commande__service=command.service,
                    reste_a_payer__lt=0,
                )

                for paiement_fractionne in paiements_fractionnes_meme_service:
                    # On teste si le paiement fractionné n'a pas été divisé en deux cadeaux / euros
                    paiement_fractionne_dans_article_vendu = PriceSold.objects.filter(
                        price=paiement_fractionne.price,
                        commande=f"{paiement_fractionne.command.uuid}",
                    )

                    if not paiement_fractionne_dans_article_vendu.exists():
                        logger.error(f"Erreur lors d'un rapprochement de paiement fractionné. Aucun paiement en Db.")
                        raise ValueError(
                            f"Erreur lors d'un rapprochement de paiement fractionné. Aucun paiement en Db.")
                    else:
                        for article_vendu in paiement_fractionne_dans_article_vendu:
                            payment_list.append({
                                'article_commande': paiement_fractionne,
                                'article_vendu': article_vendu,
                                'qty': abs(article_vendu.qty),
                            })

                articles_a_rentrer_en_db = {}
                for command in table.commands.exclude(
                        state__in=[SavedCommand.PAID, SavedCommand.SERVED_PAID, SavedCommand.CANCELLED]):
                    command: SavedCommand

                    for saved_article in command.articles.all():
                        saved_article: SavedArticle
                        if saved_article.reste_a_payer != 0:
                            articles_a_rentrer_en_db[saved_article] = saved_article.reste_a_payer
                            saved_article.reste_a_payer = 0
                            saved_article.statut = saved_article.PAID
                            saved_article.save()

                # On rentre en dB les articles qui n'ont pas été comptabilisés à cause du paiement fractionné.
                # Dans le but de pouvoir comptabiliser les articles vendus.

                # D'abord, nous cherchons les paiements fractionnés du même service,
                # pour savoir, entre autre quel ont été les moyens de paiements,
                # et on crée un dictionnaire avec la qty en valeur positive.

                # Enfin, nous créons le rapprochement entre les paiments fractionnés et les articles vendus.

                for saved_article, qty_non_comptabilisee in articles_a_rentrer_en_db.items():
                    saved_article: SavedArticle
                    price = saved_article.price
                    product = price.product
                    total_non_comptabilisee: Decimal = dround(qty_non_comptabilisee * price.value)

                    if product.method == Product.SALE:
                        # On rentre en DB la vente

                        for paiement in payment_list:
                            paiement: dict
                            article_vendu: PriceSold = paiement.get('article_vendu')
                            qty: Decimal = paiement.get('qty')

                            # Tant que l'un des deux est > 0 :
                            while qty > 0 and qty_non_comptabilisee > 0:
                                a_encaisser = dround(qty - total_non_comptabilisee)

                                if a_encaisser >= 0:
                                    # logger.info(
                                    #     f"On peut piocher {qty}€ dans {article_vendu} "
                                    #     f": a encaisser >= 0 : {a_encaisser}")

                                    PriceSold.objects.create(
                                        price=price,
                                        value=price.value,
                                        qty=qty_non_comptabilisee,
                                        pos=article_vendu.pos,
                                        card=article_vendu.card,
                                        wallet=article_vendu.wallet,
                                        asset=article_vendu.asset,
                                        responsible=article_vendu.responsible,
                                        command=article_vendu.command,
                                        payment_uuid=article_vendu.payment_uuid,
                                        table=article_vendu.table,
                                        from_fractional=True,
                                        ip_user=article_vendu.ip_user,
                                    )
                                    qty = a_encaisser
                                    qty_non_comptabilisee = 0
                                    total_non_comptabilisee = 0


                                elif a_encaisser < 0:
                                    qty_a_encaisser = Decimal(float(qty) / float(article.article.prix))

                                    logger.info(
                                        f"On peut piocher {qty}€ dans {article_vendu} : "
                                        f"a encaisser < 0 : {a_encaisser} - "
                                        f"qty_a_encaisser = {qty_a_encaisser}")

                                    ArticleVendu.objects.create(
                                        article=article.article,
                                        prix=article.article.prix,
                                        qty=qty_a_encaisser,
                                        pos=article_vendu.pos,
                                        carte=article_vendu.carte,
                                        membre=article_vendu.membre,
                                        moyen_paiement=article_vendu.moyen_paiement,
                                        responsable=article_vendu.responsable,
                                        commande=article_vendu.commande,
                                        uuid_paiement=article_vendu.uuid_paiement,
                                        table=article_vendu.table,
                                        depuis_fractionne=True,
                                        ip_user=article_vendu.ip_user,
                                    )

                                    # restera :
                                    total_non_comptabilisee -= qty
                                    qty_non_comptabilisee = Decimal(total_non_comptabilisee) / Decimal(
                                        article.article.prix)

                                    # Plus rien à rapprocher, on termine la boucle :
                                    qty = 0

                instance.commande.check_statut()


class CategoryTable(models.Model):
    name = models.CharField(max_length=20, unique=True)
    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)

    def __str__(self):
        return self.name


class Table(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    categorie = models.ForeignKey(CategoryTable,
                                  blank=True, null=True,
                                  on_delete=models.SET_NULL)

    FREE, USED = 'L', 'O'
    STATES = [
        (FREE, _('Libre')),
        (USED, _('Occupée')),
    ]
    state = models.CharField(max_length=1, choices=STATES, default=FREE)

    ephemeral = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)

    def check_state(self):
        commands_in_process = self.commands \
            .exclude(states__in=[SavedCommand.SERVED_PAID, SavedCommand.CANCELLED])

        if commands_in_process.count() == 0:
            self.state = Table.FREE  # table libre
            self.save()
        else:
            self.state = Table.USED  # pas d'ouverte, tout est servi !
            self.save()

    def reste_a_payer(self):
        reste_a_payer = 0
        for commande in self.commands \
                .exclude(state__in=[SavedCommand.CANCELLED, SavedCommand.SERVED_PAID, SavedCommand.PAID]):
            reste_a_payer += commande.reste_a_payer()

        return reste_a_payer

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Table")
        verbose_name_plural = _("Tables")
        ordering = ("poids",)


# noinspection PyPep8Naming,PyUnusedLocal
@receiver(pre_save, sender=Table)
def incrementation_du_poids_table(sender: Table, instance, **kwargs):
    if instance.weight == 0:
        instance.weight = sender.objects.count() + 1


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
