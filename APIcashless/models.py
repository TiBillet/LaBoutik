import json

import os, random
from uuid import uuid4
from decimal import Decimal

import requests
from django.core.cache import cache
from django.utils.html import format_html

from epsonprinter.models import Printer
from .fontawesomeicons import FONT_ICONS_CHOICES

from django.db import models
from datetime import datetime, timedelta, time
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
from fedow_connect.utils import rsa_generator, fernet_decrypt, fernet_encrypt

from cryptography.hazmat.backends import default_backend

# import requests, json
# from requests.auth import HTTPBasicAuth

# pour appareillement
# from django.contrib.auth import get_user_model

from dateutil import tz

runZone = tz.gettz(os.getenv('TZ'))
import logging

logger = logging.getLogger(__name__)


def dround(value):
    return Decimal(value).quantize(Decimal('1.00'))


class Appareil(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(max_length=100, verbose_name=_("Nom"), blank=True, null=True)
    pin_code = models.PositiveIntegerField(verbose_name=_("Code PIN"),
                                           blank=True, null=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)

    ip_lan = models.GenericIPAddressField(null=True, blank=True)
    ip_wan = models.GenericIPAddressField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    actif = models.BooleanField(default=False)
    hostname = models.CharField(max_length=500, null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)

    DESKTOP, SMARTPHONE, RASPBERRY, NFC_SANS_FRONT, FRONT_SANS_NFC = 'FOR', 'FMO', 'FPI', 'SSF', 'FSN'
    PERIPH_CHOICES = [
        (DESKTOP, _('Front ordinateur')),
        (SMARTPHONE, _('Front smartphone')),
        (RASPBERRY, _('Front Raspberry')),
        (NFC_SANS_FRONT, _('Serveur NFC sans front')),
        (FRONT_SANS_NFC, _('Front sans lecteur NFC')),
    ]
    periph = models.CharField(max_length=3, blank=True,
                              null=True, choices=PERIPH_CHOICES)

    def last_login(self):
        if self.user:
            # noinspection PyUnresolvedReferences
            return self.user.last_login
        return None

    last_login.allow_tags = True
    last_login.short_description = _('Last login')
    last_login.admin_order_field = 'user__last_login'

    # noinspection PyUnresolvedReferences
    def __str__(self):
        if self.name:
            return self.name
        return "N/A"

    class Meta:
        verbose_name = _('Appareil')
        verbose_name_plural = _('Appareils')


# @receiver(pre_save, sender=Appareil)
# def appareil_actif_trigger(sender, instance: Appareil, *args, **kwargs):
#     if instance._state.adding:  # = if created
#         instance.pin_code = random.randint(100000, 999999)


class Appairage(models.Model):
    front = models.OneToOneField(
        Appareil,
        related_name="appareillement_front",
        on_delete=models.CASCADE,
        limit_choices_to=Q(periph=Appareil.FRONT_SANS_NFC)
    )

    lecteur_nfc = models.OneToOneField(
        Appareil,
        related_name="appareillement_lecteur_nfc",
        on_delete=models.CASCADE,
        limit_choices_to=Q(periph=Appareil.NFC_SANS_FRONT)
    )

    def __str__(self):
        return f"{self.front.user} - {self.lecteur_nfc.user}"

    class Meta:
        verbose_name = _('Appairage')
        verbose_name_plural = _('Appairages')


class StatusMembre(models.Model):
    name = models.CharField(db_index=True, max_length=50, unique=True)

    def __str__(self):
        return self.name


class Membre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    # Wallet FEDOW
    wallet = models.OneToOneField("Wallet", on_delete=models.PROTECT, null=True, blank=True, related_name='membre')

    name = models.CharField(
        db_index=True, max_length=50, verbose_name=_("Nom"))
    prenom = models.CharField(max_length=50, verbose_name=_(
        "Prénom"), null=True, blank=True)

    pseudo = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True, unique=True)
    demarchage = models.BooleanField(
        default=True, verbose_name=_("J'accepte de recevoir la newsletter"))

    # numero_adherant = models.CharField(max_length=50, unique=True, null=True, blank=True)
    code_postal = models.IntegerField(null=True, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    tel = models.CharField(max_length=15, null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)

    status = models.ForeignKey(
        StatusMembre, null=True, blank=True, on_delete=models.SET_NULL)

    date_inscription = models.DateField(null=True, blank=True)
    date_derniere_cotisation = models.DateField(null=True, blank=True)

    date_ajout = models.DateTimeField(auto_now_add=True)

    last_action = models.DateTimeField(auto_now=True, verbose_name="Présence")

    cotisation = models.DecimalField(max_digits=10, decimal_places=2, default=20,
                                     help_text=_(
                                         "Vous pouvez modifier la valeur par default dans la page de configuration générale"))

    ajout_cadeau_auto = models.BooleanField(default=False)

    adhesion_auto_espece = models.BooleanField(default=False)
    adhesion_auto_cb = models.BooleanField(default=True)

    ADMIN, FRONT, QRCODE, BILLETTERIE, HELLOASSO = 'A', 'F', 'Q', 'B', 'H'
    ORIGIN_ADHESIONS_CHOICES = [
        (ADMIN, _('Depuis Admin')),
        (FRONT, _('Front Cashless')),
        (QRCODE, _('Scan QR Code')),
        (BILLETTERIE, _("Billetterie")),
        (HELLOASSO, _('HelloAsso')),
    ]
    adhesion_origine = models.CharField(max_length=1, choices=ORIGIN_ADHESIONS_CHOICES, default=ADMIN,
                                        verbose_name=_("Source"))

    ESPECE, CB, GRATUIT, NAN = 'E', 'C', 'G', 'N'
    TYPE_CHOICES = [
        (ESPECE, _('Espece')),
        (CB, _('CB')),
        (GRATUIT, _('Gratuit')),
        (NAN, _("Adhérer plus tard")),
    ]
    paiment_adhesion = models.CharField(max_length=1, choices=TYPE_CHOICES, default=NAN,
                                        verbose_name=_("Methode de paiement"))

    choice_adhesion = models.ForeignKey("Articles", null=True, blank=True, on_delete=models.SET_NULL)

    def choice_str(self, choice_list: list, choice_str: str):
        for choice in choice_list:
            if choice[0] == choice_str:
                return choice[1]
        return ''

    def small_commentaire(self):
        if self.commentaire:
            return self.commentaire[:60] + " ..."
        else:
            return ""

    def derniere_presence(self):
        return self.last_action

    derniere_presence.short_description = _("Derniere présence")
    derniere_presence.admin_order_field = '-last_action'

    def numero_carte(self):
        # Comprehension list :
        num_carte = ", ".join([f"{cart.number}" for cart in self.CarteCashless_Membre.all()])
        return num_carte

    numero_carte.short_description = "Cartes liées"


    def a_jour_cotisation(self):

        calcul_adh = Configuration.get_solo().calcul_adhesion
        if not self.date_derniere_cotisation:
            return False

        if calcul_adh == Configuration.ADH_365JOURS:
            return timezone.now().date() <= (self.date_derniere_cotisation + timedelta(days=365))

        elif calcul_adh == Configuration.ADH_CIVILE:
            return timezone.now().date().year == self.date_derniere_cotisation.year

        elif calcul_adh == Configuration.ADH_GLISSANTE_OCT:
            if timezone.now().date().year == (self.date_derniere_cotisation.year + 1):
                if self.date_derniere_cotisation.month >= 10:
                    return True
            return timezone.now().date().year == self.date_derniere_cotisation.year

    def prochaine_echeance(self):
        calcul_adh = Configuration.get_solo().calcul_adhesion
        if not self.date_derniere_cotisation:
            return timezone.now()

        if calcul_adh == Configuration.ADH_CIVILE:
            return datetime.strptime(f"01/01/{self.date_derniere_cotisation.year + 1}", "%d/%m/%Y")

        return self.date_derniere_cotisation + timedelta(days=365)

    def is_gerant(self):
        for carte in CarteMaitresse.objects.filter(carte__membre=self):
            if carte.edit_mode:
                return True
        return False

    def _name(self):
        if self.name:
            return self.name
        elif self.pseudo:
            return self.pseudo
        elif self.email:
            return self.email
        else:
            return "Anonymous"

    class Meta:
        ordering = ('-date_ajout',)
        verbose_name = _('Membre responsable')
        verbose_name_plural = _('Membres responsables')

    def __str__(self):
        if self.pseudo:
            return self.pseudo
        elif self.prenom:
            return f"{self.name} {self.prenom}"
        elif self.name:
            return self.name
        elif self.email:
            return self.email
        else:
            return "Anonymous"


# noinspection PyPep8Naming,PyUnusedLocal
@receiver(pre_save, sender=Membre)
def membres_creation_receiver(sender, instance, **kwargs):
    # instance: Membre
    if instance.name:
        instance.name = instance.name.upper()
    if instance.prenom:
        instance.prenom = instance.prenom.capitalize()
    if instance.email:
        instance.email = instance.email.lower()


class Couleur(models.Model):
    name = models.CharField(max_length=30, verbose_name=_("Nom"), unique=True)
    name_fr = models.CharField(
        max_length=30, verbose_name=_("Nom FR"), blank=True, null=True)
    hexa = models.CharField(max_length=30, verbose_name=_(
        "Code Couleur Hexa"), blank=True, null=True)

    def __str__(self):
        return self.name_fr

    class Meta:
        verbose_name = _("Couleur")
        verbose_name_plural = _("Couleurs")


class PointDeVente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(db_index=True, max_length=30,
                            verbose_name='nom', unique=True)
    wallet = models.CharField(max_length=38, blank=True, null=True)
    articles = models.ManyToManyField(
        'Articles', blank=True, verbose_name=_("articles"), related_name='points_de_ventes')

    categories = models.ManyToManyField(
        'Categorie',
        blank=True,
        verbose_name=_("categories"),
        related_name='points_de_ventes',
    )

    afficher_les_prix = models.BooleanField(default=True)
    accepte_especes = models.BooleanField(default=True)
    accepte_carte_bancaire = models.BooleanField(default=True)
    accepte_cheque = models.BooleanField(default=False)

    accepte_commandes = models.BooleanField(default=True)
    service_direct = models.BooleanField(default=True, verbose_name=_("Service direct ( vente au comptoir )"))

    VENTE, CASHLESS = 'A', 'C'
    TYPE_CHOICES = [
        (VENTE, _('Vente')),
        (CASHLESS, _('Rechargement')),
    ]

    comportement = models.CharField(
        max_length=1, choices=TYPE_CHOICES, default=VENTE)

    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)

    poid_liste = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('poid_liste', 'name')
        verbose_name = _('Point de vente')
        verbose_name_plural = _('Points de vente')


