from datetime import datetime, timedelta
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers

from APIcashless.models import CarteCashless, PointDeVente, Articles, CarteMaitresse, Assets, Configuration, Categorie, \
    Table, CategorieTable, CommandeSauvegarde, ArticleCommandeSauvegarde, GroupementCategorie, TauxTVA, MoyenPaiement

import pytz
import logging

logger = logging.getLogger(__name__)


def debut_fin_journee():
    """

    @type datetime_vente: datetime
    """
    now = timezone.now()
    jour = now.date()

    tzlocal = pytz.timezone(Configuration.get_solo().fuseau_horaire)
    debut_jour = tzlocal.localize(datetime.combine(jour, datetime.min.time()), is_dst=None) + timedelta(
        hours=4)
    lendemain_quatre_heure = tzlocal.localize(datetime.combine(jour, datetime.max.time()), is_dst=None) + timedelta(
        hours=4)

    if now < debut_jour:
        # alors ça s'est passé au petit matin. La date de l'évènement est celle de la veille.
        return debut_jour - timedelta(days=1), debut_jour
    else:
        return debut_jour, lendemain_quatre_heure


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets
        fields = (
            'monnaie',
            'monnaie_name',
            'qty',
            'last_date_used',
            'categorie',
        )

        read_only_fields = fields


class TvaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TauxTVA
        fields = (
            'name',
            'taux',
        )

        read_only_fields = fields


class CarteCashlessSerializer(serializers.ModelSerializer):
    cartes_maitresses = serializers.StringRelatedField(many=True, read_only=True)
    assets = serializers.SerializerMethodField()

    def get_assets(self, carte: CarteCashless):
        # On ne garde que les assets acceptés pour les paiements
        payment_assets = carte.get_payment_assets()
        self.total_monnaie = carte.total_monnaie()

        serializer = AssetSerializer(instance=payment_assets, many=True)
        return serializer.data

    # on met a jour la date last action sur le membre de la carte.
    # Comme un touch sur un fichier linux !
    def touch_membre(self, instance: CarteCashless):
        if instance.membre:
            instance.membre.save()

    def to_representation(self, instance: CarteCashless):
        representation = super().to_representation(instance)

        # on met a jour la date last_action sur le membre de la carte :
        self.touch_membre(instance)

        # On ajoute le total monnaie.
        representation['total_monnaie'] = f"{self.total_monnaie}"
        return representation

    class Meta:
        model = CarteCashless
        fields = (
            'tag_id',
            'number',
            'uuid_qrcode',
            'wallet',
            # 'total_monnaie',
            'membre_name',
            'cotisation_membre_a_jour',
            'cotisation_membre_a_jour_booleen',
            'cartes_maitresses',
            'assets',
        )
        read_only_fields = fields


class CategorieSerializer(serializers.ModelSerializer):
    tva = TvaSerializer(read_only=True)
    couleur_backgr = serializers.SlugRelatedField(
        read_only=True,
        slug_field='hexa'
    )

    couleur_texte = serializers.SlugRelatedField(
        read_only=True,
        slug_field='hexa'
    )

    class Meta:
        model = Categorie
        fields = (
            'id',
            'name',
            'poid_liste',
            'icon',
            'couleur_backgr',
            'couleur_texte',
            'groupements',
            'tva',
        )
        read_only_fields = fields


class ArticleSerializer(serializers.ModelSerializer):
    categorie = CategorieSerializer(read_only=True)
    couleur_texte = serializers.SlugRelatedField(
        read_only=True,
        slug_field='hexa'
    )

    class Meta:
        model = Articles
        fields = (
            'id',
            'name',
            'prix',
            'poid_liste',
            'categorie',
            'url_image',
            'couleur_texte',
            'methode_name',
            'archive',
        )

        read_only_fields = fields


