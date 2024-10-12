import csv
import json
import logging
from uuid import uuid4

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _
from jet.admin import CompactInline
from jet.filters import DateRangeFilter

from APIcashless.models import CarteCashless, Membre, ArticleVendu, Configuration, \
    PointDeVente, Articles
from fedow_connect.fedow_api import FedowAPI
from fedow_connect.tasks import set_primary_card

logger = logging.getLogger(__name__)


class ExportCsvMixin:
    def export_as_csv(self: admin.ModelAdmin, request, queryset):
        meta = self.model._meta
        exclude = ['id', 'ajout_cadeau_auto', 'adhesion_auto_espece', 'adhesion_auto_cb', 'comptabilise']
        field_names = [field.name for field in meta.fields if field.name not in exclude]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = _("Exporter la sélection")


class PresenceFilter(DateRangeFilter):
    '''
    Modification du DateRagngeFilter pour checker dans les articles vendus plutot que dans membre
    afin de chercher les personnes présente lors d'une date donnée.
    Ajoute aussi les membres dont la dernière action est dans la date.
    '''

    def queryset(self, request, queryset):
        if self.form.is_valid():
            validated_data = dict(self.form.cleaned_data.items())
            print(f"validated_data {validated_data}")
            if validated_data:
                original_queryset = queryset.filter(
                    **self._make_query_filter(request, validated_data)
                )

                ArticlesVendus = ArticleVendu.objects \
                    .filter(date_time__date__gte=validated_data['last_action__range__gte']) \
                    .filter(date_time__date__lte=validated_data['last_action__range__lte'])
                print(f"ArticlesVendus : {len(ArticlesVendus)}")

                membre_id = [p.membre.id for p in ArticlesVendus if p.membre]
                membres = Membre.objects.filter(id__in=membre_id)
                print(f"membres : {len(membres)}")

                merge = original_queryset | membres

                return merge.distinct()

        return queryset