@receiver(post_save, sender=PointDeVente)
def pointDeVente_postsave(sender, instance: PointDeVente, created, **kwargs):
    if created:
        if instance.poid_liste == 0:
            instance.poid_liste = PointDeVente.objects.all().count() + 1
            instance.save()

    # Les cashless toujours à la fin
    # PointDeVente.objects.filter(comportement=PointDeVente.CASHLESS).update(poid_liste=2000)

    # Fabrication du moyen de paiement cheque s'il n'exsite pas
    if instance.accepte_cheque:
        MoyenPaiement.objects.get_or_create(name=_("Chèque"), blockchain=False, categorie=MoyenPaiement.CHEQUE)


# Utilisé par le front pour connaitre le comportement de l'article
# TODO: Changer sur le front le nom des variables pour correspondre à la nouvelle nomenclature (methode_choices)
class Methode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(db_index=True, max_length=30,
                            verbose_name=_("Nom"), unique=True)
    info = models.CharField(max_length=300, verbose_name=_(
        "Information"), blank=True, null=True)

    def __str__(self):
        return self.name


class TauxTVA(models.Model):
    name = models.CharField(max_length=30)
    taux = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name=_("Taux"))

    def __str__(self):
        return f"{self.taux}%"

    def ht_from_ttc(self, prix):
        return dround(prix / (1 + (self.taux / 100)))

    def tva_from_ttc(self, prix):
        return dround(prix - self.ht_from_ttc(prix))

    class Meta:
        verbose_name = _("Taux TVA")
        verbose_name_plural = _("Taux TVA")


class Categorie(models.Model):
    name = models.CharField(max_length=30,
                            verbose_name=_("Nom"),
                            unique=True)

    poid_liste = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    url_image = models.CharField(max_length=200, verbose_name=_(
        "Url Image"), blank=True, null=True)

    couleur_texte = models.ForeignKey(Couleur,
                                      blank=True,
                                      null=True,
                                      on_delete=models.SET_NULL,
                                      related_name='couleur_texte_categorie')

    couleur_backgr = models.ForeignKey(Couleur,
                                       blank=True,
                                       null=True,
                                       on_delete=models.SET_NULL,
                                       related_name='couleur_backgr_categorie')

    tva = models.ForeignKey(TauxTVA,
                            blank=True,
                            null=True,
                            on_delete=models.SET_NULL,
                            related_name='tva_categorie')

    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)

    cashless = models.BooleanField(default=False)

    def __str__(self):
        if self.tva:
            return f"{self.name} - TVA : {self.tva.taux}%"
        return f"{self.name} - TVA : 0%"

    class Meta:
        ordering = ('poid_liste',)
        verbose_name = _("Catégorie d'articles")
        verbose_name_plural = _("Catégorie d'articles")


@receiver(post_save, sender=Categorie)
def poids_Categorie_trigger(sender, instance: Categorie, created, **kwargs):
    if created:
        # poids d'apparition
        instance.poid_liste = Categorie.objects.all().count() + 1
        instance.save()


