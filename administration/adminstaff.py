from copy import deepcopy

import requests
from adminsortable2.admin import SortableAdminMixin
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from django.core.cache import cache
from django.db.models import Q
from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework_api_key.models import APIKey
from solo.admin import SingletonModelAdmin

from APIcashless.custom_utils import badgeuse_creation, declaration_to_discovery_server, get_pin_on_appareillage
from APIcashless.models import Categorie, CarteMaitresse, CommandeSauvegarde, Appareil, \
    Couleur, TauxTVA, ClotureCaisse
from APIcashless.models import GroupementCategorie, Table, MoyenPaiement
from APIcashless.tasks import email_activation
from administration.views import TicketZ
from administration.admin_commun import *
from epsonprinter.models import Printer
from epsonprinter.tasks import ticketZ_tasks_printer
from fedow_connect.tasks import create_card_to_fedow
from fedow_connect.views import handshake
from odoo_api.odoo_api import OdooAPI
from tibiauth.models import TibiUser

logger = logging.getLogger(__name__)


class StaffAdminSite(AdminSite):
    site_header = "TiBillet Staff Admin"
    site_title = "TiBillet Staff Admin"

    # Le lien "voir le site" :
    site_url = '/wv'

    def has_permission(self, request):
        # Si c'est un user de terminal : False
        if getattr(request.user, 'appareil', None):
            return False
        return request.user.is_staff

    def index(self, request, extra_context=None):
        user_language = settings.LANGUAGE_CODE
        translation.activate(user_language)
        request.session[translation.LANGUAGE_SESSION_KEY] = user_language
        logger.info(f"LANG : {translation.get_language()}")

        template_response_index = super(StaffAdminSite, self).index(request)
        return template_response_index


staff_admin_site = StaffAdminSite(name='adminstaff')


### USER ADMIN
def send_password_reset_email(modeladmin, request, queryset):
    queryset.update(is_active=False)
    for user in queryset:
        email_activation(user.uuid)


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    # password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    # password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = TibiUser
        fields = ('email', 'is_staff',)
        help_texts = {
            'email': _(
                'Un email valide est nécessaire pour la connexion. Un formulaire de création de mot de passe sera envoyé.'),
        }

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.is_active = False
        user.save()
        email_activation(user.uuid)
        return user


# Register out own model admin, based on the default UserAdmin
class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm

    list_display = ('username', 'email', 'is_staff', 'is_active')
    list_editable = ('is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('email', 'username', 'is_staff', 'is_active')}),
    )
    actions = [send_password_reset_email]
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'is_staff',)}
         ),
    )

    def get_queryset(self, request):
        qs = super(CustomUserAdmin, self).get_queryset(request)
        return qs.filter(appareil__isnull=True, is_superuser=False)


User = get_user_model()
staff_admin_site.register(User, CustomUserAdmin)


# staff_admin_site.unregister(Group)

###

# noinspection PyUnusedLocal
def afficher_les_prix(modeladmin, request, queryset):
    queryset.update(afficher_les_prix=True)


afficher_les_prix.short_description = _("Aficher les prix")


# noinspection PyUnusedLocal
def cacher_les_prix(modeladmin, request, queryset):
    queryset.update(afficher_les_prix=False)


cacher_les_prix.short_description = _("Cacher les prix")


# noinspection PyUnusedLocal
def accepte_especes(modeladmin, request, queryset):
    queryset.update(accepte_especes=True)


accepte_especes.short_description = _("Accepte especes")


# noinspection PyUnusedLocal
def refuse_especes(modeladmin, request, queryset):
    queryset.update(accepte_especes=False)


refuse_especes.short_description = _("Refuse especes")


# noinspection PyUnusedLocal
def accepte_cb(modeladmin, request, queryset):
    queryset.update(accepte_carte_bancaire=True)


accepte_cb.short_description = _("Accepte carte bancaire")


# noinspection PyUnusedLocal
def refuse_cb(modeladmin, request, queryset):
    queryset.update(accepte_carte_bancaire=False)


refuse_cb.short_description = _("Refuse carte bancaire")