class PointDeVenteSerializer(serializers.ModelSerializer):
    articles = ArticleSerializer(
        many=True,
        read_only=True,
    )

    # source='commandes'
    # Ici on filtre et réduit l'appel en db sur que les commande OUVERTE
    # articles = serializers.SerializerMethodField('get_articles')
    # def get_articles(self, pdv):
    #     items = Articles.objects.filter(categorie__in=pdv.categories.all(), archive=False)
    # serializer = ArticleSerializer(instance=items, many=True, read_only=True)
    # return serializer.data

    # TODO: passer en SerializerMethodField ( cf table plus bas )
    def to_representation(self, instance):
        """
        1/ On rajoute le nom de la monnaie sur les name cashless.
        2/ On retire les articles mis en archives
        """
        ret = super().to_representation(instance)

        # TODO: Virer ce "Cashless" et utiliser des choices en dur ( variable permanente de methode )
        # 1/ On rajoute le nom de la monnaie sur les name cashless.
        # noinspection PyCompatibility
        if ret['name'] == "Cashless":
            for art in ret['articles']:
                if art['methode_name'] == "AjoutMonnaieVirtuelle" or \
                        art['methode_name'] == "AjoutMonnaieVirtuelleCadeau":
                    art['name'] = f"{Configuration.objects.get().monnaie_principale.name} {art['name']}"

        # 2/ On retire les articles mis en archives
        for art in ret['articles']:
            if art['archive']:
                ret['articles'].remove(art)
        return ret

    class Meta:
        model = PointDeVente
        fields = (
            'id',
            'name',
            'poid_liste',
            'comportement',
            'afficher_les_prix',
            'accepte_especes',
            'accepte_carte_bancaire',
            'accepte_commandes',
            'service_direct',
            'articles',
            'icon',
        )
        read_only_fields = fields


class CarteMaitresseSerializer(serializers.ModelSerializer):
    points_de_vente = PointDeVenteSerializer(many=True, read_only=True)
    carte = CarteCashlessSerializer(read_only=True)

    class Meta:
        model = CarteMaitresse
        fields = (
            'points_de_vente',
            'carte',
            'edit_mode',
        )
        read_only_fields = fields


'''
GESTION PANIER RESTAURATION
'''


class CategorieTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieTable
        fields = (
            'name',
            'icon'
        )
        read_only_fields = fields


class ArticleCommandeSerializer(serializers.ModelSerializer):
    article = ArticleSerializer(read_only=True)

    class Meta:
        model = ArticleCommandeSauvegarde
        fields = (
            'article',
            'qty',
            'reste_a_payer',
            'reste_a_servir',
            'statut',

        )
        read_only_fields = fields


class CommandeSerializer(serializers.ModelSerializer):
    # def __init__(self, *args, **kwargs):
    #     start = timezone.now()
    #     super().__init__(*args, **kwargs)
    #     logger.info(f"{timezone.now()} {timezone.now() - start} __init__ CommandeSerializer")

    articles = ArticleCommandeSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = CommandeSauvegarde
        fields = (
            'uuid',
            'responsable_name',
            'datetime',
            'statut',
            'articles',
            'commentaire',
            'table',
            'table_name',
            'reste_a_payer',
            'numero_du_ticket_imprime',
        )
        read_only_fields = fields


class TableSerializer(serializers.ModelSerializer):
    categorie = CategorieTableSerializer(read_only=True)

    class Meta:
        model = Table
        fields = (
            'id',
            'name',
            'poids',
            'position_top',
            'position_left',
            'categorie',
            'statut',
            'ephemere',
            'archive',
        )
        read_only_fields = fields


