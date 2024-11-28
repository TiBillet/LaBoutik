from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.utils import translation
from django.utils.translation import gettext as _

from APIcashless.models import *
from tibiauth.models import TibiUser as User
from .admin_commun import *


class RootAdminSite(AdminSite):
    site_header = "TiBillet Root Admin"
    site_title = "TiBillet Root Admin"
    site_url = '/wv'

    def has_permission(self, request):
        """
        Removed check for is_staff.
        """
        return request.user.is_superuser

    def index(self, request, extra_context=None):
        user_language = settings.LANGUAGE_CODE
        translation.activate(user_language)
        request.session[translation.LANGUAGE_SESSION_KEY] = user_language
        logger.info(f"LANG : {translation.get_language()}")

        template_response_index = super(RootAdminSite, self).index(request)
        return template_response_index


root_admin_site = RootAdminSite(name='adminroot')


class CustomGroupAdmin(GroupAdmin):
    pass


# root_admin_site.register(StatusMembre)


# def moyen_paiement_cadeau(modeladmin, request, queryset):
#     queryset.update(moyenPaiement=MoyenPaiement.objects.get(name='Cadeau'))
# moyen_paiement_cadeau.short_description = "Moyen de paiement = Cadeau"
#
#
# def Decomptabiliser(modeladmin, request, queryset):
#     queryset.update(comptabilise=False)
# Decomptabiliser.short_description = "Comptabilise = False"

class AppareilAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'hostname',
        'user',
        'ip_lan',
        'periph',
    )
    fields = list_display
    readonly_fields = ['id', ]
    list_filter = list_display


root_admin_site.register(Appareil, AppareilAdmin)


# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class AppareilInline(admin.StackedInline):
    model = Appareil
    can_delete = False
    verbose_name_plural = _('Appareils')


# Register out own model admin, based on the default UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (AppareilInline,)
    # fieldsets = (
    #     (None, {'fields': ('email', 'password')}),
    # ('Permissions', {'fields': ('is_staff', 'is_active','is_superstaff')}),
    # )

    pass


root_admin_site.register(User, CustomUserAdmin)


class AppairageAdmin(admin.ModelAdmin):
    list_display = ('front', 'lecteur_nfc',)
    fields = list_display
    list_filter = list_display


root_admin_site.register(Appairage, AppairageAdmin)


class CouleurAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_fr', 'hexa', 'pk')
    fields = ('name', 'name_fr', 'hexa')
    list_filter = ('name', 'name_fr', 'hexa')


root_admin_site.register(Couleur, CouleurAdmin)


class CategorieAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'url_image',
        'couleur_texte',
        'couleur_backgr',
        'poid_liste',
        'icon',
        'cashless',
    )

    fields = (
        'name',
        'url_image',
        'couleur_texte',
        'couleur_backgr',
        'poid_liste',
        'icon',
        'cashless',
    )

    list_editable = ('url_image',
                     'couleur_texte',
                     'couleur_backgr',
                     'poid_liste',
                     'cashless',
                     )
    search_fields = ['name', ]


root_admin_site.register(Categorie, CategorieAdmin)


class ArticlesAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'prix',
        'prix_achat',
        'categorie',
        'methode_choices',
        'poid_liste',
        'methode',
        'couleur_texte',
        'archive',
    )

    fields = (
        'name',
        'prix',
        'prix_achat',
        'categorie',
        'methode',
        'methode_choices',
        'poid_liste',
        'image',
        'couleur_texte',
        ('fractionne', 'archive'),
        'fedow_asset',

    )
    # readonly_fields = ('methode',)
    list_editable = (
        'prix',
        'prix_achat',
        'poid_liste',
        'couleur_texte',
        'categorie',
        'methode_choices',
        'archive',
    )
    list_filter = ('archive', 'categorie',)
    search_fields = ['name', ]


root_admin_site.register(Articles, ArticlesAdmin)


class CarteCashlessAdmin(admin.ModelAdmin):
    fields = ('number', 'uuid_qrcode', 'tag_id', 'membre', 'adhesion_suspendue')
    list_display = ('number', 'tag_id', 'membre', 'portefeuille', 'adhesion_suspendue')
    search_fields = ['tag_id', 'uuid_qrcode', 'number', 'membre__name']

    list_filter = ['membre', 'number', 'adhesion_suspendue']
    list_per_page = 20


root_admin_site.register(CarteCashless, CarteCashlessAdmin)


class AssetsAdmin(admin.ModelAdmin):
    list_display = ('carte', 'membre', 'monnaie', 'qty', "last_date_used", "is_sync")
    list_per_page = 50
    list_filter = ('carte', 'monnaie', 'carte__membre', "is_sync")


root_admin_site.register(Assets, AssetsAdmin)


class MoyenPaiementAdmin(admin.ModelAdmin):
    list_display = ('name', 'pk', 'blockchain', 'ardoise', 'cadeau')
    list_per_page = 10


root_admin_site.register(MoyenPaiement, MoyenPaiementAdmin)


class CategorieTableAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')


root_admin_site.register(CategorieTable, CategorieTableAdmin)


class ArticleCommandeInlines(CompactInline):
    model = ArticleCommandeSauvegarde


class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        'table',
        'statut',
        'commentaire',
        'responsable_name',
        'liste_articles',
        'datetime',
        'reste_a_payer',
        'id_commande',
        'id_service',
        'numero_du_ticket_imprime',
    )
    inlines = [
        ArticleCommandeInlines,
    ]


root_admin_site.register(CommandeSauvegarde, CommandeAdmin)