class PointOfSaleAdmin(SortableAdminMixin, admin.ModelAdmin):
    fields = (
        'name',
        'articles',
        # 'categories',
        'afficher_les_prix',
        'accepte_especes',
        'accepte_carte_bancaire',
        'service_direct',
        'icon',
    )

    list_display = (
        'poid_liste',
        'name',
        'afficher_les_prix',
        'accepte_especes',
        'accepte_carte_bancaire',
        'service_direct',
        'icon',
    )

    list_display_links = ('name',)
    list_filter = ('name',)

    list_editable = ('afficher_les_prix',
                     'accepte_especes',
                     'accepte_carte_bancaire',
                     'service_direct',
                     'icon',
                     )
    actions = [afficher_les_prix, cacher_les_prix, accepte_especes, refuse_especes, accepte_cb, refuse_cb]

    # def get_queryset(self, request):
    #     qs = super(PointOfSaleAdmin, self).get_queryset(request)
    #     return qs.exclude(comportement=PointDeVente.CASHLESS)

    # pour retirer le petit bouton plus a coté des champs article
    def get_form(self, request, obj=None, **kwargs):  # Just added this override
        form = super(PointOfSaleAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['articles'].widget.can_add_related = False
        return form

    # pour selectionner uniquement les articles ventes et retour consigne
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # import ipdb; ipdb.set_trace()
        if db_field.name == "articles":
            kwargs["queryset"] = Articles.objects.all().exclude(archive=True).exclude(
                methode_choices__in=(Articles.FRACTIONNE,)
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


staff_admin_site.register(PointDeVente, PointOfSaleAdmin)


class CustomArticleRequiredForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categorie'].required = True
        help_text = ""
        groupes = GroupementCategorie.objects.all()
        if len(groupes) > 0:
            for groupe in groupes:
                categories = []

                for categorie in groupe.categories.all():
                    categories.append(categorie.name)

                help_text += _(f"<br/>Le menu de préparation {groupe.name} affichera et imprimera les catégories :")
                help_text += f"<br/>  {categories}"

            self.fields['categorie'].help_text = help_text

        help_text_direct_to_printer = _("Activez pour une impression directe après chaque vente.")

        self.fields['direct_to_printer'].help_text = help_text_direct_to_printer


class Meta:
    model = Articles
    fields = '__all__'


class ArticlesAdmin(SortableAdminMixin, admin.ModelAdmin):
    form = CustomArticleRequiredForm
    categorie = forms.ModelChoiceField(queryset=Categorie.objects.exclude(cashless=True))

    list_display = (
        'poid_liste',
        'name',
        'prix',
        'prix_achat',
        'categorie',
        'image',
        'couleur_texte',
        'archive',
    )

    list_display_links = ('name',)

    list_editable = (
        'prix',
        'prix_achat',
        # 'couleur_texte',
        # 'categorie',
        'archive',
    )

    search_fields = ['name', ]
    list_filter = ('categorie',)

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'prix',
                'prix_achat',
                'categorie',
                'image',
                'couleur_texte',
                'archive',
            )
        }),
        ('Special', {
            'fields': (
                'direct_to_printer',
                'decompte_ticket',
                'subscription_fedow_asset',
                'subscription_type',
            ),
        }),
    )

    # Pour ne voir que les articles sans Cashless :
    def get_queryset(self, request):
        qs = super(ArticlesAdmin, self).get_queryset(request)

        return qs.filter(
            Q(methode_choices=Articles.VENTE)
            | Q(methode_choices=Articles.RETOUR_CONSIGNE)
            | Q(methode_choices=Articles.BADGEUSE)
            | Q(methode_choices=Articles.ADHESIONS)
        ).filter(archive=False)

    # On retire les categories cashless dans les categories
    def get_form(self, request, obj=None, **kwargs):  # Just added this override
        form = super(ArticlesAdmin, self).get_form(request, obj, **kwargs)
        if form.base_fields.get('categorie'):
            form.base_fields['categorie'].queryset = form.base_fields['categorie'].queryset.exclude(cashless=True)

        if form.base_fields.get('subscription_fedow_asset'):
            form.base_fields['subscription_fedow_asset'].queryset = (
                form.base_fields['subscription_fedow_asset'].queryset.filter(categorie__in=[
                    MoyenPaiement.EXTERNAL_MEMBERSHIP,
                    MoyenPaiement.MEMBERSHIP,
                    MoyenPaiement.EXTERNAL_BADGE,
                    MoyenPaiement.BADGE,
                ]))

        return form


staff_admin_site.register(Articles, ArticlesAdmin)


class CategorieAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = (
        'poid_liste',
        'name',
        'tva',
        'couleur_texte',
        'couleur_backgr',
        'icon',
    )
    list_display_links = ('name',)
    fields = (
        'name',
        'couleur_texte',
        'couleur_backgr',
        'icon',
    )

    list_editable = (
        'tva',
    )

    def get_queryset(self, request):
        qs = super(CategorieAdmin, self).get_queryset(request)
        return qs.exclude(cashless=True)


staff_admin_site.register(Categorie, CategorieAdmin)

staff_admin_site.register(CarteMaitresse, CarteMaitresseAdmin)

staff_admin_site.register(Membre, MembresAdmin)


class assetsAdmin(admin.ModelAdmin):
    list_display = ('carte', 'membre', 'monnaie', 'qty', "last_date_used")
    readonly_fields = list_display
    list_per_page = 50
    list_filter = ('carte', 'monnaie',)
    # default_filters = (f'monnaie__id__exact={configuration.monnaie_principale.id}',)

    list_display_links = None

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super(assetsAdmin, self).get_queryset(request)

        return qs.filter(
            Q(monnaie__categorie=MoyenPaiement.LOCAL_EURO) | Q(monnaie__categorie=MoyenPaiement.LOCAL_GIFT))