class TableSerializerWithCommand(serializers.ModelSerializer):
    # source='categorie'
    categorie = CategorieTableSerializer(read_only=True)

    # source='commandes'
    # Ici on filtre et réduit l'appel en db sur que les commandes OUVERTE
    commandes = serializers.SerializerMethodField('get_items')

    def get_items(self, table):
        items = CommandeSauvegarde.objects.filter(table=table, archive=False) \
            .exclude(statut=CommandeSauvegarde.SERVIE_PAYEE) \
            .exclude(statut=CommandeSauvegarde.ANNULEE)
        serializer = CommandeSerializer(instance=items, many=True)
        return serializer.data

    class Meta:
        model = Table
        fields = (
            'id',
            'name',
            'poids',
            'position_top',
            'position_left',
            'categorie',
            'statut',
            'commandes',
            'reste_a_payer',
            'ephemere',
            'archive',
        )
        read_only_fields = fields


class GroupCategorieSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        start = timezone.now()

        table_pk = kwargs.get('table')
        kwargs.pop('table', None)
        super().__init__(*args, **kwargs)

        debut_journee, fin_journee = debut_fin_journee()
        # c'est une de mande depuis la préparation d'une table en particulier
        if table_pk:
            table = get_object_or_404(Table, pk=table_pk)
            # on garde les servies et payées sur 6H pour l'historique
            self.all_commandes = CommandeSauvegarde.objects.filter(
                archive=False,
                table=table,
            ).exclude(
                Q(datetime__lte=(timezone.now() - timedelta(hours=6))) & Q(statut=CommandeSauvegarde.SERVIE_PAYEE)
            ).distinct()


        else:
            self.all_commandes = CommandeSauvegarde.objects.filter(
                archive=False,
            ).exclude(
                Q(datetime__lte=(timezone.now() - timedelta(minutes=15))) & Q(statut=CommandeSauvegarde.SERVIE_PAYEE)
            ).distinct()

            # .exclude(statut=CommandeSauvegarde.ANNULEE) \
            # .exclude(statut=CommandeSauvegarde.SERVIE_PAYEE) \
            # .exclude(statut=CommandeSauvegarde.SERVIE) \

            # self.all_commandes = CommandeSauvegarde.objects \
            #     .exclude(Q(datetime__lte=debut_journee) & Q(statut=CommandeSauvegarde.SERVIE_PAYEE)) \
            #     .exclude(Q(datetime__lte=debut_journee) & Q(statut=CommandeSauvegarde.ANNULEE)) \
            #     .distinct()

        logger.info(f"{timezone.now()} {timezone.now() - start} __init__ GroupCategorieSerializer")

    commandes = serializers.SerializerMethodField('get_items')

    def get_items(self, instance: Categorie):
        start = timezone.now()
        categorie = instance

        # on filtre par catégorie, mais si une commande à des articles venant de plusieurs groupements de catégories
        # Sinon,
        # il va falloir un filtre supplémentaire dans to representation
        commandes = self.all_commandes.filter(articles__article__categorie__groupements=categorie)
        logger.info(f"len(commandes) : {len(commandes)}")
        serializer = CommandeSerializer(instance=commandes, many=True)
        data_cmd = serializer.data
        logger.info(f"{timezone.now()} {timezone.now() - start} get_items {categorie} GroupCategorieSerializer")
        return data_cmd

    def to_representation(self, instance):
        """
        On retire les articles qui ne correspondent pas au groupement de catégorie dans chaque commande.
        Le but etant que la cuisine n'ait que les articles de boufffe,
        le Bar n'ai que les articles de boissons.
        Les articles sont triés en fonction des groupements de catégories.
        @type instance: GroupementCategorie
        """

        ret = super().to_representation(instance)

        for commande in ret['commandes']:
            lignes_articles_filtres = []
            for ligne_article in commande['articles']:
                categorie = ligne_article['article'].get('categorie')
                if categorie:
                    groupements = categorie.get('groupements')
                    if groupements:
                        if len(groupements) > 0:
                            for groupement in groupements:
                                if groupement == instance.pk:
                                    lignes_articles_filtres.append(ligne_article)

            commande['articles'] = lignes_articles_filtres

        return ret

    class Meta:
        model = GroupementCategorie
        fields = (
            'pk',
            'name',
            'commandes',
            'icon',
        )
        read_only_fields = fields