class CarteMaitresseAdmin(admin.ModelAdmin):
    fields = (
        'carte',
        'points_de_vente',
        'edit_mode',
    )
    list_display = ('membre', 'carte', 'points_de_ventes', 'edit_mode', 'datetime')
    list_editable = ('edit_mode',)
    list_filter = ['points_de_vente', 'carte', 'carte__membre']

    # pour retirer le petit bouton plus a coté des champs pos et carte
    def get_form(self, request, obj=None, **kwargs):  # Just added this override
        form = super(CarteMaitresseAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['points_de_vente'].widget.can_add_related = False
        form.base_fields['carte'].widget.can_add_related = False
        form.base_fields['carte'].widget.can_change_related = False
        return form

    def save_model(self, request, instance, form, change):
        if instance.carte:
            # informe the card is primary to Fedow
            set_primary_card.delay(instance.carte.pk)

        if instance.carte.membre:
            messages.add_message(
                request,
                messages.SUCCESS,
                _("Carte Primaire OK")
            )


        else:
            messages.add_message(
                request,
                messages.ERROR,
                _(f"Attention : cette carte n'a pas de membre associé.")
            )
        super().save_model(request, instance, form, change)


def email_minuscule(modeladmin, request, queryset):
    for membre in queryset:
        if membre.email:
            membre.email = membre.email.lower()
            membre.save()


email_minuscule.short_description = _("email en minuscule")


def inverse_nom_prenom(modeladmin, request, queryset):
    for membre in queryset:
        name = membre.prenom.upper()
        prenom = membre.name.capitalize()

        membre.name = name
        membre.prenom = prenom

        membre.save()


inverse_nom_prenom.short_description = _("Inverser nom et prénom")


def separer_nom_prenom(modeladmin, request, queryset):
    # import ipdb; ipdb.set_trace()
    for membre in queryset:
        if not membre.prenom or membre.prenom == "None":
            prenom = f"{membre.name}".split(' ')[-1].capitalize()
            name = " ".join(f"{membre.name}".split(' ')[:-1]).upper()

            membre.name = name
            membre.prenom = prenom
            membre.save()


separer_nom_prenom.short_description = _("Séparer le prénom du nom")



#
# class CarteCashlessInline(CompactInline):
#     model = CarteCashless
#     fields = (
#         'number',
#         'tag_id',
#         'uuid_qrcode',
#     )
#     readonly_fields = fields
#     max_num = 1
#     extra = 0

    # def has_add_permission(self, request, obj=None):
        # return False
    # template = 'jet_custom/edit_inline/compact.html'


class CustomMembreForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # pour évier les doublons dans les mails !
        # self.fields['email'].widget.attrs['style'] = "text-transform: lowercase;"
        self.fields['name'].widget.attrs['style'] = "text-transform: uppercase;"
        self.fields['prenom'].widget.attrs['style'] = "text-transform: capitalize;"

    nouvelle_carte_cashless = forms.ModelChoiceField(
        queryset=CarteCashless.objects.filter(membre__isnull=True),
        required=False,
        label=_("Nouvelle carte cashless"),
        help_text="<span style='color: #6f7e95'>" +
                  _("Ajouter une carte cashless à ce membre. ") +
                  "</br>" +
                  _("Onglet CARTE CASHLESS pour voir toutes les cartes de ce membre. ↑") +
                  "</span>",
    )


    def save(self, commit=True):
        instance: Membre = super().save(commit=False)
        logger.info(f'{instance} = super().save(commit=False)')
        # Prepare a 'save_m2m' method for the form,
        # pour le bouton nouvelle carte directement sur la premier onglet, sans inline.
        if self.cleaned_data:
            carte: CarteCashless = self.cleaned_data.get('nouvelle_carte_cashless')
            if carte:
                old_save_m2m = self.save_m2m

                def save_m2m():
                    old_save_m2m()
                    instance.CarteCashless_Membre.add(carte)

                self.save_m2m = save_m2m

            if not carte:
                all_carte = instance.CarteCashless_Membre.all()
                if len(all_carte) > 0:
                    carte = all_carte[0]


        logger.info(f'{instance} if commit {commit}')
        if commit:
            instance.save()
            self.save_m2m()

        return instance

    def full_clean(self):
        super().full_clean()



class MembresAdmin(admin.ModelAdmin):
    form = CustomMembreForm
    # change_list_template = 'bouton_all_page/change_list_bouton_all_page.html'

    # radio_fields = {"paiment_adhesion": admin.HORIZONTAL}
    fieldsets = (
        (None, {
            'fields': (
                ('name', 'prenom'),
                # 'pseudo',
                # 'email',
                'nouvelle_carte_cashless',
                'commentaire',
                'numero_carte',
            )
        }),
    )

    list_display = ('_name',
                    'prenom',
                    'numero_carte',
                    # 'email',
                    # 'date_derniere_cotisation',
                    'date_ajout',
                    # 'commentaire',
                    'derniere_presence',
                    # 'adhesion_origine',
                    )

    readonly_fields = ('date_ajout','numero_carte')

    search_fields = ['name',
                     'prenom',
                     'email',
                     'commentaire',
                     'CarteCashless_Membre__number']

    list_filter = [
        ('last_action', PresenceFilter),
        ('date_ajout', DateRangeFilter),
        # ('date_derniere_cotisation', DateRangeFilter),
    ]

    list_per_page = 20
    actions = [inverse_nom_prenom, separer_nom_prenom, email_minuscule]


class CashlessFilter(SimpleListFilter):
    """
    This filter is being used in django admin panel in profile model.
    """
    title = _('Type')
    parameter_name = 'article__methode'

    def lookups(self, request, model_admin):
        return (
            ('cashless', _('Cashless')),
            ('no_cashless', _('Articles')),
            ('all', _('Tout')),
        )

    def queryset(self, request, queryset):
        config = Configuration.get_solo()
        if not self.value():
            return queryset.exclude(article__methode=config.methode_paiement_fractionne)
        if self.value().lower() == 'all':
            return queryset.exclude(article__methode=config.methode_paiement_fractionne)
        if self.value().lower() == 'no_cashless':
            return queryset.filter(article__methode=config.methode_vente_article)
        elif self.value().lower() == 'cashless':
            return queryset.filter() \
                .exclude(article__methode=config.methode_vente_article) \
                .exclude(article__methode=config.methode_paiement_fractionne)


