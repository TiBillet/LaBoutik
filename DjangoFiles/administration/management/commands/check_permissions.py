from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):

        # def check_permission(apps, schema_editor):
        # se refferer au JET_SIDE_MENU_ITEMS dans settings.
        '''
        content_type = ContentType.objects.get_for_model(CarteCashless)
        p = Permission.objects.filter(
            content_type=content_type,
            )
        for x in p:
            print(x.codename)
        '''

        liste_permission_user_acceuil = [

            # TODO: Verifier que ça ne génère pas une faille.
            'add_cartecashless',
            'change_cartecashless',
            'view_cartecashless',

            'add_membre',
            'change_membre',
            'view_membre',

        ]

        liste_permission_user_staff = [

            # TODO: Verifier que ça ne génère pas une faille.
            'add_cartecashless',
            'change_cartecashless',
            'delete_cartecashless',
            'view_cartecashless',

            # TODO: Verifier que ça ne génère pas une faille.
            'change_assets',
            'view_assets',

            'add_membre',
            'change_membre',
            'delete_membre',
            'view_membre',

            'add_articles',
            'change_articles',
            'view_articles',

            'add_categorie',
            'change_categorie',
            'delete_categorie',
            'view_categorie',

            'add_groupementcategorie',
            'change_groupementcategorie',
            'delete_groupementcategorie',
            'view_groupementcategorie',

            'add_pointdevente',
            'change_pointdevente',
            'delete_pointdevente',
            'view_pointdevente',

            'add_table',
            'change_table',
            'delete_table',
            'view_table',

            # 'add_commandesauvegarde',
            'change_commandesauvegarde',
            # 'delete_commandesauvegarde',
            'view_commandesauvegarde',

            'change_articlevendu',
            'view_articlevendu',

            'add_cartemaitresse',
            'change_cartemaitresse',
            'delete_cartemaitresse',
            'view_cartemaitresse',

            'view_configuration',
            'change_configuration',

            'add_couleur',
            'change_couleur',
            'delete_couleur',
            'view_couleur',

            'change_configurationsgraphique',
            'view_configurationsgraphique',

            'add_appareil',
            'change_appareil',
            'delete_appareil',
            'view_appareil',

            'add_printer',
            'change_printer',
            'view_printer',

            'view_rapporttableaucomptable',
            'change_rapporttableaucomptable',

            'view_cloturecaisse',
            'change_cloturecaisse',

            'add_tauxtva',
            'change_tauxtva',
            'delete_tauxtva',
            'view_tauxtva',

            'view_tibiuser',
            'add_tibiuser',
            'change_tibiuser',
            'delete_tibiuser',
        ]

        # on clean les anciennes permissions:
        Permission.objects.all().delete()
        print('update_permissions')
        call_command('update_permissions')

        staff_group = Group.objects.get_or_create(name="staff")[0]
        for permission in liste_permission_user_staff:
            # print(permission)
            perm = Permission.objects.get(codename=permission)
            # print(perm)

            staff_group.permissions.add(perm)
        staff_group.save()

        compta_group = Group.objects.get_or_create(name="comptabilite")[0]
        for permission in liste_permission_user_staff:
            # print(permission)
            perm = Permission.objects.get(codename=permission)
            # print(perm)

            compta_group.permissions.add(perm)
        compta_group.save()

        acceuil_group = Group.objects.get_or_create(name="acceuil")[0]
        for permission in liste_permission_user_acceuil:
            # print(permission)
            perm = Permission.objects.get(codename=permission)
            # print(perm)

            acceuil_group.permissions.add(perm)

        acceuil_group.save()