class ArticleCommandeSauvegardeAdmin(admin.ModelAdmin):
    list_display = (
        'article',
        'commande',
        'table',
        'qty',
        'reste_a_payer',
        'reste_a_servir',
        'statut',
    )


root_admin_site.register(ArticleCommandeSauvegarde, ArticleCommandeSauvegardeAdmin)


# class ArticlesVendusAdmin(DefaultFilterMixIn):
class ArticlesVendusAdmin(admin.ModelAdmin):
    list_display = (
        'article',
        'categorie',
        'prix',
        '_qty',
        'total',
        'date_time',
        'moyen_paiement',
        'membre',
        'carte',
        'responsable',
        'pos',
        'table',
        'id_commande',
        'id_paiement',
        # 'hash8_fedow',
        'ip_user',

    )

    # readonly_fields = ('article', 'prix','qty','date_time','membre',  'moyen_paiement', 'responsable','pos' )
    # search_fields = ['date_time']

    list_filter = [
        'article',
        'categorie',
        'responsable',
        ('date_time', DateRangeFilter),
        'moyen_paiement',
        'carte',
        'pos',
        'table',
    ]

    default_filters = ('pos__id__exact=48',)
    # actions = [moyenPaiementCadeau, Decomptabiliser]
    list_per_page = 50


root_admin_site.register(ArticleVendu, ArticlesVendusAdmin)


# class BoutonAdmin(admin.ModelAdmin):
#     fields = ('nom', 'idHtml', 'largeur', 'hauteur', 'texte', 'couleur_texte', 'ligne', 'tailleTexte',
#               'couleur_backgr', 'infoTexte', 'infoCouleurTexte', 'infoId', 'fonctionNom', 'fonctionVariable')
#     list_display = (
#     'nom', 'idHtml', 'largeur', 'hauteur', 'texte', 'couleur_texte', 'ligne', 'tailleTexte', 'couleur_backgr',
#     'infoTexte', 'infoCouleurTexte', 'infoId', 'fonctionNom', 'fonctionVariable')
#     list_filter = ('nom',)
#
# root_admin_site.register(Bouton, BoutonAdmin)

#
# class ConfpointOfSaleAdmin(admin.ModelAdmin):
#     fields = ('nom','presencePrix')
#     list_display = ('nom','presencePrix')
#     list_filter = ('nom',)
#
# root_admin_site.register(ConfpointOfSale, ConfpointOfSaleAdmin)


# noinspection PyUnusedLocal
def afficher_les_prix(modeladmin, request, queryset):
    queryset.update(afficher_les_prix=True)


afficher_les_prix.short_description = "Aficher les prix"


# noinspection PyUnusedLocal
def cacher_les_prix(modeladmin, request, queryset):
    queryset.update(afficher_les_prix=False)


cacher_les_prix.short_description = "Cacher les prix"


# noinspection PyUnusedLocal
def accepte_especes(modeladmin, request, queryset):
    queryset.update(accepte_especes=True)


accepte_especes.short_description = "Accepte especes"


# noinspection PyUnusedLocal
def refuse_especes(modeladmin, request, queryset):
    queryset.update(accepte_especes=False)


refuse_especes.short_description = "Refuse especes"


# noinspection PyUnusedLocal
def accepte_cb(modeladmin, request, queryset):
    queryset.update(accepte_carte_bancaire=True)


accepte_cb.short_description = "Accepte carte bancaire"


# noinspection PyUnusedLocal
def refuse_cb(modeladmin, request, queryset):
    queryset.update(accepte_carte_bancaire=False)


refuse_cb.short_description = "Refuse carte bancaire"


class PointOfSaleAdmin(admin.ModelAdmin):
    fields = (
        'name',
        'articles',
        'poid_liste',
        'categories',
        'wallet',
        'afficher_les_prix',
        'accepte_especes',
        'accepte_carte_bancaire',
        'accepte_commandes',
        'service_direct',
        'comportement',
        'icon')

    list_display = (
        'name',
        'poid_liste',
        'afficher_les_prix',
        'accepte_especes',
        'accepte_carte_bancaire',
        'accepte_commandes',
        'service_direct',
        'comportement',
        'icon'
    )
    readonly_fields = ('wallet',)
    list_filter = ('name',)

    list_editable = ('afficher_les_prix',
                     'accepte_especes',
                     'accepte_carte_bancaire',
                     'accepte_commandes',
                     'service_direct',
                     )

    actions = [afficher_les_prix, cacher_les_prix,
               accepte_especes, refuse_especes, accepte_cb, refuse_cb]


# noinspection DuplicatedCode
root_admin_site.register(PointDeVente, PointOfSaleAdmin)


class InformationGeneraleAdmin(admin.ModelAdmin):
    fields = ('date', 'total_monnaie_principale')
    list_display = ('date', 'total_monnaie_principale')


root_admin_site.register(InformationGenerale, InformationGeneraleAdmin)


class OdoologsAdmin(admin.ModelAdmin):
    fields = ('date', 'log')
    list_display = ('date', 'log')


root_admin_site.register(Odoologs, OdoologsAdmin)

'''
DEPUIS admin_commun :
'''

fieldsets_moyen_paiement = (
    (
        'Moyen_Paiement', {
            'fields': (
                'monnaie_principale',
                'monnaie_principale_cadeau',
                'monnaie_principale_ardoise',
                'moyen_paiement_espece',
                'moyen_paiement_cb',
                'moyen_paiement_mollie',
                'moyen_paiement_oceco',
                'moyen_paiement_commande',
                'monnaies_acceptes',
            ),
        },
    ),
)