class GroupementCategorie(models.Model):
    name = models.CharField(max_length=50, unique=True)

    categories = models.ManyToManyField(
        Categorie,
        related_name="groupements",
        verbose_name=_("Catégories"),
    )

    icon = models.CharField(max_length=30,
                            blank=True, null=True,
                            choices=FONT_ICONS_CHOICES)

    printer = models.ForeignKey(Printer,
                                on_delete=models.CASCADE,
                                null=True,
                                blank=True,
                                verbose_name=_("Imprimante"))

    compteur_ticket_journee = models.PositiveSmallIntegerField(default=0, verbose_name=_("Compteur de ticket"))

    qty_ticket = models.PositiveSmallIntegerField(default=1, verbose_name=_("Nombre de copie à imprimer"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Préparation & impression')
        verbose_name_plural = _('Préparations & impressions')


class Articles(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(max_length=300, verbose_name=_("Nom"))
    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Prix de vente"))
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2,
                                     default=0, verbose_name=_("Prix d'achat"))

    poid_liste = models.PositiveSmallIntegerField(default=0, verbose_name=_("Poids"))

    categorie = models.ForeignKey(
        Categorie,
        blank=True, null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Catégorie"),
    )

    # Utilisé par le front pour connaitre le comportement de l'article
    # TODO: Changer sur le front le nom des variables pour correspondre à la nouvelle nomenclature (methode_choices)
    methode = models.ForeignKey(
        Methode, blank=True, null=True, on_delete=models.PROTECT)

    image = StdImageField(upload_to='images/',
                          null=True, blank=True,
                          validators=[MaxSizeValidator(200, 200)],
                          variations={
                              'thumbnail': (60, 60),
                          }, delete_orphans=True)

    couleur_texte = models.ForeignKey(Couleur, blank=True, null=True,
                                      related_name="couleur_texte",
                                      on_delete=models.SET_NULL)

    archive = models.BooleanField(default=False,
                                  verbose_name=_("Archiver"))
    fractionne = models.BooleanField(default=False)

    VENTE = 'VT'
    RECHARGE_EUROS = 'RE'
    # RECHARGE_EUROS_FEDERE = 'RF'
    RECHARGE_CADEAU = 'RC'
    RECHARGE_TIME = 'TM'
    ADHESIONS = 'AD'
    RETOUR_CONSIGNE = 'CR'
    VIDER_CARTE = 'VC'
    VOID_CARTE = 'VV'
    FRACTIONNE = 'FR'
    BILLET = 'BI'
    BADGEUSE = 'BG'
    FIDELITY = 'FD'
    CASHBACK = 'HB'

    METHODES_CHOICES = [
        (VENTE, _('Vente')),
        (RECHARGE_EUROS, _('Recharge €')),
        # (RECHARGE_EUROS_FEDERE, _('Recharge fédérée €')),
        (RECHARGE_CADEAU, _('Recharge Cadeau')),
        (RECHARGE_TIME, _('Recharge Temps')),
        (ADHESIONS, _('Adhésions')),
        (RETOUR_CONSIGNE, _('Retour de consigne')),
        (VIDER_CARTE, _('Vider Carte')),
        (VOID_CARTE, _('Void Carte')),
        (FRACTIONNE, _('Fractionné')),
        (BILLET, _('Billet de concert')),
        (BADGEUSE, _('Badgeuse')),
        (FIDELITY, _('Fidélité')),
        (CASHBACK, _('Cashback')),
    ]

    methode_choices = models.CharField(
        max_length=2,
        choices=METHODES_CHOICES,
        default=VENTE,
        verbose_name=_("methode"),
    )

    direct_to_printer = models.ForeignKey(Printer,
                                          null=True, blank=True,
                                          on_delete=models.SET_NULL,
                                          help_text=_("Activez pour une impression directe après chaque vente. Utile pour vendre des billets."),
                                          )

    decompte_ticket = models.BooleanField(default=False,
                                          help_text=_(
                                              "Incrémente le décompte des billets vendu à la journée et imprimé sur le ticket."))

    fedow_asset = models.ForeignKey("MoyenPaiement",
                                    null=True, blank=True,
                                    on_delete=models.SET_NULL,
                                    related_name="subscription_articles",
                                    help_text=_("Asset Fédéré. Obligatoire pour cashless, adhésion ou badgeuse."),
                                    verbose_name=_("Asset Fédéré. Obligatoire pour cashless, adhésion ou badgeuse."),
                                    )

    NA, YEAR, MONTH, DAY, HOUR, CIVIL = 'N', 'Y', 'M', 'D', 'H', 'C'
    SUB_CHOICES = [
        (NA, _('Non applicable')),
        (YEAR, _("365 Jours")),
        (MONTH, _('30 Jours')),
        (DAY, _('1 Jour')),
        (HOUR, _('1 Heure')),
        (CIVIL, _('Civile')),
    ]

    subscription_type = models.CharField(max_length=1,
                                         choices=SUB_CHOICES,
                                         default=NA,
                                         verbose_name=_("durée d'abonnement"),
                                         )

    # def derniere_vente(self, carte=None):
    #     return ArticleVendu.objects.filter(
    #         carte=carte,
    #         article=self,
    #     )

    def url_image(self):
        if self.image:
            # oui, thumbnail existe bien !
            # noinspection PyUnresolvedReferences
            return self.image.thumbnail.url
        else:
            return None

    # Utilisé par le front pour connaitre le comportement de l'article
    # TODO: Changer sur le front le nom des variables pour correspondre à la nouvelle nomenclature (methode_choices)
    def methode_name(self):
        MAP_EX_METHODES_CHOICES = {
            self.VENTE: "VenteArticle",
            self.RECHARGE_EUROS: "AjoutMonnaieVirtuelle",
            # self.RECHARGE_EUROS_FEDERE: "AjoutMonnaieVirtuelle",
            self.RECHARGE_CADEAU: "AjoutMonnaieVirtuelleCadeau",
            self.ADHESIONS: "Adhesion",
            self.RETOUR_CONSIGNE: "RetourConsigne",
            self.VIDER_CARTE: "ViderCarte",
            self.VOID_CARTE: "ViderCarte",
            # self.BILLET: self.BILLET, #TODO: pour l'imprimante géré par le client
            self.BADGEUSE: self.BADGEUSE,
            # self.FIDELITY: self.FIDELITY,
        }
        if MAP_EX_METHODES_CHOICES.get(self.methode_choices):
            return MAP_EX_METHODES_CHOICES[self.methode_choices]
        elif self.methode:
            return self.methode.name
        else:
            logger.error(_(f"Pas de methode pour {self.name}"))
            return ""

    def methode_tuple_name(self):
        for tuple in self.METHODES_CHOICES:
            if tuple[0] == self.methode_choices:
                return tuple[1]
        return None


    def __str__(self):
        if self.methode_choices == self.RECHARGE_EUROS:
            pre_name = "Refill"
            if settings.LANGUAGE_CODE == 'fr':
                pre_name = "Recharge"
            return f"{pre_name} {self.name}"
        return self.name

    class Meta:
        ordering = ('poid_liste', 'methode', 'categorie',)
        verbose_name = _('article')
        verbose_name_plural = _('Articles et tarifs')


# noinspection PyUnusedLocal
@receiver(post_save, sender=Articles)
def article_trigger(sender, instance: Articles, created, **kwargs):
    """
    met par default la methode Vente Article lors de la création dans la page admin
    """
    if created:
        if not instance.methode:
            vente_article, created = Methode.objects.get_or_create(
                name="VenteArticle")
            instance.methode = vente_article

        # poids d'apparition
        if instance.poid_liste == 0:
            instance.poid_liste = len(Articles.objects.all()) + 1

        instance.save()

    if instance.archive:
        for pdv in instance.points_de_ventes.all():
            pdv.articles.remove(instance)


class Wallet(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=True)


class Place(models.Model):
    # Fedow place
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    wallet = models.OneToOneField(Wallet, on_delete=models.PROTECT, related_name='place')
    name = models.CharField(db_index=True, max_length=30, verbose_name=_("Nom"), unique=True)
    dokos_id = models.CharField(max_length=50, blank=True, null=True)
    stripe_connect_valid = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Origin(models.Model):
    place = models.ForeignKey(Place, on_delete=models.PROTECT, related_name='origins', null=True, blank=True)
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

    def __str__(self):
        if self.place:
            return f"{self.place.name} - {self.generation}"
        return f"?? {self.generation}"




class MoyenPaiement(models.Model):
    """
    Devrait s'appeller ASSET (monnaie)
    Et Asset devrait s'appeller Wallet (portefeuille du client)
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=True)
    name = models.CharField(db_index=True, max_length=100, unique=True)
    currency_code = models.CharField(max_length=3, null=True, blank=True)

    blockchain = models.BooleanField(default=False)
    is_federated = models.BooleanField(default=False)
    ardoise = models.BooleanField(default=False)
    cadeau = models.BooleanField(default=False)
    place_origin = models.ForeignKey(Place, on_delete=models.SET_NULL, related_name='moyen_paiements', null=True,
                                     blank=True)

    # Cashless
    LOCAL_EURO = 'LE'
    LOCAL_GIFT = 'LG'
    EXTERIEUR_FED = 'XE'
    EXTERIEUR_GIFT = 'XG'

    # Classics
    CASH = 'CA'
    CREDIT_CARD_NOFED = 'CC'
    CHEQUE = 'CH'
    FREE = 'NA'

    # Methode special
    FRACTIONNE = 'FR'
    COMMANDE = "CM"
    ARDOISE = 'AR'

    # Online
    STRIPE_FED = 'SF' # Paimeent vers le compte stripe principal
    STRIPE_NOFED = 'SN' # Paiement direct vers le compte stripe connect
    FEDOW = 'FD'

    # Assets with special method
    OCECO = 'OC'
    BADGE = 'BG'
    EXTERNAL_BADGE = 'XB'
    TIME = 'TP'
    EXTERNAL_TIME = 'XT'
    ADHESION = 'AD'
    MEMBERSHIP = 'MS'
    EXTERNAL_MEMBERSHIP = 'XM'
    FIDELITY = 'FI'
    EXTERNAL_FIDELITY = 'XF'

    CATEGORIES = [
        # Cashless
        (LOCAL_EURO, _('Token local')),
        (LOCAL_GIFT, _('Token cadeau')),
        (EXTERIEUR_FED, _('Token exterieur')),
        (EXTERIEUR_GIFT, _('Token exterieur cadeau')),
        (FEDOW, _('Fedow')),

        (CASH, _('Espèces')),
        (CREDIT_CARD_NOFED, _('Carte bancaire')),
        (CHEQUE, _('Chèque')),
        (FREE, _('Offert')),

        (FRACTIONNE, _('Fractionné')),
        (COMMANDE, _('Commande')),
        (ARDOISE, _('Ardoise')),

        (STRIPE_NOFED, _('Stripe')),
        (STRIPE_FED, _('Token fédéré')),

        (OCECO, _('Oceco')),
        (BADGE, _('Badgeuse')),
        (EXTERNAL_BADGE, _('Badgeuse fédérée')),
        (TIME, _('Temps')),
        (EXTERNAL_TIME, _('Temps fédéré')),
        (ADHESION, _('Adhésion associative')),
        (MEMBERSHIP, _('Abonnement')),
        (EXTERNAL_MEMBERSHIP, _('Abonnement fédéré')),
        (FIDELITY, _('Points de fidélité')),
        (EXTERNAL_FIDELITY, _('Points de fidélité fédérés')),
    ]

    # Toute les catégories doivent être unique, sauf une : Exterieur Fed
    # On ne peut pas avoir deux monnaies avec la même catégorie
    categorie = models.CharField(
        max_length=2,
        choices=CATEGORIES,
        default=LOCAL_EURO,
        # unique=True,
    )

    @staticmethod
    def sort_assets(assets):
        # sort asset par importance
        list_prio = [
            MoyenPaiement.LOCAL_GIFT,
            MoyenPaiement.LOCAL_EURO,
            MoyenPaiement.STRIPE_FED,
        ]

        if os.environ.get('EXT_FED_PRIO') == "1":
            list_prio = [
                MoyenPaiement.LOCAL_GIFT,
                MoyenPaiement.EXTERIEUR_FED,
                MoyenPaiement.LOCAL_EURO,
                MoyenPaiement.STRIPE_FED,
            ]

        def asset_key(asset):
            try:
                return list_prio.index(asset.monnaie.categorie)
            except ValueError:
                # Si la catégorie n'est pas dans list_prio, retourner un grand nombre
                return len(list_prio) + 1

        return sorted(assets, key=asset_key)

    @classmethod
    def get_local_euro(cls) -> 'MoyenPaiement':
        if cache.get('mp_local_euro'):
            return cache.get('mp_local_euro')
        mp_local_euro = cls.objects.get(categorie=cls.LOCAL_EURO)
        cache.set('mp_local_euro', mp_local_euro, None)
        return mp_local_euro

    @classmethod
    def get_local_gift(cls) -> 'MoyenPaiement':
        if cache.get('mp_local_gift'):
            return cache.get('mp_local_gift')
        mp_local_gift = cls.objects.get(categorie=cls.LOCAL_GIFT)
        cache.set('mp_local_gift', mp_local_gift, None)
        return mp_local_gift

    @staticmethod
    def fedow_asset_category_to_moyen_paiement_category(fedow_category):
        # Fedow utilise une autre nomenclature, on fait la lisaison
        fedow_category_map = {
            'FED': MoyenPaiement.STRIPE_FED,
            'TLF': MoyenPaiement.EXTERIEUR_FED,
            'TNF': MoyenPaiement.EXTERIEUR_GIFT,
            'TIM': MoyenPaiement.TIME,
            'BDG': MoyenPaiement.EXTERNAL_BADGE,
            'SUB': MoyenPaiement.EXTERNAL_MEMBERSHIP,
            'FID': MoyenPaiement.EXTERNAL_FIDELITY,
        }

        return fedow_category_map.get(fedow_category)

    def get_currency_code(self):
        return self.currency_code if self.currency_code else f"{self.name[:2]}{self.categorie[1:]}".upper()

    def fedow_category(self):
        self_category_map = {
            MoyenPaiement.LOCAL_EURO: 'TLF',
            MoyenPaiement.LOCAL_GIFT: 'TNF',
            MoyenPaiement.FIDELITY: 'FID',
            MoyenPaiement.BADGE: 'BDG',
        }
        return self_category_map.get(self.categorie, None)

    def total_tokens(self):
        try:
            return Assets.objects.filter(monnaie=self).aggregate(Sum('qty'))['qty__sum']
        except:
            return 0

    # def save(self, *args, **kwargs):

    # Le nom du token est dans les variables d'environnemnts.
    # On change si besoin pour que ça soit plus joli sur les rapports.
    def _get_FIELD_display(self, field):
        if getattr(self, field.attname) == self.FEDOW:
            return _(f"{self.name} (Fédéré)")
        elif self.name:
            return self.name

        return super()._get_FIELD_display(field)

    def __str__(self):
        if self.categorie == self.FEDOW:
            return _(f"{self.name} (Fédéré)")
        elif self.name:
            return self.name
        return self.get_categorie_display()



class CarteCashless(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )

    tag_id = models.CharField(
        db_index=True,
        max_length=8,
        unique=True,
        verbose_name="RFID TagID (8)"
    )

    uuid_qrcode = models.UUIDField(
        blank=True, null=True,
        verbose_name=_('uuid4 pour QrCode'),
        help_text=_("Non obligatoire lors de la création, il sera généré aléatoirement si non rempli.")
    )

    number = models.CharField(
        db_index=True,
        max_length=8,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Numéro imprimé"),
        help_text=_("Non obligatoire lors de la création, il sera généré aléatoirement si non rempli.")
    )

    origin = models.ForeignKey(Origin, on_delete=models.SET_NULL, related_name='cards', blank=True, null=True)

    def generation(self):
        if self.origin:
            return self.origin.generation
        return 1

    # En référence au wallet FEDOW
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='cards', blank=True, null=True)

    membre = models.ForeignKey(Membre, blank=True, null=True,
                               on_delete=models.SET_NULL,
                               related_name="CarteCashless_Membre")

    def email(self):
        if self.membre:
            return self.membre.email
        return None

    adhesion_suspendue = models.BooleanField(default=False)

    NON, CB, ESPECE, FREE = 'N', 'A', 'C', 'F'
    SUSPENDU_CHOICES = [
        (NON, _('Aucune')),
        (CB, _('Carte Bancaire')),
        (ESPECE, _('Espèce')),
        (FREE, _('Gratuit')),
    ]
    adhesion_suspendue_paiement = models.CharField(
        max_length=1, choices=SUSPENDU_CHOICES, default=NON)

    recharge_suspendue = models.BooleanField(default=False)

    def numero(self):
        return str(self.number)[:8].upper()

    def portefeuille(self):
        assets_string = " \n ".join(
            [f"{asset.qty} {asset.monnaie.name}" for asset in self.assets.all()])
        return assets_string

    def membre_name(self):
        if self.membre:
            if self.membre.pseudo:
                return self.membre.pseudo
            else:
                return self.membre.name

        else:
            return "---"

    def get_payment_assets(self, monnaies_acceptees=None):
        if not monnaies_acceptees:
            config = Configuration.get_solo()
            monnaies_acceptees = config.monnaies_acceptes.all()

        return self.assets.filter(monnaie__in=monnaies_acceptees).exclude(monnaie__categorie__in=[
            # Uniquement les asset pour payer
            MoyenPaiement.BADGE,
            MoyenPaiement.EXTERNAL_BADGE,
            MoyenPaiement.ADHESION,
            MoyenPaiement.MEMBERSHIP,
            MoyenPaiement.EXTERNAL_MEMBERSHIP,
            # au cas ou des complementaires trainent
            MoyenPaiement.CASH,
            MoyenPaiement.CREDIT_CARD_NOFED,
            MoyenPaiement.CHEQUE,
        ])

    def total_monnaie(self, assets=None):
        if not assets:
            assets = self.get_payment_assets()
        return assets.aggregate(Sum('qty')).get('qty__sum') or 0

    def get_wallet(self):
        return self.wallet

    def get_local_euro(self):
        try:
            return self.assets.get(monnaie=MoyenPaiement.get_local_euro())
        except Assets.DoesNotExist:
            asset, created = self.assets.get_or_create(monnaie=MoyenPaiement.get_local_euro())
            return asset

    def get_local_gift(self):
        try:
            return self.assets.get(monnaie=MoyenPaiement.get_local_gift())
        except Assets.DoesNotExist:
            asset, created = self.assets.get_or_create(monnaie=MoyenPaiement.get_local_gift())
            return asset

    def cotisation_membre_a_jour(self):
        if self.membre:
            if self.membre.date_derniere_cotisation:
                if self.membre.a_jour_cotisation():
                    return _("A Jour " + str(self.membre.date_derniere_cotisation.strftime('%d-%m-%Y')))
                else:
                    return _("PAS A Jour " + str(self.membre.date_derniere_cotisation.strftime('%d-%m-%Y')))
            else:
                return _("Aucune cotisation")
        elif self.adhesion_suspendue:
            return _(
                "Adhésion suspendue. Merci de créer la fiche membre via l'administraion ou en scannant le QRCode au dos de la carte.")
        else:
            return _("Carte Anonyme")

    def cotisation_membre_a_jour_booleen(self):
        if self.membre:
            if self.membre.a_jour_cotisation():
                return True
            else:
                return False
        else:
            return False

    def url_qrcode(self):
        config = Configuration.get_solo()
        if config.billetterie_url:
            url = f"{config.billetterie_url}qr/{self.uuid_qrcode}/"
            return format_html(f"<a href='{url}'>{url}</a>")
        return self.uuid_qrcode

    def __str__(self):
        if self.number:
            return f"{self.number}"
        else:
            return f"{self.tag_id}"

    class Meta:
        ordering = ('number',)
        verbose_name = _('Carte cashless')
        verbose_name_plural = _('Cartes cashless')


class Assets(models.Model):
    # Devrait s'appeller TOKEN pour faire référence à FEDOW
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    carte = models.ForeignKey(
        CarteCashless, related_name='assets', on_delete=models.PROTECT)

    last_date_used = models.DateTimeField(auto_now=True)

    is_sync = models.BooleanField(default=True)

    monnaie = models.ForeignKey(MoyenPaiement, on_delete=models.PROTECT)

    def monnaie_name(self):
        return self.monnaie.name

    def categorie(self):
        return self.monnaie.categorie

    def membre(self):
        if self.carte.membre:
            return self.carte.membre
        else:
            return ""

    # def a_jour_cotisation(self):
    # if calcul_adh == Configuration.ADH_365JOURS:
    #     return timezone.now().date() <= (self.date_derniere_cotisation + timedelta(days=365))
    #
    # elif calcul_adh == Configuration.ADH_CIVILE:
    #     return timezone.now().date().year == self.date_derniere_cotisation.year
    #
    # elif calcul_adh == Configuration.ADH_GLISSANTE_OCT:
    #     if timezone.now().date().year == (self.date_derniere_cotisation.year + 1):
    #         if self.date_derniere_cotisation.month >= 10:
    #             return True
    #     return timezone.now().date().year == self.date_derniere_cotisation.year

    class Meta:
        unique_together = [['monnaie', 'carte']]
        verbose_name = _('Asset')
        verbose_name_plural = _('Portefeuilles')

    def __str__(self):
        return f'{self.monnaie.name}, {self.qty}'


class CarteMaitresse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    carte = models.ForeignKey(CarteCashless,
                              related_name='cartes_maitresses',
                              help_text=_("Seul les cartes avec membres sont listées ici."),
                              on_delete=models.CASCADE,
                              unique=True)

    points_de_vente = models.ManyToManyField(PointDeVente,
                                             verbose_name=_("Point de vente"),
                                             related_name='cartes_maitresses')

    datetime = models.DateTimeField(auto_now=True,
                                    null=True,
                                    verbose_name=_('Mise a jour le'))

    edit_mode = models.BooleanField(default=False, verbose_name=_("Mode gérant.e"))

    # noinspection PyBroadException
    def __str__(self):
        if self.carte.membre:
            return f"{(self.carte.membre.prenom if self.carte.membre.prenom else '')} {self.carte.membre.name}"
        return "No member linked"

    def points_de_ventes(self):
        return ", ".join([pdv["name"] for pdv in self.points_de_vente.values('name')])

    def membre(self):
        if self.carte.membre:
            return f"{(self.carte.membre.prenom if self.carte.membre.prenom else '')} {self.carte.membre.name}"
        return "No member linked"

    class Meta:
        verbose_name = _('Carte primaire')
        verbose_name_plural = _('Cartes primaires')


'''
GESTION PANIER RESTAURATION
'''


class CategorieTable(models.Model):
    name = models.CharField(max_length=20, unique=True)
    icon = models.CharField(max_length=30, blank=True,
                            null=True, choices=FONT_ICONS_CHOICES)

    def __str__(self):
        return self.name


class Table(models.Model):
    name = models.CharField(max_length=50, unique=True)
    poids = models.PositiveSmallIntegerField(default=0,
                                             verbose_name="Poids")
    categorie = models.ForeignKey(CategorieTable,
                                  blank=True, null=True,
                                  on_delete=models.SET_NULL)

    # pour le futur, affichage pour le css :
    position_top = models.PositiveSmallIntegerField(default=0)
    position_left = models.PositiveSmallIntegerField(default=0)

    LIBRE, EN_COURS, SERVIE = 'L', 'O', 'S'
    TYPE_STATUT = [
        (LIBRE, _('Libre')),
        (EN_COURS, _('Occupée')),
    ]
    statut = models.CharField(max_length=1, choices=TYPE_STATUT, default=LIBRE)

    ephemere = models.BooleanField(default=False)
    archive = models.BooleanField(default=False)

    def check_status(self):
        commandes_ni_servie_ni_payee = self.commandes \
            .exclude(statut=CommandeSauvegarde.SERVIE_PAYEE) \
            .exclude(statut=CommandeSauvegarde.ANNULEE)
        if commandes_ni_servie_ni_payee.count() == 0:
            self.statut = Table.LIBRE  # table libre
            self.save()
        else:
            self.statut = Table.EN_COURS  # pas d'ouverte, tout est servi !
            self.save()

    def reste_a_payer(self):
        reste_a_payer = 0
        for commande in self.commandes \
                .exclude(statut=CommandeSauvegarde.ANNULEE) \
                .exclude(statut=CommandeSauvegarde.SERVIE_PAYEE) \
                .exclude(statut=CommandeSauvegarde.PAYEE):
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
def incrementation_du_poids_table(sender, instance, **kwargs):
    if instance.poids == 0:
        instance.poids = len(Table.objects.all()) + 1


class CommandeSauvegarde(models.Model):
    service = models.UUIDField(default=uuid4)

    uuid = models.UUIDField(primary_key=True,
                            default=uuid4,
                            editable=False)

    responsable = models.ForeignKey(Membre,
                                    on_delete=models.SET_NULL,
                                    null=True)

    table = models.ForeignKey(Table,
                              on_delete=models.SET_NULL,
                              related_name="commandes",
                              null=True)

    datetime = models.DateTimeField(auto_now_add=True)

    numero_du_ticket_imprime = JSONField(default=dict)

    OUVERTE, SERVIE, PAYEE, SERVIE_PAYEE, ANNULEE = "O", "S", "P", "SP", "CA"
    TYPE_STATUT = [
        (OUVERTE, _('Ouverte')),
        (SERVIE, _('Servie')),
        (PAYEE, _('Payée')),
        (SERVIE_PAYEE, _('Servie et payée')),
        (ANNULEE, _('Annulée')),
    ]
    statut = models.CharField(
        max_length=2, choices=TYPE_STATUT, default=OUVERTE)

    commentaire = models.TextField(blank=True, null=True)

    archive = models.BooleanField(default=False)

    def responsable_name(self):
        if self.responsable:
            return self.responsable.name
        return ""

    def table_name(self):
        if self.table:
            return self.table.name
        else:
            return " - "

    def liste_articles(self):
        return " - ".join(
            [f"{int(articles.qty)}/{int(articles.reste_a_servir)}/{int(articles.reste_a_payer)} {articles.article.name}"
             for articles in self.articles.all()])

    def reste_a_payer(self):
        total_reste = 0
        for article in self.articles \
                .exclude(statut=ArticleCommandeSauvegarde.PAYES) \
                .exclude(statut=ArticleCommandeSauvegarde.SERVIS_PAYES) \
                .exclude(statut=ArticleCommandeSauvegarde.ANNULES):
            total_reste += article.reste_a_payer * article.article.prix

        return total_reste

    def id_commande(self):
        return str(self.uuid).split('-')[0]

    def id_service(self):
        return str(self.service).split('-')[0]

    def __str__(self):
        return (f"{str(self.uuid).split('-')[0]}")

    def check_statut(self):
        articles = self.articles.all()
        article_non_payees = articles.exclude(reste_a_payer=0).count()
        article_non_servis = articles.exclude(reste_a_servir=0).count()

        if article_non_payees == 0 and article_non_servis == 0:
            if self.statut != CommandeSauvegarde.SERVIE_PAYEE:
                self.statut = CommandeSauvegarde.SERVIE_PAYEE
                self.save()

        elif article_non_payees == 0:
            if self.statut != CommandeSauvegarde.PAYEE:
                self.statut = CommandeSauvegarde.PAYEE
                self.save()

        elif article_non_servis == 0:
            if self.statut != CommandeSauvegarde.SERVIE:
                self.statut = CommandeSauvegarde.SERVIE
                self.save()

    class Meta:
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")
        ordering = ("-datetime",)


# noinspection PyPep8Naming,PyUnusedLocal
@receiver(post_save, sender=CommandeSauvegarde)
def statut_table_from_commande(sender, instance: CommandeSauvegarde, created, **kwargs):
    if instance.table:
        instance.table.check_status()


class ArticleCommandeSauvegarde(models.Model):
    commande = models.ForeignKey(CommandeSauvegarde,
                                 on_delete=models.CASCADE,
                                 related_name='articles',
                                 )

    article = models.ForeignKey(Articles, on_delete=models.PROTECT)

    qty = models.DecimalField(max_digits=10, decimal_places=2)

    reste_a_payer = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    reste_a_servir = models.DecimalField(default=0, max_digits=10, decimal_places=2)

    PREPA, PRETS, SERVIS, PAYES, SERVIS_PAYES, ANNULES, OFFERT = "PP", "PR", "SV", "PY", "SP", "CA", "GF"
    TYPE_STATUT = [
        (PREPA, _('En préparation')),
        (PRETS, _('Prêt à servir')),
        (SERVIS, _('Servis')),
        (PAYES, _('Payés')),
        (SERVIS_PAYES, _('Servis et payés')),
        (ANNULES, _('Annulés')),
    ]
    statut = models.CharField(
        max_length=2, choices=TYPE_STATUT, default=PREPA)

    def table(self):
        return self.commande.table

    def __str__(self):
        return f"{self.article.name} {self.pk} {str(self.commande.uuid).split('-')[0]}"


@receiver(post_save, sender=ArticleCommandeSauvegarde)
def reste_a_check(sender, instance: ArticleCommandeSauvegarde, created, **kwargs):
    logger.info(f'--- function reste_a_check : post_save ArticleCommandeSauvegarde pour {instance}')
    # On incrémente la valeur du reste a payer lors de la création de la commande.
    # Valeur qui sera décrémentée lors du paiement.
    if created:
        logger.info(f'reste_a_check created {instance}')
        instance.reste_a_payer = instance.qty
        config = Configuration.get_solo()
        if instance.article.methode == config.methode_vente_article:
            # si l'article fait parti d'un groupement de catégorie,
            # il est dans les préparations :
            if instance.article.categorie:
                if len(instance.article.categorie.groupements.all()) > 0:
                    if config.validation_service_ecran:
                        if instance.qty > 0:
                            instance.reste_a_servir = instance.qty

        instance.save()


    elif instance.commande.statut != CommandeSauvegarde.ANNULEE:

        # Si tout a été payé et tout est servi, on passe les articles  en SERVIS_PAYES
        if instance.reste_a_payer == 0 and instance.reste_a_servir == 0 \
                and instance.statut != ArticleCommandeSauvegarde.SERVIS_PAYES:
            logger.info(f'condition pour SERVIS_PAYES {instance}')

            instance.statut = ArticleCommandeSauvegarde.SERVIS_PAYES
            instance.save()
            instance.commande.check_statut()


        # Si il reste a servir, mais que tout est payé :
        elif instance.reste_a_payer == 0 \
                and instance.statut != ArticleCommandeSauvegarde.PAYES \
                and instance.statut != ArticleCommandeSauvegarde.SERVIS_PAYES:

            # tout les articles de cette ligne sont payés,
            # on vérifie et mets à jour le status de la commande.
            logger.info(f'condition pour PAYES {instance}')
            instance.statut = ArticleCommandeSauvegarde.PAYES
            instance.save()
            instance.commande.check_statut()




        # Si tout est servi mais qu'il reste a payer :
        elif instance.reste_a_servir == 0 \
                and instance.statut != ArticleCommandeSauvegarde.SERVIS \
                and instance.statut != ArticleCommandeSauvegarde.SERVIS_PAYES:

            # Tous les articles de cette ligne sont servis,
            # on vérifie et mets à jour le status de la commande.
            logger.info(f'condition pour SERVIS {instance}')
            instance.statut = ArticleCommandeSauvegarde.SERVIS
            instance.save()
            instance.commande.check_statut()

        # Si toutes les commandes de la table sont terminées,
        # on vérifie et mets à jour le reste à payer des articles et des commandes.
        # Au cas où un paiement fractionné a été effectué.
        if instance.commande.table:
            if instance.commande.table.reste_a_payer() == 0:
                logger.info(f"Table {instance.commande.table.name} TOUT PAYEE ! {instance}")
                paiements_list = []
                paiements_fractionnes_meme_service = ArticleCommandeSauvegarde.objects.filter(
                    article__methode_choices=Articles.FRACTIONNE,
                    commande__service=instance.commande.service,
                    reste_a_payer__lt=0,
                )

                for paiement_fractionne in paiements_fractionnes_meme_service:
                    # On teste si le paiement fractionné n'a pas été divisé en deux cadeaux / euros
                    paiement_fractionne_dans_article_vendu = ArticleVendu.objects.filter(
                        article=paiement_fractionne.article,
                        commande=paiement_fractionne.commande_id,
                    )

                    if len(paiement_fractionne_dans_article_vendu) < 1:
                        raise ValueError(
                            _("Erreur lors d'un rapprochement de paiement fractionné. Aucun paiement en Db."))
                    else:
                        for article_vendu in paiement_fractionne_dans_article_vendu:
                            paiements_list.append({
                                'article_commande': paiement_fractionne,
                                'qty': abs(article_vendu.qty),
                                'article_vendu': article_vendu
                            })



                # Mise à zero du reste a payer et récupère les articles à rentrer en db
                articles_a_rentrer_en_db = {}
                for commande in instance.commande.table.commandes \
                        .exclude(statut=CommandeSauvegarde.PAYEE) \
                        .exclude(statut=CommandeSauvegarde.SERVIE_PAYEE) \
                        .exclude(statut=CommandeSauvegarde.ANNULEE):

                    for article_dans_commande in commande.articles.all():
                        if article_dans_commande.reste_a_payer != 0:
                            articles_a_rentrer_en_db[article_dans_commande] = article_dans_commande.reste_a_payer
                            article_dans_commande.reste_a_payer = 0
                            article_dans_commande.statut = article_dans_commande.PAYES
                            article_dans_commande.save()


                # On rentre en dB les articles qui n'ont pas été comptabilisés à cause du paiement fractionné.
                # Dans le but de pouvoir comptabiliser les articles vendus.

                # D'abord, nous cherchons les paiements fractionnés du même service,
                # pour savoir, entre autre quels ont été les moyens de paiements,
                # et on crée un dictionnaire avec la qty en valeur positive.

                # Enfin, nous créons le rapprochement entre les paiments fractionnés et les articles vendus.
                for article in articles_a_rentrer_en_db:
                    article: ArticleCommandeSauvegarde
                    qty_non_comptabilisee = articles_a_rentrer_en_db[article]
                    total_non_comptabilisee: Decimal = Decimal(qty_non_comptabilisee) * Decimal(article.article.prix)

                    if article.article.methode_choices == Articles.VENTE:
                        logger.info(
                            f"ON RENTRE EN DB {qty_non_comptabilisee * article.article.prix}€ {article.article.name} ")

                        for paiement in paiements_list:
                            paiement: dict
                            article_commande: ArticleCommandeSauvegarde = paiement.get('article_commande')
                            article_vendu: ArticleVendu = paiement.get('article_vendu')
                            qty: Decimal = paiement.get('qty')

                            original_article = article.article
                            categorie: Categorie = original_article.categorie
                            tva = categorie.tva.taux if categorie.tva else 0

                            # Tant que l'un des deux est > 0 :
                            while qty > 0 and qty_non_comptabilisee > 0:
                                a_encaisser = qty - total_non_comptabilisee

                                if a_encaisser >= 0:
                                    # logger.info(
                                    #     f"On peut piocher {qty}€ dans {article_vendu} "
                                    #     f": a encaisser >= 0 : {a_encaisser}")
                                    # logger.info(
                                    #     f"Boucle1 Original article : {original_article} - categorie : {categorie} "
                                    #     f"tva : {tva}")

                                    ArticleVendu.objects.create(
                                        prix_achat=original_article.prix_achat,
                                        tva=tva,
                                        article=article.article,
                                        prix=article.article.prix,
                                        qty=qty_non_comptabilisee,
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
                                    qty = a_encaisser
                                    paiement['qty'] = qty
                                    qty_non_comptabilisee = 0
                                    total_non_comptabilisee = 0


                                elif a_encaisser < 0:
                                    qty_a_encaisser = Decimal(float(qty) / float(article.article.prix))

                                    # logger.info(
                                    #     f"On peut piocher {qty}€ dans {article_vendu} : "
                                    #     f"a encaisser < 0 : {a_encaisser} - "
                                    #     f"qty_a_encaisser = {qty_a_encaisser}")
                                    # logger.info(
                                    #     f"Boucle2 Original article : {original_article} - categorie : {categorie} "
                                    #     f"tva : {tva}")

                                    ArticleVendu.objects.create(
                                        prix_achat=original_article.prix_achat,
                                        tva=tva,
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
                                    paiement['qty'] = qty


                instance.commande.check_statut()


'''
GESTION ET SUIVI DES VENTES
'''


class IpUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ip = models.GenericIPAddressField()

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return f"{self.user.username[:20]} {self.ip}"


class ArticleVendu(models.Model):
    uuid_paiement = models.UUIDField(editable=False, default=uuid4)
    uuid = models.UUIDField(default=uuid4)


    article = models.ForeignKey(Articles, on_delete=models.PROTECT)
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, null=True, blank=True)

    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    tva = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name=_("Taux"), default=0)

    qty = models.DecimalField(max_digits=12, decimal_places=6, default=0, null=True)
    pos = models.ForeignKey(PointDeVente, null=True, on_delete=models.PROTECT)

    ip_user = models.ForeignKey(IpUser, on_delete=models.PROTECT,
                                null=True, blank=True)

    commande = models.UUIDField(editable=False)

    # TODO: A renseigner dans view :
    lecteur_nfc = models.CharField(max_length=20,
                                   null=True, blank=True)

    date_time = models.DateTimeField(default=timezone.now)
    membre = models.ForeignKey(Membre,
                               null=True, blank=True,
                               on_delete=models.PROTECT)

    responsable = models.ForeignKey(Membre,
                                    null=True, blank=True,
                                    related_name='articles_vendus_responsables',
                                    on_delete=models.PROTECT)

    moyen_paiement = models.ForeignKey(MoyenPaiement,
                                       null=True, blank=True,
                                       on_delete=models.PROTECT)

    carte = models.ForeignKey(CarteCashless,
                              null=True, blank=True,
                              on_delete=models.PROTECT,
                              related_name="articles_vendus")

    table = models.ForeignKey(Table,
                              null=True, blank=True,
                              on_delete=models.SET_NULL)

    depuis_fractionne = models.BooleanField(default=False)

    # Utilisé pour les envoi vers Odoo
    comptabilise = models.BooleanField(default=False, verbose_name=_("Envoyé sur Odoo"))
    logs = models.TextField(blank=True, null=True)

    # Fedow
    sync_fedow = models.BooleanField(default=False, verbose_name="Fedow")
    hash_fedow = models.CharField(max_length=64, blank=True, null=True)

    # Commentaires
    comment = models.TextField(blank=True, null=True, verbose_name=_("Commentaire"))

    class Meta:
        ordering = ('-date_time',)
        verbose_name = _('Vente')
        verbose_name_plural = _('Ventes')

    def __str__(self):
        return f"{self.article.name} {self.prix}€"

    def total(self):
        total = dround(self.prix * self.qty)
        return total

    def cout(self):
        return dround(self.prix_achat * self.qty)

    def benefice(self):
        return dround(self.total() - self.cout())

    def id_commande(self):
        return str(self.commande).split('-')[0]

    def id_paiement(self):
        return str(self.uuid_paiement).split('-')[0]

    # def hash8_fedow(self):
    #     if self.hash_fedow:
    #         return str(self.hash_fedow)[:8]
    #     return None

    def _article(self):
        if self.depuis_fractionne or self.article.fractionne:
            return (f"{self.article.name} ({str(self.commande).split('-')[0][:3]})")
        else:
            return self.article

    def _qty(self):
        return dround(self.qty)

    def ht_from_ttc(self):
        return dround(self.prix / (1 + (self.tva / 100)))

    def tva_from_ttc(self):
        return dround(self.prix - self.ht_from_ttc())

    # Surclassage de la méthode save pour appliquer
    # les attribus relatifs à l'article parent
    # en cas de changement futur de ce dernier.
    def save(self, *args, **kwargs):

        if not self.categorie:
            if self.article.categorie:
                self.categorie = self.article.categorie
            elif self.article.methode_choices == Articles.VENTE:
                self.categorie, created = Categorie.objects.get_or_create(name="Autre")

        # On applique la TVA de la catégorie de l'article en cas de changement futur de la catégorie parent :
        if self.tva is None:
            if self.article.categorie:
                if self.article.categorie.tva:
                    self.tva = self.article.categorie.tva.taux

        # On applique le prix de l'article en cas de changement futur de l'article parent :
        if self.prix is None:
            if self.article:
                self.prix = self.article.prix

        # On applique le prix d'achat de l'article en cas de changement futur de l'article parent :
        if self.prix_achat is None:
            if self.article:
                self.prix_achat = self.article.prix_achat

        super().save(*args, **kwargs)


class InformationGenerale(models.Model):
    date = models.DateField(blank=True, null=True)
    total_monnaie_principale = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = _('information Generale')
        verbose_name_plural = _('informations Generale')


class CreditExterieur(models.Model):
    monnaie = models.ForeignKey(MoyenPaiement, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    information_generale = models.ForeignKey(InformationGenerale,
                                             on_delete=models.PROTECT,
                                             null=True, blank=True,
                                             related_name="information_generale")


# TODO: A degager lors du prochain nettoyage
class RapportArticlesVendu(models.Model):
    article = models.ForeignKey(Articles, on_delete=models.PROTECT)
    date = models.DateField()
    pos = models.ForeignKey(PointDeVente, null=True, blank=True, on_delete=models.CASCADE)
    qty = models.SmallIntegerField(default=0)

    espece = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    carte_bancaire = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("CB"))
    monnaie_principale = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Cashless"))
    mollie = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Web (mollie)")
    monnaie_principale_cadeau = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    oceco = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_benefice_estime = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def benefice_estime(self):
        if self.total_benefice_estime == 0:
            if self.article.prix_achat > 0:
                benef = (self.article.prix - self.article.prix_achat) * self.qty
                if self.date != timezone.now().date() and benef > 0:
                    logger.info(
                        f"{timezone.now()} On inscrit le calcul de benef ({benef}€) dans rapport qty vendu à l'article {self.article}")
                    self.total_benefice_estime = benef
                    self.save()
                return benef

        return self.total_benefice_estime

    class Meta:
        ordering = ('-date',)
        verbose_name = 'Quantités vendus'
        verbose_name_plural = 'Quantités vendus'


# TODO: a virer lors du prochain nettoyage
class ConfigurationsGraphique(SingletonModel):
    jours_evolution_monnaie = models.SmallIntegerField(default=10)
    jours_vente_article = models.SmallIntegerField(default=1)

    class Meta:
        verbose_name = 'Graphique du dashboard'
        verbose_name_plural = 'Graphique du dashboard'


# TODO: a virer lors du prochain nettoyage
class BoissonCoutant(models.Model):
    carte = models.ForeignKey(CarteCashless,
                              related_name='boissons_prix_coutant',
                              blank=True, null=True,
                              on_delete=models.SET_NULL)

    nbr_boisson = models.IntegerField(default=0)

    date = models.DateField(blank=True, null=True)

    class Meta(object):
        ordering = ('-date',)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.nbr_boisson)


class Odoologs(models.Model):
    date = models.DateTimeField(auto_now_add=True, editable=False)
    log = models.CharField(max_length=500)


class ClotureCaisse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    datetime = models.DateTimeField(auto_now_add=True, verbose_name=_("Généré le"))
    start = models.DateTimeField(verbose_name=_("Début"))
    end = models.DateTimeField(verbose_name=_("Fin"))

    # Enregistrement dans le dur du tableau qui a été généré.
    ticketZ = JSONField(default=dict, max_length=50000)

    CUSTOM, POS, CLOTURE, HEBDOMADAIRE, MENSUEL, ANNUEL = 'K', 'P', 'C', 'H', 'M', 'A'
    CAT_CHOICES = [
        (CUSTOM, _('Custom')),
        (POS, _("Cloture d'un point de vente")),
        (CLOTURE, _('Cloture de toutes caisses')),
        (HEBDOMADAIRE, _('Rapport hebdomadaire')),
        (MENSUEL, _('Rapport mensuel')),
        (ANNUEL, _('Rapport annuel')),
    ]
    categorie = models.CharField(max_length=1, choices=CAT_CHOICES, default=CLOTURE)

    def chiffre_affaire(self):
        return json.loads(self.ticketZ).get('total_TTC')

    def uuid_8(self):
        return str(self.id)[:8]

    class Meta:
        ordering = ('-datetime',)
        verbose_name = _("Cloture de caisse")
        verbose_name_plural = _("Clotures de caisse")


class Configuration(SingletonModel):
    ''' GENERAL '''

    structure = models.CharField(max_length=50,
                                 null=True, blank=True,
                                 verbose_name=_("Nom de la structure"),
                                 )
    url_image = models.URLField(null=True, blank=True)

    siret = models.CharField(max_length=20,
                             null=True, blank=True)

    adresse = models.CharField(max_length=500,
                               null=True, blank=True)

    pied_ticket = models.TextField(null=True, blank=True)

    telephone = models.CharField(max_length=20, null=True, blank=True)

    email = models.EmailField(null=True, blank=True)

    numero_tva = models.CharField(max_length=20, null=True, blank=True)

    taux_tva = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    prix_adhesion = models.SmallIntegerField(default=0, verbose_name=_("Prix de l'adhésion par default"))

    ADH_365JOURS, ADH_CIVILE, ADH_GLISSANTE_OCT = "J", "C", "G"
    ADH_CHOICES = [
        (ADH_365JOURS, _('365 Jours')),
        (ADH_CIVILE, _('31 Decembre')),
        (ADH_GLISSANTE_OCT, _("Année glissante : Octobre -> Decembre +1")),
    ]

    calcul_adhesion = models.CharField(default="J",
                                       max_length=1,
                                       choices=ADH_CHOICES,
                                       verbose_name=_("Durée d'adhésion"))

    horaire_ouverture = models.TimeField(null=True, blank=True)
    horaire_fermeture = models.TimeField(null=True, blank=True)

    # TODO: utiliser settings.TIME_ZONE
    TZ_REUNION, TZ_PARIS = "Indian/Reunion", "Europe/Paris"
    TZ_CHOICES = [
        (TZ_REUNION, _('Indian/Reunion')),
        (TZ_PARIS, _('Europe/Paris')),
    ]

    fuseau_horaire = models.CharField(default=TZ_REUNION,
                                      max_length=50,
                                      choices=TZ_CHOICES,
                                      )

    def timezone(self):
        return settings.TIME_ZONE

    def language(self):
        return settings.LANGUAGE_CODE

    '''configuration des moyens de paiements par default'''

    monnaie_principale = models.OneToOneField(MoyenPaiement, verbose_name=_("Monnaie Principale"),
                                              related_name='configuration_monnaie_principale',
                                              null=True, blank=True,
                                              on_delete=models.PROTECT)

    monnaie_principale_cadeau = models.OneToOneField(MoyenPaiement, verbose_name=_("Monnaie Principale Cadeau"),
                                                     related_name='configuration_monnaie_principale_cadeau',
                                                     null=True, blank=True,
                                                     on_delete=models.PROTECT)

    monnaie_principale_ardoise = models.OneToOneField(MoyenPaiement, verbose_name=_("Monnaie Principale Ardoise"),
                                                      related_name='configuration_monnaie_principale_ardoise',
                                                      null=True,
                                                      blank=True,
                                                      on_delete=models.PROTECT)

    moyen_paiement_espece = models.OneToOneField(MoyenPaiement, on_delete=models.PROTECT,
                                                 related_name='configuration_espece',
                                                 null=True)

    moyen_paiement_cb = models.OneToOneField(MoyenPaiement, on_delete=models.PROTECT,
                                             related_name='configuration_cb',
                                             null=True)

    moyen_paiement_mollie = models.OneToOneField(MoyenPaiement, on_delete=models.PROTECT,
                                                 related_name='configuration_mollie',
                                                 null=True)

    moyen_paiement_oceco = models.OneToOneField(MoyenPaiement, on_delete=models.PROTECT,
                                                related_name='configuration_oceco',
                                                null=True)

    moyen_paiement_commande = models.OneToOneField(MoyenPaiement, on_delete=models.PROTECT,
                                                   related_name='configuration_commande',
                                                   null=True)

    moyen_paiement_fractionne = models.OneToOneField(MoyenPaiement, on_delete=models.PROTECT,
                                                     related_name='configuration_fractionne',
                                                     null=True)

    monnaies_acceptes = models.ManyToManyField(MoyenPaiement,
                                               verbose_name=_("Assets acceptés pour ventes"),
                                               related_name="configuration_monnaies_acceptees",
                                               blank=True)

    # TODO: a virer, pas utilisé
    emplacement = models.CharField(max_length=50,
                                   null=True, blank=True)

    '''configuration methode'''

    methode_vente_article = models.OneToOneField(Methode, on_delete=models.PROTECT,
                                                 related_name='configuration_vente_article',
                                                 null=True)

    methode_ajout_monnaie_virtuelle = models.OneToOneField(Methode, on_delete=models.PROTECT,
                                                           related_name='configuration_ajout_monnaie_virtuelle',
                                                           null=True)

    methode_ajout_monnaie_virtuelle_cadeau = models.OneToOneField(
        Methode,
        on_delete=models.PROTECT,
        related_name='configuration_ajout_monnaie_virtuelle_cadeau',
        null=True)

    methode_paiement_fractionne = models.OneToOneField(Methode, on_delete=models.CASCADE,
                                                       related_name='configuration_fractionne',
                                                       null=True)

    methode_adhesion = models.OneToOneField(Methode,
                                            on_delete=models.PROTECT,
                                            related_name='configuration_adhesion',
                                            null=True)

    methode_retour_consigne = models.OneToOneField(Methode,
                                                   on_delete=models.PROTECT,
                                                   related_name='configuration_retour_consigne',
                                                   null=True)

    methode_vider_carte = models.OneToOneField(Methode,
                                               on_delete=models.PROTECT,
                                               related_name='configuration_vider_carte',
                                               null=True)

    '''
    OPTIONS & COMPORTEMENT
    '''

    # Si False, aucun nouvel utilisateur ( donc interface front ) ne peut se logger.
    # appareillement = models.BooleanField(default=False)
    # pin_code_primary_link = models.CharField(max_length=8, null=True, blank=True, editable=False,
    #                                          verbose_name=_("Code PIN pour appareillement"))

    # Si True, les plats commandés sont en état servi.
    validation_service_ecran = models.BooleanField(default=False,
                                                   verbose_name=_(
                                                       "Validation manuelle de la préparation sur ecran tactile"))

    remboursement_auto_annulation = models.BooleanField(default=False,
                                                        verbose_name=_(
                                                            "Si annulation d'un article déja payé par cashless, on rembourse automatiquement sur la carte"))

    domaine_cashless = models.URLField(verbose_name=_("Url publique du serveur cashless"), blank=True, null=True)
    ip_cashless = models.GenericIPAddressField(blank=True, null=True, verbose_name=_("IP publique du serveur cashless"))

    adhesion_suspendue = models.BooleanField(default=False,
                                             help_text="Adhésion possible sur carte sans membre. Au prix par default dès que la fiche membre est renseignée.")

    void_card = models.BooleanField(default=True, verbose_name=_("Séparer l'utilisateur lors du vider carte"),
                                    help_text=_("Si coché, la carte vidée redeviendra neuve. Sinon, la carte garde toujours le portefeuille de l'utilisateur pour par exemple ses adhésions."))

    '''
    OCECO API KEY
    '''

    valeur_oceco = models.DecimalField(max_digits=10, decimal_places=2, default=2)

    revoquer = models.BooleanField(
        default=False,
        verbose_name=_('Créer / Révoquer'),
        help_text=_(
            "Selectionnez et validez pour générer ou supprimer une clé API. La clé ne sera affiché qu'a la création, notez la bien !")
    )

    key = models.OneToOneField(APIKey,
                               on_delete=models.CASCADE,
                               blank=True, null=True,
                               related_name="oceco"
                               )

    oceco_ip_white_list = models.GenericIPAddressField(
        verbose_name=_("Ip serveur oceco"),
        blank=True, null=True
    )

    '''
    API BILLETTERIE
    '''

    key_billetterie = models.OneToOneField(APIKey,
                                           on_delete=models.CASCADE,
                                           blank=True, null=True,
                                           related_name="billetterie",
                                           )

    revoquer_key_billetterie = models.BooleanField(
        default=False,
        verbose_name=_('Créer / Révoquer'),
        help_text=_("Selectionnez et validez pour générer ou supprimer une clé API. "
                    "La clé ne sera affiché qu'a la création, notez la bien !")
    )

    billetterie_ip_white_list = models.GenericIPAddressField(
        verbose_name=_("Ip serveur Billetterie"),
        blank=True, null=True
    )

    billetterie_url = models.URLField(
        verbose_name=_("Url du serveur SaaS"),
        default="https://www.tibillet.re/"
    )

    '''
    CASHBACK
    '''

    cashback_active = models.BooleanField(default=False,
                                          verbose_name=_("Activez le cashbash pour les rechargements cashless"))
    cashback_start = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                         help_text=_(
                                             "Valeur du rechargement à partir de laquelle les cadeaux s'enclenchent"))
    cashback_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                         help_text=_("Valeur donnée en monnaie cadeau"))

    '''
    FIDELITY
    '''

    fidelity_active = models.BooleanField(default=False,
                                          verbose_name=_("Incrémentez des points de fidélité pour chaque achat."))
    fidelity_asset_trigger = models.ManyToManyField('MoyenPaiement', related_name='fidelity_asset_trigger',
                                                    blank=True,
                                                    verbose_name=_(
                                                        "Asset déclencheur de l'incrémentation des points de fidélité"))
    fidelity_asset = models.ForeignKey('MoyenPaiement', on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name=_("Asset de fidélité"))
    fidelity_factor = models.DecimalField(max_digits=4, decimal_places=2, default=1,
                                          verbose_name=_("Facteur de point."),
                                          help_text=_("10€ de vente X facteur = X*10 points de fidélité."))

    '''
    ODOO
    '''

    odoo_send_membership = models.BooleanField(default=False,
                                               verbose_name=_("Envoyer les adhésions vers Odoo"))

    odoo_url = models.URLField(
        verbose_name=_("Url du serveur odoo"),
        blank=True, null=True
    )

    odoo_database = models.CharField(
        max_length=30,
        blank=True, null=True
    )

    odoo_login = models.CharField(
        max_length=200,
        blank=True, null=True
    )

    odoo_api_key = models.CharField(
        max_length=200,
        blank=True, null=True
    )

    revoquer_odoo_api_key = models.BooleanField(
        default=False,
        verbose_name=_('Révoquer la clé API'),
        help_text=_("Selectionnez et validez pour supprimer la clé API et entrer une nouvelle.")
    )

    def _odoo_api_key(self):
        if self.odoo_api_key:
            return f"{self.odoo_api_key[:3]}{'*' * (len(self.odoo_api_key) - 3)}"
        else:
            return None

    odoo_create_invoice_membership = models.BooleanField(default=True,
                                                         verbose_name=_("Créer les facture pour chaque adhésion"))
    odoo_set_payment_auto = models.BooleanField(default=False,
                                                verbose_name=_("Valider le paiement automatiquement"))

    journal_out_invoice = models.CharField(
        max_length=200,
        blank=True, null=True,
        verbose_name=_("Nom du journal Facture Client")
    )

    journal_odoo_espece = models.CharField(
        max_length=200,
        blank=True, null=True,
        verbose_name=_("Nom du journal Espèce")
    )

    journal_odoo_cb = models.CharField(
        max_length=200,
        blank=True, null=True,
        verbose_name=_("Nom du journal Carte Bancaire")
    )

    journal_odoo_stripe = models.CharField(
        max_length=200,
        blank=True, null=True,
        verbose_name=_("Nom du journal Stripe")
    )

    def last_log_odoo(self):
        if Odoologs.objects.last():
            return Odoologs.objects.last().log

    def monnaies_acceptes_str(self):
        return ", ".join([f'{monnaie}' for monnaie in self.monnaies_acceptes.all()])

    '''
    TicketZ
    '''

    cash_float = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Fond de caisse par défaut"))
    ticketZ_printer = models.ForeignKey(Printer, on_delete=models.SET_NULL, blank=True, null=True)
    compta_email = models.EmailField(blank=True, null=True, verbose_name=_("Email de la compta."),
                                     help_text=_(
                                         "Email de la compta. Envoie des rapports de la veille en pdf tout les matins."))
    cloture_de_caisse_auto = models.TimeField(blank=True, null=True,
                                              verbose_name=_("Heure de cloture automatique de toutes les caisses"),
                                              default=time(4, 0))

    '''
    BADGEUSE DOKOS
    '''
    dokos_url = models.URLField(blank=True, null=True, verbose_name=_("Url du serveur Dokos"),
                                help_text=_("ex: http://demobadge.dokos.cloud/"))
    dokos_key = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("Clé API Dokos"),
                                 help_text=_("Format pub_key:priv_key"))
    dokos_id = models.CharField(max_length=200, blank=True, null=True,
                                verbose_name=_("Id du lieu Dokos (client_venue)"))

    revoquer_dokos = models.BooleanField(default=False,
                                         verbose_name=_('Révoquer la clé Dokos'),
                                         help_text=_(
                                             "Selectionnez et validez pour supprimer la clé API et entrer une nouvelle."))

    def _cle_dokos(self):
        if self.dokos_key:
            return f"***"
        return None

    '''
    DISCOVERY SERVER
    '''
    # Serveur pour découverte de nouveaux terminaux android ou pi
    discovery_key = models.CharField(max_length=200, blank=True, null=True,
                                     verbose_name=_("Clé API Serveur de découverte"), editable=False)

    def set_discovery_key(self, key):
        self.discovery_key = fernet_encrypt(key)
        self.save()

    def get_discovery_key(self):
        return fernet_decrypt(self.discovery_key)

    '''
    FEDOW
    '''
    string_connect = models.CharField(max_length=500, blank=True, null=True,
                                      verbose_name=_("Entrez la clé FEDOW pour activer le modèle fédéré :"))
    onboard_url = models.URLField(blank=True, null=True, verbose_name=_("Validez votre compte stripe :"),
                                  editable=False)

    fedow_domain = models.URLField(blank=True, null=True, editable=False)
    fedow_place_uuid = models.UUIDField(blank=True, null=True, editable=False)
    fedow_ip = models.GenericIPAddressField(blank=True, null=True, editable=False)
    fedow_place_admin_apikey = models.CharField(max_length=41, blank=True, null=True, editable=False)
    # fedow_place_wallet_public_pem = models.CharField(max_length=500, blank=True, null=True, editable=False)
    fedow_place_wallet_uuid = models.UUIDField(blank=True, null=True, editable=False)

    self_fed_apikey = models.OneToOneField(APIKey, on_delete=models.SET_NULL, blank=True, null=True, editable=False)

    stripe_connect_account = models.CharField(max_length=21, blank=True, null=True, editable=False)
    stripe_connect_valid = models.BooleanField(default=False)

    fedow_synced = models.BooleanField(default=False, editable=False)

    private_pem = models.CharField(max_length=2048, editable=False)
    public_pem = models.CharField(max_length=512, editable=False)

    '''
    BADGEUSE
    '''

    badgeuse_active = models.BooleanField(default=False,
                                          verbose_name=_("Badgeuse active"),
                                          help_text=_("Création de l'article et du points de vente Badge si activé."))

    def can_fedow(self):
        # Peut poser des questions à fedow ?
        # Ne vérifie pas les composants liés à stripe
        return all([
            self.fedow_domain,
            self.fedow_place_uuid,
            # self.fedow_ip,
            self.fedow_place_admin_apikey,
            # self.fedow_place_wallet_public_pem,
            self.fedow_place_wallet_uuid,
            # self.self_fed_apikey,
            self.private_pem,
            self.public_pem,
            self.fedow_synced,
        ])

    # TODO: Chiffrer avec Fernet :
    def get_private_key(self):
        if not self.private_pem:
            private_pem, public_pem = rsa_generator()
            self.private_pem = private_pem
            self.public_pem = public_pem
            self.save()

        private_key = serialization.load_pem_private_key(
            self.private_pem.encode('utf-8'),
            password=settings.SECRET_KEY.encode('utf-8'),
        )
        return private_key

    def get_public_pem(self):
        if not self.public_pem:
            private_pem, public_pem = rsa_generator()
            self.private_pem = private_pem
            self.public_pem = public_pem
            self.save()

        return self.public_pem

    def get_public_key(self):
        # Charger la clé publique au format PEM
        public_key = serialization.load_pem_public_key(self.get_public_pem().encode('utf-8'), backend=default_backend())
        return public_key

    def _onboarding(self):
        if self.onboard_url:
            # import ipdb; ipdb.set_trace()
            return format_html(f"<a href={self.onboard_url}>Please valid your stripe account</a>")
        return ""

    def federated_with(self):
        if self.can_fedow():
            dashboard_fedow = f"https://{self.fedow_domain}/dashboard/place/{self.fedow_place_uuid}/"
            return format_html(f"<a href={dashboard_fedow}>Dashboard Fedow</a>")

        else:
            return _("Aucune fédération configurée")

    class Meta:
        verbose_name = _('Configuration')
        verbose_name_plural = _('Configuration')

    def save(self, *args, **kwargs):
        if self.billetterie_url:
            if not self.billetterie_url.endswith('/'):
                self.billetterie_url += '/'
        # if self.domaine_cashless:
        #     if not self.domaine_cashless.endswith('/'):
        #         self.domaine_cashless += '/'
        if self.dokos_url:
            if not self.dokos_url.endswith('/'):
                self.dokos_url += '/'
        cache.clear()
        logger.info(f"Conf cache cleared")
        super().save(*args, **kwargs)


class RapportTableauComptable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    date = models.DateField()
    chiffre_affaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    monnaie_restante = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delta_monnaie = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cadeau_restant = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delta_cadeau = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cash_float = models.IntegerField(blank=True, null=True, verbose_name=_("Fond de caisse."))

    # TODO: EX A VIRER ?
    # Tableau Recette
    recharge_cashless_carte_bancaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recharge_cashless_espece = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    recharge_cashless_stripe = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    vente_directe_carte_bancaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vente_directe_espece = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    vente_directe_stripe = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    adhesion_carte_bancaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    adhesion_espece = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    adhesion_stripe = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    remboursement_carte_bancaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remboursement_espece = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remboursement_stripe = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    recharge_cadeau = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recharge_cadeau_oceco = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Tableau Dépense
    # Foreign key

    monnaie_restante_calcul_rapport = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def _monnaie_restante(self):
        # monnaie_restante est renseigné par le cron4hmatin
        if self.monnaie_restante:
            return self.monnaie_restante
        # calculré par re_rapport
        elif self.monnaie_restante_calcul_rapport:
            return self.monnaie_restante_calcul_rapport
        # renvoie la valeur actuelle
        else:
            return Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_EURO).aggregate(Sum('qty'))['qty__sum']

    cadeau_restant_calcul_rapport = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def _monnaie_cadeau_restante(self):
        if self.cadeau_restant:
            return self.cadeau_restant
        elif self.cadeau_restant_calcul_rapport:
            return self.cadeau_restant_calcul_rapport
        else:
            return Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_GIFT).aggregate(Sum('qty'))['qty__sum']

    cout_estime = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    benefice_estime = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ('-date',)
        verbose_name = _('EX Tableau comptable')
        verbose_name_plural = _('EX Tableaux comptable')