# noinspection PyUnusedLocal
def valider_service(modeladmin, request, queryset: CommandeSauvegarde.objects):
    # import ipdb; ipdb.set_trace()
    for commande in queryset:
        for art in commande.articles.all():
            art.reste_a_servir = 0
            art.save()
        commande.check_statut()


valider_service.short_description = _("Commande(s) servie(s)")


# noinspection PyUnusedLocal
def supprimer_commande(modeladmin, request, queryset: CommandeSauvegarde.objects):
    # import ipdb; ipdb.set_trace()
    tables = []
    for commande in queryset:
        tables.append(commande.table)
        commande.delete()

    for table in tables:
        table.check_status()


supprimer_commande.short_description = _("Supprimer les commandes")


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

    readonly_fields = list_display
    list_display_links = None
    list_filter = (
        'table',
        'statut',
        ('datetime', DateRangeFilter),
        'archive',
    )
    actions = [valider_service, supprimer_commande]

    def changelist_view(self, request, extra_context=None):
        my_context = {
            # 'actions_on_bottom' : True,
            'messages': [_('Colonne " Liste des articles x/x/x " :  Qty Commandées / Reste à servir / Reste à payer ')],
            # 'title' : 'CACABOUDIN',
        }

        return super(CommandeAdmin, self).changelist_view(request,
                                                          extra_context=my_context)

    def get_queryset(self, request):
        qs: CommandeSauvegarde.objects = super(CommandeAdmin, self).get_queryset(request)
        return qs.exclude(articles__article__fractionne=True)


staff_admin_site.register(CommandeSauvegarde, CommandeAdmin)


class CategorieFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("methode")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'methode'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('RECHARGE_EUROS', _('Recharge Euros')),
            ('RECHARGE_CADEAU', _('Recharge Cadeau')),
            ('RECHARGES', _('RechargeS')),
            ('VENTE', _('Vente')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        VENTE = 'VT'
        RECHARGE_EUROS = 'RE'
        RECHARGE_CADEAU = 'RC'
        RECHARGES = 'RS'
        ADHESIONS = 'AD'
        RETOUR_CONSIGNE = 'CR'
        VIDER_CARTE = 'VC'
        BLANCHIR_CARTE = 'BC'
        VOID_CARTE = 'VV'
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == "RECHARGE_EUROS":
            return queryset.filter(article__methode_choices=Articles.RECHARGE_EUROS)
        elif self.value() == "RECHARGE_CADEAU":
            return queryset.filter(article__methode_choices=Articles.RECHARGE_CADEAU)
        elif self.value() == "RECHARGES":
            return queryset.filter(article__methode_choices__in=[Articles.RECHARGE_EUROS, Articles.RECHARGE_CADEAU])
        elif self.value() == "VENTE":
            return queryset.filter(article__methode_choices=Articles.VENTE)


class CarteCashlessAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "tag_id",
        "membre",
        "url_qrcode",
    )

    fields = (
        "tag_id",
        "number",
        "uuid_qrcode",
    )

    # readonly_fields = fields
    list_display_links = None

    search_fields = ['tag_id', 'number', 'membre__name', 'membre__prenom', 'membre__email']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def save_model(self, request, instance, form, change):
        if form.is_valid():
            instance.tag_id = instance.tag_id.upper()
            if not instance.uuid_qrcode:
                instance.uuid_qrcode = uuid4()

            if not instance.number:
                instance.number = str(instance.uuid_qrcode)[:8].upper()

            create_card_to_fedow.delay(instance.pk)
        super().save_model(request, instance, form, change)


staff_admin_site.register(CarteCashless, CarteCashlessAdmin)


def send_to_odoo(modeladmin, request, queryset):
    if queryset.exclude(article__methode_choices=Articles.ADHESIONS).exists():
        messages.add_message(request, messages.ERROR,
                             _("Des articles sélectionnés ne sont pas des adhésions. ACTION CANCELED"))
        return False

    odoo_api = OdooAPI()
    for article_vendu in queryset:
        try:
            result = odoo_api.new_membership(article_vendu)
            messages.add_message(request, messages.SUCCESS, f"ODOO OK : {result}")
        except Exception as e:
            messages.add_message(request, messages.ERROR, f"ODOO ERROR : {e}")


