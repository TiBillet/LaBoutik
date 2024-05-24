import requests
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from APIcashless.models import ArticleVendu, Configuration, Appareil, CarteCashless, CarteMaitresse, MoyenPaiement, \
    Categorie, Articles, PointDeVente, Membre
from epsonprinter.tasks import direct_to_print
from APIcashless.tasks import adhesion_to_odoo, cashback, badgeuse_to_dokos, fidelity_task, email_new_hardware
from fedow_connect.fedow_api import FedowAPI
from fedow_connect.tasks import badgeuse_to_fedow, create_card_to_fedow, set_primary_card
from django.utils.translation import gettext_lazy as _

import logging

logger = logging.getLogger(__name__)


class TriggerMethodeArticleVenduPOSTSAVE:
    def __init__(self, article_vendu: ArticleVendu, created: bool):
        self.article_vendu = article_vendu
        self.methode = article_vendu.article.methode_choices
        self.created = created

        try:
            # on met en majuscule et on rajoute _ au début du nom de la catégorie.
            trigger_name = f"_{self.methode.upper()}"
            logger.info(
                f"methode_trigger launched - ArticleVendu : {self.article_vendu} - trigger_name : {trigger_name}")
            trigger = getattr(self, f"trigger{trigger_name}")
            trigger()
        except AttributeError as exc:
            logger.info(f"Pas de trigger ArticleVendu pour la methode {self.methode} -> error : {exc}")
        except Exception as exc:
            logger.error(f"category_trigger ERROR  {type(exc)} : {exc}")

    def trigger_VT(self):
        logger.info(f"TRIGGER ArticleVendu.methode_choices -> VENTE")
        config = Configuration.get_solo()
        if config.fidelity_active and self.article_vendu.carte:
            fidelity_task(self.article_vendu.pk)
            # import ipdb; ipdb.set_trace()

    def trigger_AD(self):
        pass
        # TODO: Déplacer dans Lespass
        # logger.info(f"TRIGGER ArticleVendu.methode_choices -> ADHESION -> adhesion_to_odoo.delay")
        # if not self.article_vendu.comptabilise:
        #     adhesion_to_odoo.delay(self.article_vendu.pk)

    # Trigger des recharges euros en local (Espèce ou TPE des lieux ou Stripe Non connect)
    def trigger_RE(self):
        config = Configuration.get_solo()

        # CASHBACK
        if config.cashback_active:
            logger.info(f"TRIGGER ArticleVendu.methode_choices -> RECHARGE EUROS -> CASHBACK")
            total = self.article_vendu.total()
            if total >= config.cashback_start \
                    and config.cashback_value > 0 \
                    and self.article_vendu.carte:
                cashback.delay(self.article_vendu.pk)

    def trigger_BG(self):
        # badgeuse
        logger.info(f"TRIGGER ArticleVendu.methode_choices -> BADGEUSE")

        badgeuse_to_fedow(self.article_vendu.pk)

        # TODO: Déplacer dans LesPass
        badgeuse_to_dokos(self.article_vendu.pk)

        #
        # task_fedow = badgeuse_to_fedow.delay(self.article_vendu.pk)
        # logger.info(f"task_badg : {task_fedow}")
        #
        # task_doko = badgeuse_to_dokos.delay(self.article_vendu.pk)
        # logger.info(f"task_badg : {task_doko}")


@receiver(post_save, sender=Appareil)
def send_mail_to_admin(sender, instance: Appareil, created, **kwargs):
    if instance.actif:
        email_new_hardware.delay(instance.pk)


@receiver(post_save, sender=ArticleVendu)
def postsave_article_vendu(sender, instance: ArticleVendu, created, **kwargs):
    TriggerMethodeArticleVenduPOSTSAVE(instance, created)

    if instance.article.direct_to_printer:
        logger.info(f"DIRECT TO PRINT : {instance}")
        direct_to_print.delay(instance.pk)


@receiver(pre_save, sender=ArticleVendu)
def set_category_from_article(sender, instance: ArticleVendu, **kwargs):
    """
    On récupère la catégorie de l'article et on la met dans la catégorie de l'ArticleVendu
    """
    if instance.article:
        instance.categorie = instance.article.categorie


@receiver(post_save, sender=CarteCashless)
def send_card_to_fedow(sender, instance: CarteCashless, created, **kwargs):
    if created:
        # On le fait en synchrone, comme ça si ça plante, on le voit dans l'admin
        create_card_to_fedow(instance.pk)


@receiver(post_save, sender=CarteMaitresse)
def send_primarycard_to_fedow(sender, instance: CarteMaitresse, created, **kwargs):
    if created:
        # On le fait en synchrone, comme ça si ça plante, on le voit dans l'admin
        set_primary_card(instance.carte.pk)


@receiver(post_save, sender=MoyenPaiement)
def send_new_asset_to_fedow(sender, instance: MoyenPaiement, created, **kwargs):
    if created:
        # Si c'est dans les catégories acceptés par Fedow
        if instance.fedow_category():
            config = Configuration.get_solo()
            if config.can_fedow():
                fedowAPI = FedowAPI()
                asset, created = fedowAPI.asset.get_or_create_asset(instance)



@receiver(post_save, sender=MoyenPaiement)
def create_article_membership(sender, instance: MoyenPaiement, created, **kwargs):
    if created:
        logger.info(f'MoyenPaiement {instance.get_categorie_display()} created !')
        if instance.categorie in [
            MoyenPaiement.ADHESION,
            MoyenPaiement.MEMBERSHIP,
            MoyenPaiement.EXTERNAL_MEMBERSHIP,
        ]:
            config = Configuration.get_solo()
            retrieve_product = requests.get(
                f"{config.billetterie_url}/api/products/{instance.pk}/",
                verify=bool(not settings.DEBUG))
            product = retrieve_product.json()

            # Création de la catégorie Adhésion
            CatMembership, created = Categorie.objects.get_or_create(
                name=_("Memberships"),
                icon='fa-address-book',
                cashless=False,
            )

            prices = []
            for price in product.get('prices'):
                art = Articles.objects.create(
                    name=f"{product['name']} {price['name']}",
                    methode_choices=Articles.ADHESIONS,
                    prix=price['prix'],
                    categorie=CatMembership,
                    subscription_fedow_asset=instance,
                )
                prices.append(art)





@receiver(post_save, sender=MoyenPaiement)
def create_article_badge(sender, instance: MoyenPaiement, created, **kwargs):
    if created:
        logger.info(f'MoyenPaiement {instance.get_categorie_display()} created !')
        if instance.categorie in [
            MoyenPaiement.BADGE,
            MoyenPaiement.EXTERNAL_BADGE,
        ]:
            config = Configuration.get_solo()

            retrieve_product = requests.get(
                f"{config.billetterie_url}/api/products/{instance.pk}/",
                verify=bool(not settings.DEBUG))
            product = retrieve_product.json()

            # Création de la catégorie Adhésion
            CatBadge, created = Categorie.objects.get_or_create(
                name=_("Badge"),
                icon='fa-address-card',
                cashless=False,
            )

            prices = []
            for price in product.get('prices'):
                art = Articles.objects.create(
                    name=f"{product['name']} {price['name']}",
                    methode_choices=Articles.BADGEUSE,
                    prix=price['prix'],
                    categorie=CatBadge,
                    subscription_fedow_asset=instance,
                )
                prices.append(art)




@receiver(post_save, sender=Membre)
def link_membre_to_card(sender, instance: Membre, created, **kwargs):
    # import ipdb; ipdb.set_trace()
    pass