class ArticlesVendusAdmin(admin.ModelAdmin):
    # change_list_template = 'admin_totals_v2/change_list_totals.html'

    list_display = (
        '_article',
        'prix',
        '_qty',
        'tva',
        'total',
        'date_time',
        'moyen_paiement',
        # 'membre',
        'carte',
        'pos',
        'table',
        'id_commande',
    )

    fields = (
        'article',
        'prix',
        'qty',
        'moyen_paiement',
        'carte',
        # 'comptabilise',
    )

    readonly_fields = list_display + fields
    list_per_page = 50
    list_filter = [
        'article',
        CategorieFilter,
        'membre',
        'carte',
        ('date_time', DateRangeFilter),
        'moyen_paiement',
        'table',
        # 'comptabilise',
    ]

    # actions = [send_to_odoo, ]

    # default_filters = ('pos__id__exact=48',)

    def has_delete_permission(self, request, obj=None):
        group_compta, created = Group.objects.get_or_create(name="comptabilite")
        return group_compta in request.user.groups.all()

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True


staff_admin_site.register(ArticleVendu, ArticlesVendusAdmin)


class CouleurAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_fr', 'hexa')
    fields = ('name', 'name_fr', 'hexa')
    search_fields = ('name', 'name_fr', 'hexa')


staff_admin_site.register(Couleur, CouleurAdmin)


class AppareilAdmin(admin.ModelAdmin):
    fields = ('name',)

    list_display = (
        'name',
        'pin_code',
        'actif',
        'user',
        'last_login',
        'ip_lan',
        'periph',
    )

    # list_display_links = None
    list_editable = ('actif',)

    def save_model(self, request, instance, form, change, *args, **kwargs):
        if not instance.name:
            messages.add_message(request, messages.ERROR,
                                 _(f"Le nom du modèle est obligatoire. Merci de le renseigner."))
            return None

        config = Configuration.get_solo()
        if not config.discovery_key:
            # C'est le premier appairage, serveur tout neuf et non déclaré :
            # Génération de la clé discovery
            try:
                declaration_to_discovery_server()
                # La clé API du serveur discovery a été généré
                config.refresh_from_db()
            except Exception as e:
                messages.add_message(request, messages.ERROR, _(f"declaration_to_discovery_server erreur : {e}"))
                return None

        # Scenario : Atif était coché et on le décoche. On desactive tout.
        # On supprime la liaison avec l'utilisateur et on le rend inactif
        if not instance.actif and form.initial.get('actif'):
            if instance.user:
                instance.user.is_active = False
                instance.user.is_superstaf = False
                instance.user.public_pem = None
                instance.user.save()
            instance.user = None
            instance.pin_code = None
            messages.add_message(request, messages.WARNING, _(f"Desactivation du terminal {instance.name}"))

        # Scenario : Le code pin est présent, on active le terminal avec new_hadware, pas a la main
        # Si on coche actif a la main, on renvoi une erreur, le perif doit s'activer avec new_hardware
        if instance.actif and not form.initial.get('actif') and instance.pin_code:
            messages.add_message(request, messages.ERROR,
                                 _(f"Activation manuelle du terminal {instance.name} impossible : "
                                   f"Entrez le code pin sur l'interface du terminal."))
            return False

        # Scenario : On coche actif alors qu'il a été désactivé avant.
        # On a pas de code pin, on va en refabriquer un
        if instance.actif and not form.initial.get('actif') and not instance.pin_code:
            messages.add_message(request, messages.WARNING, _(f"RE - Activation du terminal {instance.name}"))
            instance.actif = False

        # Scénario création de l'objet depuis l'admin. Nom OK
        # On va chercher le code pin sur le serveur primaire
        if not form.initial.get('actif'):
            try:
                pin_code = get_pin_on_appareillage(instance.name)
                instance.pin_code = pin_code
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     _(f"Erreur lors de la récupération du code pin, contactez l'administrateur : {e}"))
                return None

        super().save_model(request, instance, form, change)


staff_admin_site.register(Appareil, AppareilAdmin)


class PrinterAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'thermal_printer_adress',
        'serveur_impression',
        'revoquer_odoo_api_serveur_impression',
    )

    readonly_fields = (
        '_api_serveur_impression',
    )

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'thermal_printer_adress',
                'serveur_impression',
                'api_serveur_impression',
                'revoquer_odoo_api_serveur_impression',
            )
        }),
    )

    def save_model(self, request, instance, form, change):
        if instance.revoquer_odoo_api_serveur_impression:
            instance.api_serveur_impression = None
            instance.revoquer_odoo_api_serveur_impression = False
        super().save_model(request, instance, form, change)

    def get_fieldsets(self, request, obj=None):

        # Append replace here instead of using self.exclude.
        # When fieldsets are defined for the user admin, so self.exclude is ignored.
        if obj:
            fieldsets = deepcopy(super().get_fieldsets(request, obj))
            replace = {}
            if obj.api_serveur_impression:
                replace = {'api_serveur_impression': '_api_serveur_impression'}

            # Iterate fieldsets
            for fieldset in fieldsets:
                fieldset_fields = fieldset[1]['fields']

                # Remove excluded fields from the fieldset
                for value, key in enumerate(replace):
                    if key in fieldset_fields:
                        # import ipdb; ipdb.set_trace()
                        fieldset_fields_list = [field for field in fieldset_fields if field != key]  # Filter
                        fieldset_fields_list.append(replace[key])
                        fieldset_fields = tuple(fieldset_fields_list)
                        fieldset[1]['fields'] = fieldset_fields  # Store new tuple

            return fieldsets

        return [(None, {'fields': self.get_fields(request, obj)})]


staff_admin_site.register(Printer, PrinterAdmin)


class ConfigurationAdmin(SingletonModelAdmin):
    # form = CustomConfigForm

    readonly_fields = [
        'key',
        'key_billetterie',
        'monnaie_principale',
        'monnaie_principale_cadeau',
        'monnaie_principale_ardoise',
        'moyen_paiement_espece',
        'moyen_paiement_cb',
        'moyen_paiement_mollie',
        'moyen_paiement_oceco',
        'moyen_paiement_commande',
        'moyen_paiement_fractionne',
        'pin_code_primary_link',
        # 'monnaies_acceptes',
        'methode_vente_article',
        'methode_ajout_monnaie_virtuelle',
        'methode_ajout_monnaie_virtuelle_cadeau',
        'methode_paiement_fractionne',
        'methode_adhesion',
        'methode_retour_consigne',
        'methode_vider_carte',
        'last_log_odoo',
        '_odoo_api_key',
        'federated_with',
        '_onboarding',
        '_cle_dokos',
    ]

    fieldsets = (
        (None, {
            'fields': (
                'structure',
                'url_image',
                'siret',
                'adresse',
                'email',
                'pied_ticket',
                'telephone',
                'numero_tva',
                'taux_tva',
                'fuseau_horaire',
                'horaire_ouverture',
                'horaire_fermeture',
            )
        }),
        ('Options', {
            'fields': (
                ('appareillement', 'pin_code_primary_link',),
                'validation_service_ecran',
                'remboursement_auto_annulation',
                # 'domaine_cashless',
                'ip_cashless',
            ),
        }),
        ('Adhésion', {
            'fields': (
                'prix_adhesion',
                'calcul_adhesion',
                # 'adhesion_suspendue',
            ),
        }),
        ('Ticket Z', {
            'fields': (
                'compta_email',
                'cash_float',
                'cloture_de_caisse_auto',
                'ticketZ_printer',
            ),
        }),
        # ('Billetterie', {
        #     'fields': (
        # 'key_billetterie',
        # 'billetterie_ip_white_list',
        # 'billetterie_url',
        # 'revoquer_key_billetterie',
        # ),
        # }),
        ('OCECO', {
            'fields': (
                'valeur_oceco',
                'key',
                'oceco_ip_white_list',
                'revoquer',
            ),
        }),
        ('Cashback', {
            'fields': (
                'cashback_active',
                'cashback_start',
                'cashback_value',
            ),
        }),
        # ('Badgeuse', {
        #     'fields': (
        #         'badgeuse_active',
        #     ),
        # }),
        ('Fidelity', {
            'fields': (
                'fidelity_active',
                'fidelity_asset_trigger',
                'fidelity_asset',
                'fidelity_factor',
            ),
        }),
        ('Odoo', {
            'fields': (
                'odoo_url',
                'odoo_database',
                'odoo_login',
                'odoo_api_key',
                'journal_out_invoice',
                'journal_odoo_espece',
                'journal_odoo_cb',
                'journal_odoo_stripe',
                (
                    'odoo_send_membership',
                    'odoo_create_invoice_membership',
                    'odoo_set_payment_auto',
                ),
                'last_log_odoo',
                'revoquer_odoo_api_key',

            ),
        }),
        ('Dokos', {
            'fields': (
                'dokos_url',
                'dokos_key',
                'dokos_id',
                'revoquer_dokos',
            ),
        }),
        ('Federation', {
            'fields': (
                # 'string_connect',
                'monnaies_acceptes',
                'federated_with',
            ),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if form.base_fields.get('monnaies_acceptes'):
            # On filtre les monnaies acceptée
            form.base_fields['monnaies_acceptes'].queryset = (
                form.base_fields['monnaies_acceptes'].queryset.filter(categorie__in=[
                    MoyenPaiement.LOCAL_EURO,
                    MoyenPaiement.LOCAL_GIFT,
                    MoyenPaiement.EXTERIEUR_FED,
                    MoyenPaiement.EXTERIEUR_GIFT,
                    MoyenPaiement.STRIPE_FED,
                ]))

        # On ajoute les assets FIDELITY
        if form.base_fields.get('fidelity_asset_trigger'):
            form.base_fields['fidelity_asset_trigger'].queryset = (
                # Ne pas accepter le point de fildélité comme trigger de lui même
                form.base_fields['fidelity_asset_trigger'].queryset.exclude(categorie__in=[
                    MoyenPaiement.FIDELITY,
                    MoyenPaiement.EXTERNAL_FIDELITY,
                ]))

        if form.base_fields.get('fidelity_asset'):
            form.base_fields['fidelity_asset'].queryset = (
                form.base_fields['fidelity_asset'].queryset.filter(categorie__in=[
                    MoyenPaiement.FIDELITY,
                    MoyenPaiement.EXTERNAL_FIDELITY,
                ]))

        return form

    def save_model(self, request, instance: Configuration, form, change):
        # if (not form.initial.get('badgeuse_active')
        #         and instance.badgeuse_active):
        # On passe de False à True
        # badgeuse_creation()

        # obj.user = request.user
        ex_api_key = None
        if instance.revoquer:
            if instance.key:
                ex_api_key = APIKey.objects.get(id=instance.key.id)
                instance.key = None
                messages.add_message(request, messages.WARNING, "API Key deleted")

            else:
                api_key = None
                key = " "
                # On affiche le string Key sur l'admin de django en message
                # et django.message capitalize chaque message...
                # Du coup, on fait bien gaffe à ce que je la clée générée ai bien une majusculle au début ...
                while key[0].isupper() == False:
                    api_key, key = APIKey.objects.create_key(name="oceco_key")
                    if key[0].isupper() == False:
                        api_key.delete()

                instance.key = api_key

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    _(f"Copiez bien la clé suivante et mettez la en lieu sur ! "
                      f"Elle n'est pas enregistrée sur nos serveurs et ne sera affichée qu'une seule fois ici :")
                )
                messages.add_message(
                    request,
                    messages.WARNING,
                    f"{key}"
                )

            instance.revoquer = False

        if instance.revoquer_odoo_api_key:
            instance.odoo_api_key = None
            instance.revoquer_odoo_api_key = False

        # if instance.revoquer_key_billetterie:
        #     if instance.key_billetterie:
        #         ex_api_key = APIKey.objects.get(id=instance.key_billetterie.id)
        #         instance.key_billetterie = None
        #         messages.add_message(request, messages.WARNING, "API Key deleted")
        #
        #     else:
        #         api_key = None
        #         key = " "
        #         # On affiche la string Key sur l'admin de django en message
        #         # et django.message capitalize chaque message...
        #         # du coup on fait bien gaffe à ce que je la clée générée ai bien une majusculle au début ...
        #         while key[0].isupper() == False:
        #             api_key, key = APIKey.objects.create_key(name="billetterie_key")
        #             if key[0].isupper() == False:
        #                 api_key.delete()
        #
        #         instance.key_billetterie = api_key
        #
        #         messages.add_message(
        #             request,
        #             messages.SUCCESS,
        #             _(f"Copiez bien la clé suivante et mettez la en lieu sur ! Elle n'est pas enregistrée sur nos serveurs et ne sera affichée qu'une seule fois ici :")
        #         )
        #         messages.add_message(
        #             request,
        #             messages.WARNING,
        #             f"{key}"
        #         )
        #
        #     instance.revoquer_key_billetterie = False

        ### DOKOS
        if instance.dokos_url and instance.dokos_key and instance.dokos_id:
            session = requests.Session()
            url = f"{instance.dokos_url}/api/method/venues_federation.api.v1/venues"
            headers = {
                'Authorization': f'token {instance.dokos_key}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            check_id_lieu = session.get(url, headers=headers)
            if check_id_lieu.status_code == 200:
                reponse = check_id_lieu.json()
                liste_ids = [message['identification'] for message in reponse['message']]
                if instance.dokos_id not in liste_ids:
                    logger.warning(f"{reponse}")
                    logger.warning(f"l'id du lieu ne correspond pas à l'identification : {liste_ids}")
                    messages.add_message(request, messages.ERROR,
                                         _("L'id du lieu ne correspond pas à un id de lieu connu : https://doc.dokos.io/federation-lieux/federation-de-lieux/api/"))

                messages.add_message(request, messages.SUCCESS, "Connexion Dokos OK")
            else:
                messages.add_message(request, messages.ERROR,
                                     _("Erreur de connexion à Dokos, vérifiez l'url et la clé API : https://doc.dokos.io/federation-lieux/federation-de-lieux/api/"))

        if instance.revoquer_dokos:
            instance.dokos_key = None
            instance.revoquer_dokos = False

        ### ODO
        if instance.odoo_url:
            # Test API
            odoo_api = OdooAPI(instance)
            try:
                odoo_api.test_login()
                messages.add_message(request, messages.INFO, "Login API Odoo OK. Please check account name")
            except Exception as e:
                messages.add_message(request, messages.ERROR, f"ODOO ERROR : {e}")

            # Vérification des journaux dans ODOO. On les affiche pour bien correspondre à la configuration.
            try:
                req, journaux = odoo_api.get_account_journal()
                messages.add_message(request, messages.INFO, f"{journaux}")
                journaux_ok = True
                for journal in [
                    instance.journal_out_invoice,
                    instance.journal_odoo_espece,
                    instance.journal_odoo_cb,
                    instance.journal_odoo_stripe]:
                    if not journal or journal not in journaux.keys():
                        messages.add_message(request, messages.ERROR,
                                             f"Error journal name. Please fill with : {journaux}")
                        journaux_ok = False

                if journaux_ok:
                    messages.add_message(request, messages.SUCCESS, "Journaux and Odoo config OK")

            except Exception as e:
                messages.add_message(request, messages.ERROR, f"ODOO ERROR : {e}")

        # On lance la connexion à la fédération FEDOW
        # if instance.string_connect and not instance.stripe_connect_account and not instance.onboard_url:
        #     handshake_with_fedow = handshake(instance, first_handshake=True)
        #
        #     if handshake_with_fedow:
        #         instance.fedow_place_admin_apikey = handshake_with_fedow['place_admin_apikey']
        #         # instance.fedow_place_wallet_public_pem = handshake_with_fedow['place_wallet_public_pem']
        #         instance.onboard_url = handshake_with_fedow['url_onboard']
        #         instance.fedow_domain = handshake_with_fedow['fedow_domain']
        #         instance.fedow_place_uuid = handshake_with_fedow['fedow_place_uuid']
        #         instance.fedow_place_wallet_uuid = handshake_with_fedow['fedow_place_wallet_uuid']
        #
        #         messages.add_message(request, messages.SUCCESS,
        #                              _("Connexion FEDOW réussie, merci de valider votre compte Stripe"))
        #     else:
        #         messages.add_message(request, messages.ERROR, f"Erreur handshake")
        #         instance.string_connect = None

        # Clé API OCECO
        if ex_api_key:
            ex_api_key.delete()
        cache.clear()

        from fedow_connect.fedow_api import FedowAPI
        fedowAPI = FedowAPI()
        # Verification des synchros asset fedelitée
        try:
            # TODO: Tester la fidelitée
            if instance.fidelity_active:
                fidelity, created = MoyenPaiement.objects.get_or_create(categorie=MoyenPaiement.FIDELITY,
                                                                        name="Fidelity")
                asset_serialized, created = fedowAPI.asset.get_or_create_asset(fidelity)
                messages.add_message(request, messages.SUCCESS, "Asset Fidelity OK")
        except Exception as e:
            messages.add_message(request, messages.ERROR, _(f"Fedow non connecté. Asset non mis à jour : {e}"))

        try:
            # Mise à jour des assets Fedow
            fedowAPI.place.get_accepted_assets()
            messages.add_message(request, messages.SUCCESS, _("Mise à jour des assets Fedow OK"))
        except Exception as e:
            messages.add_message(request, messages.ERROR, _(f"Fedow non connecté. Asset non mis à jour : {e}"))

        super().save_model(request, instance, form, change)

    def get_fieldsets(self, request, obj: Configuration = None):
        if obj:
            fieldsets = deepcopy(super().get_fieldsets(request, obj))

            # Append replace here instead of using self.exclude.
            # When fieldsets are defined for the user admin, so self.exclude is ignored.
            replace = {}

            if obj.dokos_key:
                replace['dokos_key'] = '_cle_dokos'

            # Obfuscation de la clé API
            if obj.odoo_api_key:
                replace['odoo_api_key'] = '_odoo_api_key'

            # Wizard de connexion à la fédération
            # 1 - On demande la string généré par Fedow lors de la création d'un nouveau lieu
            # 2 - Nouvelles clé API et génération de clé publique RSA entre serveurs
            # 3 - Génération du lien onboard Stripe Connect qui vérifie l'identité
            # if obj.string_connect:
            #     if obj.onboard_url and not obj.stripe_connect_account:
            #         replace['string_connect'] = '_onboarding'
            # elif obj.stripe_connect_valid:
            #     replace['string_connect'] = 'federated_with'

            # Iterate fieldsets
            for fieldset in fieldsets:
                fieldset_fields = fieldset[1]['fields']

                # Remove excluded fields from the fieldset
                for value, key in enumerate(replace):
                    if key in fieldset_fields:
                        # import ipdb; ipdb.set_trace()
                        fieldset_fields_list = [field for field in fieldset_fields if field != key]  # Filter
                        fieldset_fields_list.append(replace[key])
                        fieldset_fields = tuple(fieldset_fields_list)
                        fieldset[1]['fields'] = fieldset_fields  # Store new tuple

            return fieldsets

        return [(None, {'fields': self.get_fields(request, obj)})]


staff_admin_site.register(Configuration, ConfigurationAdmin)


# noinspection PyUnusedLocal
def liberer_la_table(modeladmin, request, queryset):
    queryset.update(statut=Table.LIBRE)


liberer_la_table.short_description = _("Libérer les tables selectionnées")


class TablesAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = (
        'poids',
        'name',
        'reste_a_payer',
        'statut',
        'archive',
    )
    ordering = ('poids',)
    actions = [liberer_la_table, ]
    list_editable = ('archive', 'statut')
    list_display_links = ('name',)
    list_filter = ('archive',)

    def has_delete_permission(self, request, obj=None):
        return False
    # def get_queryset(self, request):
    #     qs = super(TablesAdmin, self).get_queryset(request)
    #     return qs.filter(archive=False)


staff_admin_site.register(Table, TablesAdmin)


class TauxTVAadmin(admin.ModelAdmin):
    list_display = ('name', 'taux')


staff_admin_site.register(TauxTVA, TauxTVAadmin)


class GroupementCategorieAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'str_categories',
        'icon',
        'qty_ticket',
        'printer',
    )
    list_editable = ('icon', 'qty_ticket', 'printer',)

    def str_categories(self, obj):
        return str([categrorie.name for categrorie in obj.categories.all()])

    str_categories.short_description = _("Catégories")

    # pour retirer le petit bouton plus a coté des champs article
    def get_form(self, request, obj=None, **kwargs):  # Just added this override
        form = super(GroupementCategorieAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['categories'].widget.can_add_related = False
        return form


staff_admin_site.register(GroupementCategorie, GroupementCategorieAdmin)


class GroupementCategorieFilter(SimpleListFilter):
    title = _('groupement pour préparation')
    parameter_name = 'article__categorie__groupements__name'

    def lookups(self, request, model_admin):

        groupes = GroupementCategorie.objects.all()
        tuples_list = []
        for groupe in groupes:
            t = (groupe.name, groupe.name.capitalize())
            tuples_list.append(t)

        return tuples_list

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        else:
            return queryset.filter(article__categorie__groupements__name=self.value())

#
# def recalculer_la_tva(modeladmin, request, queryset):
#     for rapport in queryset:
#         debut_event, fin_event = start_end_event_4h_am(rapport.date)
#
#         article_vendus = ArticleVendu.objects.filter(
#             date_time__gte=debut_event,
#             date_time__lte=fin_event,
#         )
#         for article in article_vendus:
#             if article.article:
#                 if article.article.categorie:
#                     if article.article.categorie.tva:
#                         article.tva = article.article.categorie.tva.taux
#                         article.save()
#
#         ticketZ = TicketZ(rapport)
#         ticketZ.calcul_valeurs()
#
#
# recalculer_la_tva.short_description = _("Recalculer la tva en fonction des catégories d'articles.")
#

def update(modeladmin, request, queryset):
    for cloture in queryset:
        cloture: ClotureCaisse
        start, end = cloture.start, cloture.end
        ticketZ = TicketZ(start_date=start, end_date=end)
        if ticketZ.calcul_valeurs():
            ticketz_json = ticketZ.to_json
            cloture.ticketZ = ticketz_json
            cloture.save()


# Au lieux d'afficher les fields ordinaire, on affiche le template ticketZ
class ClotureCaisseChangeList(ChangeList):
    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)
        return f'/rapport/TicketZFromCloture/{pk}'


def reprint_ticketz(modeladmin, request, queryset):
    # import ipdb; ipdb.set_trace()
    for cloture in queryset:
        to_printer = ticketZ_tasks_printer.delay(cloture.ticketZ)


class ClotureCaisseAdmin(admin.ModelAdmin):
    list_display = (
        'categorie',
        'start',
        'end',
        'buttons_actions',
        'datetime',
    )
    list_filter = (
        'categorie',
        'datetime',
        ('start', DateRangeFilter),
        ('end', DateRangeFilter),
    )
    actions = [reprint_ticketz, update]

    list_display_links = None
    ordering = ('-start',)

    def get_changelist(self, request, **kwargs):
        self.uri = request.build_absolute_uri()
        self.root = request.user.is_superuser
        return ClotureCaisseChangeList

    def buttons_actions(self, obj):
        html = f'<a class="button" href="/rapport/RapportFromCloture/{obj.pk}">Rapport</a>&nbsp;' \
               f'<a class="button" href="/rapport/TicketZsimpleFromCloture/{obj.pk}">Ticket Z</a>&nbsp;' \
               f'<a class="button" href="/rapport/ClotureToPrinter/{obj.pk}?next={self.uri}">-> Thermal Print</a>&nbsp;' \
               f'<a class="button" href="/rapport/ClotureToMail/{obj.pk}?next={self.uri}">-> Mail</a>&nbsp;'

        if self.root:
            html += f'<a class="button" href="/rapport/RecalculerCloture/{obj.pk}?next={self.uri}">-> Reload</a>&nbsp;'
        return format_html(html)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    buttons_actions.short_description = 'Actions'


staff_admin_site.register(ClotureCaisse, ClotureCaisseAdmin)
