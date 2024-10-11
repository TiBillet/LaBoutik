import threading
from typing import List

from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import JsonResponse, HttpResponseNotFound, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAcceptable
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from APIcashless.models import *
# from APIcashless.views import get_client_ip
from Cashless.scripts_utiles.ip_utils import get_ip_user, get_client_ip
from administration.email_ticket import ticket_conso_jour
from administration.ticketZ import TicketZ
from epsonprinter.tasks import print_command_epson_tm20, ticketZ_tasks_printer
from fedow_connect.fedow_api import FedowAPI
from tibiauth.models import TibiUser
from webview.serializers import CarteCashlessSerializer, PointDeVenteSerializer, \
    TableSerializerWithCommand, GroupCategorieSerializer, TableSerializer, ConfigurationSerializer
from webview.validators import DataAchatDepuisClientValidator, PreparationValidator, LoginHardwareValidator, \
    NewPeriphPinValidator

logger = logging.getLogger(__name__)
from decimal import Decimal


def login_admin(request):
    user: TibiUser = request.user

    logger.info(f"User : {user.username}")
    # Si un modèle appareil est lié (One2One)
    if hasattr(user, 'appareil'):
        logger.error(f"Terminal user : {request.user.username}")
        return HttpResponseNotAllowed(['Terminal user not allowed', ])

    if request.method == 'POST':
        user = authenticate(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)

    # EN CAS DE DEBUG On va chercher le premier admin et on log :
    if settings.DEBUG:
        user = get_user_model().objects.filter(
            is_staff=True,
            is_superuser=False,
            appareil=None,
        ).first()
        if user:
            if user.is_staff:
                logger.warning(f"DEBUG MODE, on log automatiquement sur {user.username}")
                login(request, user)

    if not user or user.is_anonymous:
        logger.warning("User anonyme, redirect to login")
        return render(request, 'login.html', {'erreur': True})

    # Si l'user est staff
    if user.is_staff:
        logger.info(f"Staff user login successful : {user.username}")
        return redirect('/adminstaff')

    # Un utilisateur sans terminal et non staff ne devrait pas pouvoir arriver ici.
    # Todo : vérifier lorsqu'on supprime un appareil, l'user reste et peut permettre de se connecter ailleurs ?
    user.is_active = False
    user.save()
    logger.warning(f"User {user} sans appareil et non staff. Désactivé.")
    return HttpResponseNotAllowed("User not allowed, desactivated.")


@csrf_exempt
def new_hardware(request):
    new_perif_validator = NewPeriphPinValidator(data=request.POST, context={'request': request})
    if not new_perif_validator.is_valid():
        return JsonResponse(new_perif_validator.errors, status=status.HTTP_400_BAD_REQUEST)

    valid_data = new_perif_validator.validated_data
    appareil: Appareil = new_perif_validator.appareil

    User: TibiUser = get_user_model()
    user, created = User.objects.get_or_create(username=valid_data['username'])

    # Si un appareill existe déja sur l'user (created == False)
    if hasattr(user, 'appareil') and not created:
        ex_appareil: Appareil = user.appareil
        if ex_appareil.actif:
            return JsonResponse(
                {'msg': _("Appareil déja en cours d'utilisation. Désactivez le d'abord pour un nouvel appairage.")},
                status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_perif_validator.password)
    user.is_active = True
    user.public_pem = valid_data['public_pem']
    user.save()

    appareil.user = user
    appareil.pin_code = None
    appareil.ip_lan = valid_data['ip_lan']
    appareil.ip_wan = get_client_ip(request)
    appareil.user_agent = request.META.get('HTTP_USER_AGENT')
    appareil.claimed_at = timezone.now()
    appareil.periph = valid_data['periph']
    appareil.hostname = valid_data['hostname']
    appareil.version = valid_data['version']

    # Tache celery pour envoyer un mail de vérification à l'admin
    # via le signal.py si actif = True en post_save
    appareil.actif = True
    appareil.save()

    # Le code pin a été validé, on renvoie vers la page de login
    return JsonResponse({"msg": "ok"}, status=status.HTTP_201_CREATED)


def login_hardware(request):
    """
    Le login pour les machines, raspbery, smartphones, etc..
    :param request:
    :return: request ou json
    """
    if request.method == 'POST':
        # Le validator authentifie l'user avec username/password/signature
        login_hardware_validator = LoginHardwareValidator(data=request.POST, context={'request': request})
        if not login_hardware_validator.is_valid():
            return JsonResponse(login_hardware_validator.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = login_hardware_validator.validated_data
        # L'user a été authentitifié
        user: TibiUser = login_hardware_validator.user

        try:
            appareil: Appareil = user.appareil
        except Exception as e:
            # Un user existe mais l'appareil a été supprimé
            # TODO : supprimer l'user ?
            user.is_active = False
            user.save()
            return JsonResponse({"msg": _("Utilisateur non actif. Relancez l'appairage.")},
                                status=status.HTTP_401_UNAUTHORIZED)

        if user.is_active:
            appareil.ip_lan = validated_data['ip_lan']
            appareil.actif = True
            appareil.save()
            login(request, user)
            # return HttpResponseRedirect("/wv")
            return JsonResponse({"user_activation": "true"}, status=status.HTTP_200_OK)

        return JsonResponse({"msg": _("Utilisateur non actif. Relancez l'appairage.")},
                            status=status.HTTP_401_UNAUTHORIZED)
    # GET request :
    return render(request, 'login_hardware.html', {'language': settings.LANGUAGE_CODE})


# @csrf_exempt
# @api_view(['POST'])
class NfcReader(APIView):
    permission_classes = [AllowAny]

    @method_decorator(csrf_exempt)
    def post(self, request):

        hostname = request.POST.get('hostname', None)
        ip_lan = request.POST.get('ip_lan', None)
        uuid = request.POST.get('uuid', None)

        # Si hostname, la demande vient d'un lecteur pour sa création ou sa mise a jour d'ip
        if hostname:
            appareil, created = Appareil.objects.get_or_create(
                hostname=hostname, periph="SSF")

            if ip_lan:
                appareil.ip_lan = ip_lan
                appareil.save()
                return Response(f"{appareil.id}".split('-')[0], status=status.HTTP_201_CREATED)

        # Si uuid, demande vient d'un front pour avoir son ip
        if uuid:
            appareil = Appareil.objects.get(id__in=uuid, periph="SSF")
            if appareil.actif:
                return Response(appareil.ip_lan, status=status.HTTP_200_OK)
            else:
                return Response('Appareil non actif', status=status.HTTP_401_UNAUTHORIZED)

        return Response('Heing ?', status=status.HTTP_404_NOT_FOUND)


@login_required(login_url='/wv/login_hardware')
@api_view(['POST', 'GET'])
def index(request):
    # Si l'user n'est pas un appareil et que le mode démo n'est pas activé
    mode_demo: bool = settings.DEMO
    if not getattr(request.user, 'appareil', None) and not mode_demo:
        return HttpResponseNotFound(_(f"Terminal non appairé ou mode demo : {mode_demo}"))

    # print("----------------------------------------------")
    # print(f"-> request.method = {request.method}")
    # print("----------------------------------------------")

    if request.method == 'POST':
        # print("----------------------------------------------")
        # print(f"->data ={request.POST}")
        # print("----------------------------------------------")

        configuration = Configuration.get_solo()
        # valider la carte primaire
        if request.POST.get('type-action') == 'valider_carte_maitresse':
            tag_id_cm = request.POST.get('tag-id-cm').upper()

            try:
                carte_m = CarteMaitresse.objects.get(carte__tag_id=tag_id_cm)

            except CarteMaitresse.DoesNotExist:
                # TODO: Virer "erreur :1", passer en response REST
                return JsonResponse({"erreur": 1, "msg": "Carte non maitresse"})

            except Exception as e:
                logger.error(f"Erreur login carte primaire : {e}")
                raise e

            else:
                responsable = carte_m.carte.membre
                if responsable:
                    monnaie_principale_name = Configuration.objects.get().monnaie_principale.name
                    article_paiement_fractionne = Articles.objects.get(methode_choices=Articles.FRACTIONNE)
                    # noinspection PyDictCreation
                    data = {'data': PointDeVenteSerializer(carte_m.points_de_vente.all(), many=True).data,
                            'tables': TableSerializer(Table.objects.filter(archive=False), many=True).data,
                            'configuration': ConfigurationSerializer(Configuration.get_solo()).data,
                            'responsable': {},
                            'article_paiement_fractionne': f"{article_paiement_fractionne.pk}",
                            }

                    data['responsable']['nom'] = responsable.name,
                    data['responsable']['uuid'] = responsable.id
                    data['responsable']['edit_mode'] = False
                    if carte_m.edit_mode:
                        data['responsable']['edit_mode'] = True

                    data['monnaie_principale_name'] = monnaie_principale_name

                    return Response(data, status=status.HTTP_200_OK)
                else:
                    logger.error("/wv/index Carte sans nom !")
                    # TODO: Virer "erreur :1", utiliser Response
                    return JsonResponse(
                        {"erreur": 1, "msg": "Carte sans membre, ajoutez un responsable sur cette carte maitresse."})

    contexte = {
        'version': '0.9.10',
        'titrePage': _('Laboutik | Tibillet'),
        'demo': mode_demo,
        'time_zone': settings.TIME_ZONE,
        'demoTagIdCm': os.getenv("DEMO_TAGID_CM"),
        'demoTagIdClient1': os.getenv("DEMO_TAGID_CLIENT1"),
        'demoTagIdClient2': os.getenv("DEMO_TAGID_CLIENT2"),
        'demoTagIdTempsReponse': 1
    }

    return render(request, 'accueil.html', contexte)


@login_required
@api_view(['GET'])
def close_all_pos(request):
    if request.method == "GET":
        now = timezone.localtime()

        derniere_fermeture = ClotureCaisse.objects.all().order_by('-end').first()
        if not derniere_fermeture:
            # Aucune cloture de caisse.
            # On charge la datetime du matin :
            config = Configuration.get_solo()
            date_derniere_fermeture = datetime.combine(timezone.localdate(), config.cloture_de_caisse_auto,
                                                       tzinfo=timezone.get_current_timezone())
        else:
            date_derniere_fermeture = derniere_fermeture.end

        # On classe par ordre décroissant de temps ( le plus jeune en premier )
        # On prend le dernier, aka le plus vieux
        premiere_vente_apres_derniere_fermeture = ArticleVendu.objects.filter(
            date_time__gte=date_derniere_fermeture).order_by('-date_time').last()

        # import ipdb; ipdb.set_trace()

        # Aucune vente depuis la dernière fermeture,
        # on envoie la fermeture précédente
        if not premiere_vente_apres_derniere_fermeture:
            return Response({"message": "Aucune vente depuis la dernière fermeture."},
                            status=status.HTTP_206_PARTIAL_CONTENT)

        start_date = premiere_vente_apres_derniere_fermeture.date_time
        end_date = now

        # Génération du ticket Z
        ticketz_validator = TicketZ(start_date=start_date, end_date=end_date)
        if ticketz_validator.calcul_valeurs():
            ticketz_json = ticketz_validator.to_json

            ClotureCaisse.objects.create(
                ticketZ=ticketz_json,
                start=start_date,
                end=end_date,
                categorie=ClotureCaisse.CLOTURE,
            )

            config = Configuration.get_solo()
            to_printer = ticketZ_tasks_printer.delay(ticketz_json)
            if not config.ticketZ_printer:
                return Response({
                    "message": _(
                        "Caisses cloturées mais aucune imprimante selectionnée dans la configuration pour le Ticket Z.\n"
                        "Vous pouvez le ré-imprimer depuis l'interface d'administration.")},
                    status=status.HTTP_200_OK)

            return Response({"message": _("Caisses cloturées et ticket envoyé à l'impression")},
                            status=status.HTTP_200_OK)
        return Response({"message": _("Erreur génération du ticket Z")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
@api_view(['GET'])
def ticket_client(request, tagid):
    if request.method == "GET":
        carte = get_object_or_404(CarteCashless, tag_id=tagid)
        # ticket.print()

        if carte.membre:
            if carte.membre.email:
                ticket = ticket_conso_jour(carte, datetime.now())
                logger.info(f'on lance le thread email pour ticket_client {carte.membre.email}')
                thread_email = threading.Thread(target=ticket.to_mail)
                thread_email.start()
                logger.info(f'Thread email lancé pour ticket_client {carte.membre.email}')

                return Response(f"Mail envoyé sur {carte.membre.email}", status=status.HTTP_200_OK)
            else:
                return Response(f"Pas de mail sur la carte.", status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(f"Pas de membre sur la carte.", status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(['POST'])
def reprint(request):
    if request.method == 'POST':
        logger.info(f"reprint")

        uuid_commande = request.data.get('uuid_commande')
        str_pk_groupement = request.data.get('pk_groupement_categories')
        commande = get_object_or_404(CommandeSauvegarde, uuid=uuid_commande)
        groupement = get_object_or_404(GroupementCategorie, pk=str_pk_groupement)

        if groupement.printer:
            task = print_command_epson_tm20.delay(commande.pk, groupement_solo_pk=str_pk_groupement)

        return Response("reprint ok", status=status.HTTP_200_OK)


@login_required
@api_view(['POST', 'GET'])
def allOrders(request, *args, **kwargs):
    start = timezone.now()
    if request.method == 'GET':
        table = kwargs.get('table')
        commandes_classee_par_groupe = GroupCategorieSerializer(GroupementCategorie.objects.all(), many=True, table=kwargs.get('table'))

        data_cmd = commandes_classee_par_groupe.data
        logger.info(f"{timezone.now()} {timezone.now() - start} /wv/allOrders")
        print(f'data_cmd = ${data_cmd}')
        contexte = { 'data': data_cmd }

        return render(request, 'allOrders.html', contexte)


@login_required
@api_view(['POST', 'GET'])
def preparation(request, *args, **kwargs):
    start = timezone.now()
    if request.method == 'GET':
        table = kwargs.get('table')
        commandes_classee_par_groupe = GroupCategorieSerializer(GroupementCategorie.objects.all(), many=True,
                                                                table=kwargs.get('table'))

        data_cmd = commandes_classee_par_groupe.data
        logger.info(f"{timezone.now()} {timezone.now() - start} /wv/preparation GET table:{table}")
        return Response(data_cmd)

    if request.method == 'POST':
        validator = PreparationValidator(data=request.data)

        if validator.is_valid():

            data = validator.validated_data
            responsable: Membre = data['pk_responsable']
            carte_maitresse: CarteMaitresse = data['tag_id_cm']
            articles = data.get('articles')

            dict_message = {}
            dict_message['message'] = ""

            commande: CommandeSauvegarde = data.get('uuid_commande')

            for ligne_article in articles:
                article: Articles = ligne_article['pk']
                dec_qty = Decimal(ligne_article.get('qty'))
                for ligne_commande in commande.articles.all():
                    ligne_commande: ArticleCommandeSauvegarde
                    if ligne_commande.article == article:
                        if ligne_article.get('void'):
                            if responsable.is_gerant() and carte_maitresse.edit_mode:
                                logger.info(f"VOID ! {ligne_article}")
                                if ligne_commande.reste_a_servir >= dec_qty:
                                    ligne_commande.reste_a_servir -= dec_qty

                                if ligne_commande.reste_a_payer >= dec_qty:
                                    ligne_commande.reste_a_payer -= dec_qty

                                ligne_commande.qty -= dec_qty

                                # if ligne_commande.qty == 0:
                                #     ligne_commande.delete()
                                ligne_commande.save()
                                commande.check_statut()

                                # on check si l'article a déja été encaissé :
                                # Si oui, on crée une ligne négative pour laisser une trace et décrémenter
                                ligne_article_vendu_filter = ArticleVendu.objects.filter(article=article,
                                                                                         commande=ligne_commande.commande.uuid)
                                if len(ligne_article_vendu_filter) > 0:
                                    logger.info(f'article {article} déja vendu !')
                                    ligne_article_vendu: ArticleVendu = ligne_article_vendu_filter[0]
                                    ligne_article_vendu_negatif = ArticleVendu.objects.create(
                                        article=article,
                                        prix=article.prix,
                                        qty=-abs(dec_qty),
                                        pos=ligne_article_vendu.pos,
                                        carte=ligne_article_vendu.carte,
                                        membre=ligne_article_vendu.membre,
                                        moyen_paiement=ligne_article_vendu.moyen_paiement,
                                        responsable=responsable,
                                        commande=ligne_article_vendu.commande,
                                        table=ligne_article_vendu.table,
                                    )

                                    # Si l'article a été payé via carte cashless,
                                    # et si l'option est activée dans la config,
                                    # on rembourse automatiquement sur la carte :
                                    configuration = Configuration.get_solo()
                                    if ligne_article_vendu.moyen_paiement.blockchain \
                                            and ligne_article_vendu.carte \
                                            and configuration.remboursement_auto_annulation:

                                        carte: CarteCashless = ligne_article_vendu.carte
                                        logger.info(f"on rembourse sur la carte {carte}")
                                        asset = carte.assets.get(monnaie=ligne_article_vendu.moyen_paiement)
                                        asset.qty += article.prix * dec_qty
                                        asset.save()

                                        # on informe le client que sa carte a été remboursée :
                                        dict_message['message'] += f"La carte {carte.number}"

                                        if ligne_article_vendu.table:
                                            dict_message[
                                                'message'] += f", sur la table {ligne_article_vendu.table.name},"

                                        dict_message[
                                            'message'] += f" a été remboursée de {asset.qty} {asset.monnaie.name}.\n"

                                    if not configuration.remboursement_auto_annulation:
                                        dict_message[
                                            'message'] += f"{article.name} payé en {ligne_article_vendu.moyen_paiement} supprimés de la commande et comptabilisé, mais aucun remboursement automatique n'a été réalisé.\n"

                            else:
                                raise serializers.ValidationError(_("Carte maitresse non gérante."))

                        elif ligne_commande.reste_a_servir >= dec_qty:
                            ligne_commande.reste_a_servir -= dec_qty
                            ligne_commande.save()
                        else:

                            raise serializers.ValidationError(_("reste a servir < qty"))

                            # return Response("reste a servir < qty", status=status.HTTP_400_BAD_REQUEST )

            commandes_classee_par_groupe = GroupCategorieSerializer(GroupementCategorie.objects.all(), many=True)
            data_cmd = commandes_classee_par_groupe.data

            logger.info(f"{timezone.now()} {timezone.now() - start} /wv/preparation POST")
            # data_cmd.append(dict_message)
            return Response(data_cmd, status=status.HTTP_200_OK)

        else:
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(['POST'])
def check_carte(request):
    if request.method == 'POST':
        tag_id_request = request.data.get('tag_id_client').upper()

        # Methode FEDOW Uniquement, on va mettre a jour la carte
        try:
            fedowApi = FedowAPI()
            # CardValidator. Mets à jour les assets/tokens depuis Fedow
            serializer_from_fedow = fedowApi.NFCcard.retrieve(tag_id_request)
        except Exception as e:
            logger.error(f"Check carte FEDOW : {e}")
            data = {
                'background': '#e93363',
                'error_msg': _('Carte inconnue'),
            }
            return render(request, 'popup_check_carte.html', data)

        carte = CarteCashless.objects.get(tag_id=tag_id_request)
        serializer = CarteCashlessSerializer(carte)
        data = serializer.data

        data['serializer_from_fedow'] = serializer_from_fedow
        # On sépare les token pour l'affichage sur la table
        data['tokens_cashless'] = [token for token in serializer_from_fedow['wallet']['tokens'] if
                                   token['asset_category'] in ['TLF', 'TNF', 'FED']]
        data['tokens_membership'] = [token for token in serializer_from_fedow['wallet']['tokens'] if
                                     token['asset_category'] == 'SUB']

        # import ipdb; ipdb.set_trace()

        logger.info(f"/wv/check_carte POST {data}")

        data['background'] = '#b85521'  # FOND ORANGE
        if not serializer_from_fedow['is_wallet_ephemere']:  # We get an user
            # Check if the membership are OK
            if data['tokens_membership']:
                data['background'] = '#339448'  # FOND VERT

        # ancienne réponse
        # return Response(data, status=status.HTTP_200_OK)
        # print(f'-------- data = {data}')

        return render(request, 'popup_check_carte.html', data)


class Commande:
    def __init__(self, data):
        """

        :type data: validators.DataAchatDepuisClientValidator.validated_data
        ( OrderedDict )
        """
        self.configuration = Configuration.get_solo()
        #
        self.data: DataAchatDepuisClientValidator.validated_data = data

        # CARTE NFC ET ASSETS
        self.nfc_tag_id = data.get('tag_id', None)
        self.carte_db: CarteCashless = self.data.get('card', None)
        self.card2: CarteCashless = self.data.get('card2', None)

        self.payments_assets: List[Assets] = data.get('payments_assets')
        self.total_in_payments_assets: Decimal = data.get('total_in_payments_assets')

        # FEDOW : Liste des assets utilisés ou rechargés
        self.used_assets = {}
        self.refill_assets = {}

        self.reponse = {}
        self.total_vente_article = self._total_vente_article(data)
        self.point_de_vente = data.get('pk_pdv')
        self.moyen_paiement: MoyenPaiement = data.get('moyen_paiement')  # string
        self.table: Table = data.get('pk_table')
        self.nouvelle_table = data.get('nouvelle_table')
        self.commentaire = data.get('commentaire')
        self.responsable: Membre = data.get('pk_responsable')

        # Dans le cas d'une recharge Stripe, il peut ne pas y avoir de carte Primaire
        # TODO: a a jouter dans le serializer
        carte_responsable = CarteMaitresse.objects.filter(
            carte__membre=self.responsable).first()
        if carte_responsable:
            self.primary_card_fisrtTagId = carte_responsable.carte.tag_id
        else:
            # on prend la premiere carte primaire fabriquée
            self.primary_card_fisrtTagId = CarteMaitresse.objects.last().carte.tag_id

        # Au cas où la vente vient de l'extérieur
        # ex : recharge stripe fédéré depuis la billetterie :
        self.uuid_commande = data.get('uuid_commande_exterieur', uuid4())
        self.uuid_paiement = data.get('uuid_commande_exterieur', uuid4())

        self.manque = 0
        self.commande_sauvegardee_input = None
        self.nouvelle_commande_created = False
        self.nouvelle_commande = None
        self.service = self._service()
        self.ip_user = data.get('ip_user')

        # si c'est une nouvelle table, on renvoie le pk dans la réponse.
        if self.nouvelle_table:
            self.reponse['nouvelle_table'] = self.table.pk

        logger.info("\n__ COMMAND INIT __ COMMAND INIT __ COMMAND INIT __ COMMAND INIT __ COMMAND INIT __\n")

    # Créations des assets uniquement si nous en avons besoin :
    def asset_principal(self):
        for asset in self.payments_assets:
            if asset.monnaie.categorie == MoyenPaiement.LOCAL_EURO:
                return asset

        # Si on arrive ici, c'est qu'il n'y a pas d'asset local euro.
        # Alors qu'on le réclame pour une recharge : Creation.
        mp_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        asset_euro, created = self.carte_db.assets.get_or_create(monnaie=mp_local_euro)
        if created:
            logger.info(f"    Asset LOCAL EURO {asset_euro} créé")
        self.payments_assets.append(asset_euro)
        return asset_euro

    def asset_principal_cadeau(self):
        for asset in self.payments_assets:
            if asset.monnaie.categorie == MoyenPaiement.LOCAL_GIFT:
                return asset

        # Si on arrive ici, c'est qu'il n'y a pas d'asset local gift.
        # Alors qu'on le réclame pour une recharge : Creation.
        mp_local_gift = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        asset_gift, created = self.carte_db.assets.get_or_create(monnaie=mp_local_gift)
        if created:
            logger.info(f"    Asset GIFT {asset_gift} créé")
        self.payments_assets.append(asset_gift)
        return asset_gift

    def asset_stripe_primaire(self):
        # On récupère le wallet sérialisé par le validateur
        wallet = self.carte_db.get_wallet()
        serialized_wallet = self.data['wallets'][wallet.uuid]
        token_primaire_list = [token for token in serialized_wallet['tokens'] if token['asset']['is_stripe_primary'] ]
        if len(token_primaire_list)> 1:
            logger.error(f"Il ne peut y avoir qu'un seul token primaire. Contactez un administrateur FEDOW - {serialized_wallet}")
            raise Exception(f"Il ne peut y avoir qu'un seul token primaire. Contactez un administrateur FEDOW - {serialized_wallet}")
        qty_token_primaire = None
        for token in token_primaire_list:
            return token

        return None

    def validation(self):
        """
        Fonction appellée par la vue paiement une fois que l'instance de classe commande a été générée.
        :rtype: dict
        :return: retourne le dictionaire qui sera envoyé en JSON au client.
        """

        # Si carte cashless et
        # si Article methode = vente (Total vente article comptabilise que les articles vente ou fractionnés):

        # TODO: A déplacer dans le validator
        if self.carte_db:

            # TOTAL superieur au solde de la carte :
            if self.total_vente_article > 0 \
                    and self.total_vente_article > self.total_in_payments_assets:
                self.manque = self.total_vente_article - self.total_in_payments_assets

                # # Paiement avec deuxieme carte ?
                if self.card2:
                    total_in_card2 = self.card2.get_payment_assets().aggregate(Sum('qty'))['qty__sum'] or 0
                    # Oui, mais solde toujours inférieur :
                    self.reponse = {
                        'route': "transcation_nfc2_fonds_insuffisants",
                        'message': {
                            'msg': _("Fonds insuffisants sur deuxieme carte."),
                            'manque': f"{abs(self.manque)}"
                        }
                    }
                    logger.info(f"Fonds sur deuxieme carte ({total_in_card2}) insuffisants.")
                    return self.reponse

                self.reponse = {
                    'route': "transcation_nfc_fonds_insuffisants",
                    'carte': CarteCashlessSerializer(self.carte_db).data,
                    'message': {
                        'msg': _("Fonds insuffisants. Il manque"),
                        'manque': f"{self.manque}"
                    }
                }
                return self.reponse

        # On itère sur chaque article.
        for item in self.data.get('articles'):
            article: Articles = item.get('pk')
            qty = dround(item.get('qty'))

            # si ça fait partie d'une commande déja sauvegardé,
            # on met le même uuid de commande pour les articles vendus.
            commande_input = item.get('uuid_commande', None)
            if commande_input:
                self.uuid_commande = commande_input.uuid
                self.commande_sauvegardee_input = commande_input

            # A l'aide d'une fonction nommé comme la methode inscrite en db de chaque article.
            # On lance la fonction qui porte le nom methode_{methode} de l'article.
            fonction_paiement = getattr(self, f"methode_{article.methode_choices}")
            fonction_paiement(article, qty)

            # Si l'article fait partie d'une commande sauvegardée sur une table,
            # on décrémente de la commande de la table :
            if commande_input:
                commande: CommandeSauvegarde = commande_input
                # import ipdb; ipdb.set_trace()
                ligne_article_dans_commande = commande.articles.get(article=article)

                if ligne_article_dans_commande.reste_a_payer - qty >= 0:
                    ligne_article_dans_commande.reste_a_payer -= qty
                    ligne_article_dans_commande.save()
                else:
                    self.reponse['message'] = {
                        'msg': _(
                            f"Trop d'articles {article.name}."
                            f"Reste à payer : {ligne_article_dans_commande.reste_a_payer}."
                        )
                    }

        if self.nouvelle_commande_created:
            # Une nouvelle commande a été créée,
            # On lance l'impression de ticket.
            logger.info(f'{"*" * 30} self.nouvelle_commande_created {"*" * 30}')
            print_command_epson_tm20.delay(self.nouvelle_commande.pk)

        ### ENREGISTREMENT DES ASSETS
        # Si c'est un paiement cashless
        if self.carte_db:
            logger.info(f"\n\nSAUVEGARDE ASSET POST PAIEMENT CASHLESS")

            # Mise à jour les valeurs des assets de la carte
            # for asset in self.carte_nfc.assets:
            for asset in self.payments_assets:
                asset: Assets
                asset.save()
                logger.info(f"    Carte : {asset.carte.number} - {asset}")

            # Une fois tout les paiments passés, on met à jour les assets coté Fedow
            self._send_to_fedow_used_assets()
            self._send_to_fedow_refill_assets()

            self.reponse['carte'] = CarteCashlessSerializer(self.carte_db).data
            self.reponse['total_sur_carte_avant_achats'] = f"{dround(self.total_in_payments_assets)}" \
                if self.total_in_payments_assets > 0 else "0"
            # "0" pour éviter le moche 0.00

        logger.info(f"\n")

        self.reponse['somme_totale'] = f"{Decimal(self.total_vente_article)}"

        return self.reponse

    def _service(self):
        # Si il ya  déja des commandes ouvertes sur cette table, c'est le même service, meme groupe de client !
        if self.table:
            last_commande: CommandeSauvegarde = CommandeSauvegarde.objects \
                .exclude(statut=CommandeSauvegarde.SERVIE_PAYEE) \
                .exclude(statut=CommandeSauvegarde.ANNULEE) \
                .filter(table=self.table) \
                .last()

            if last_commande:
                return last_commande.service
            else:
                return uuid4()
        # sinon, on en génère un nouveau
        else:
            return uuid4()

    @staticmethod
    def _total_vente_article(data):
        """
        :rtype: Decimal
        :param data: Dictionnaire comportant le is_valid() de la requete POST
        :return: retourne le prix total des articles qui ont la methode vente ou fractionné
                afin de comparer si la carte à suffisement de crédit
        """
        total_vente_article = 0
        for item in data['articles']:
            article: Articles = item['pk']
            if article.methode_choices in [Articles.VENTE, Articles.FRACTIONNE]:
                # la quantitée peut être en virgule flotante ( 1€ x qty )
                qty = dround(item['qty'])
                prix = article.prix
                total_vente_article += dround((qty * prix))
        return dround(total_vente_article)

    def _to_db_article_vendu(self, article, qty, asset):

        ligne_article_vendu = ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            carte=asset.carte,
            membre=asset.carte.membre,
            moyen_paiement=asset.monnaie,
            responsable=self.responsable,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

        return ligne_article_vendu

    def _to_db_cash_cb(self, article, qty):
        ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            moyen_paiement=self.moyen_paiement,
            responsable=self.responsable,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

        self.reponse['route'] = f'transaction_{self.moyen_paiement.name.lower().replace(" ", "_")}'

    def _used_assets(self, asset, qty):
        if self.used_assets.get(asset):
            self.used_assets[asset] += qty
        else:
            self.used_assets[asset] = qty

    def _send_to_fedow_used_assets(self):

        # Mise à jour des tokens vers fedow :
        # import ipdb; ipdb.set_trace()
        # Dans le cas d'un paiement complementaire,
        # les assets peuvent venir de plusieurs cartes
        for asset, amount in self.used_assets.items():
            carte = asset.carte
            wallet = carte.get_wallet()

            # Valeur du token fedow. pour le comparer avec la valeur de l'asset décrémenté
            tokens = self.data['wallets'][wallet.uuid]['payment_tokens']

            if asset.monnaie.is_federated and tokens.get(asset.monnaie.pk):
                # Si la quantité de l'asset en DB est inférieur au token fedow,
                # Alors l'asset a été utilisé pour la dépense plus haut
                # Alors on pousse la transaction
                if amount <= tokens.get(asset.monnaie.pk):
                    # Mise à jour de Fedow
                    fedowAPI = FedowAPI()
                    signed_data = json.dumps({"data": signing.dumps(str(self.data))})
                    try:
                        post_data = {
                            "amount": int(amount * 100),
                            "metadata": signed_data,
                            "wallet": f"{wallet.uuid}",
                            "asset": f"{asset.monnaie.pk}",
                            "user_card_firstTagId": f"{carte.tag_id}",
                            "primary_card_fisrtTagId": self.primary_card_fisrtTagId,
                        }
                        logger.info(f"\n\nASSET TO FEDOW :")
                        logger.info(f"{asset.monnaie} -> {amount}")
                        logger.info(f"\n")

                        serialized_transaction_w2w = fedowAPI.transaction.to_place(**post_data)

                        # Ajout du hash de BC dans les paiements
                        ArticleVendu.objects.filter(
                            uuid_paiement=self.uuid_paiement,
                            carte=carte,
                            moyen_paiement=asset.monnaie,
                        ).update(
                            hash_fedow=serialized_transaction_w2w['hash'],
                            sync_fedow=True,
                        )

                    except Exception as e:
                        logger.error(f"Erreur fedow : {e}")
                        raise NotAcceptable(detail=f"Erreur fedow : {e}", code=None)

                    # Vérification de la signature
                    data_signed = json.loads(serialized_transaction_w2w['metadata'])['data']
                    if str(self.data) != signing.loads(data_signed):
                        raise NotAcceptable(detail=f"Erreur de signature", code=None)

    def _refill_assets(self, asset, qty):
        if self.refill_assets.get(asset):
            self.refill_assets[asset] += qty
        else:
            self.refill_assets[asset] = qty

    def _send_to_fedow_refill_assets(self):
        for asset, amount in self.refill_assets.items():
            carte = asset.carte
            wallet = carte.get_wallet()

            fedowApi = FedowAPI()
            serialized_transaction = fedowApi.transaction.refill_wallet(
                amount=int(amount * 100),
                wallet=f"{wallet.uuid}",
                asset=f"{asset.monnaie.pk}",
                user_card_firstTagId=f"{self.carte_db.tag_id}",
                primary_card_fisrtTagId=self.primary_card_fisrtTagId,
            )

            # Ajout du hash de BC dans les paiements
            ArticleVendu.objects.filter(
                uuid_paiement=self.uuid_paiement,
                carte=carte,
            ).update(
                hash_fedow=serialized_transaction['hash'],
                sync_fedow=True,
            )

    def sauvegarde_commande_en_db(self, article, qty, article_paye_a_la_commande=False):
        # pas de paiement tout de suite. On sauvegarde la commande
        # import ipdb; ipdb.set_trace()

        logger.info(f'commande en attente {self.table.name}')

        nouvelle_commande, nouvelle_commande_created = CommandeSauvegarde.objects.get_or_create(
            uuid=self.uuid_commande,
            table=self.table,
            responsable=self.responsable,
            commentaire=self.commentaire,
            service=self.service,
        )

        if nouvelle_commande_created:
            self.nouvelle_commande = nouvelle_commande
            self.nouvelle_commande_created = True

        article_cree_dans_commande_sauvegardee = ArticleCommandeSauvegarde.objects.create(
            article=article,
            qty=qty,
            commande=self.nouvelle_commande,
        )

        if article_paye_a_la_commande:
            article_cree_dans_commande_sauvegardee.reste_a_payer = 0
            article_cree_dans_commande_sauvegardee.save()

        self.reponse['route'] = 'transaction_commande'

    def methode_BG(self, article, qty):
        carte = self.carte_db

        if not carte:
            logger.warning(f"methode_BG : pas de carte")
            raise NotAcceptable(detail=f"Pas de carte NFC", code=None)

        # if not carte.membre:
        #     logger.warning(f"methode_BG : pas de membre")
        #     raise NotAcceptable(detail=f"Pas de membre sur la carte", code=None)
        # if not carte.membre.email:
        #     logger.warning(f"methode_BG : pas de mail")
        #     raise NotAcceptable(detail=f"Pas de mail sur la carte", code=None)

        asset = article.subscription_fedow_asset

        if article.prix > 0:
            logger.warning(f"Article badge payant, en cours de dev.")
            raise NotAcceptable(detail=f"Pas de badge payant tout de suite :)", code=None)

        ligne_article_vendu = ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            carte=carte,
            membre=carte.membre,
            moyen_paiement=asset,
            responsable=self.responsable,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

    # FRACTIONNE = 'FR'
    def methode_FR(self, article, qty):

        if qty > 0:
            return_methode_vente = self.methode_VT(article, qty)

            # bug si paiement fractionné est en deux fois (1x token et 1x cadeau)
            self.sauvegarde_commande_en_db(article, -(abs(qty)))

            return return_methode_vente
        else:
            # TODO Return ne passe pas. TOUT PASSER EN API !!!
            return Response('Mauvaise QTY', status=status.HTTP_400_BAD_REQUEST)
        # self.methode_vente_article(article, qty)

    # VENTE = 'VT'
    def methode_VT(self, article, qty):
        # Si c'est une commande à payer plus tard ( type restauration ) :
        if self.moyen_paiement.categorie == MoyenPaiement.COMMANDE:
            self.sauvegarde_commande_en_db(article, qty)

        elif self.moyen_paiement.categorie in [
            MoyenPaiement.LOCAL_GIFT,  # n'arrive qu'en cas de mode gerant : offert
            MoyenPaiement.CASH,
            MoyenPaiement.CREDIT_CARD_NOFED,
            MoyenPaiement.CHEQUE,
        ]:
            if self.table \
                    and not self.commande_sauvegardee_input \
                    and article.methode_choices != Articles.FRACTIONNE:
                # nous avons une table, C'est un paiement direct après la commande.
                # mais pas de commande préalablement sauvegardée et récupérée par uuid_commande
                self.sauvegarde_commande_en_db(article, qty, article_paye_a_la_commande=True)

            self._to_db_cash_cb(article, qty)

        # si c'est un paiement par carte NFC :
        else:
            if self.table \
                    and not self.commande_sauvegardee_input \
                    and article.methode_choices != Articles.FRACTIONNE:
                # C'est un paiement direct après la commande,
                # nous avons une table,
                # mais pas de commande préalablement sauvegardée et récupérée par uuid_commande
                self.sauvegarde_commande_en_db(article, qty, article_paye_a_la_commande=True)

            # LA fonction de paiement !
            # On décrémente en fonction des assets présents dans la carte.
            # Cela peut provoquer des quantitées inférieures à 1 car
            # La moitié peut être payé en cadeau et l'autre en équivalent €, par exemple.
            reste = (article.prix * qty)
            self.used_asset = []
            while reste > 0:
                # assets = self.carte_nfc.assets
                assets = self.payments_assets
                for asset in assets:
                    logger.info(f"Il reste a payer pour {article.name} : {reste}")
                    logger.info(f"on test avec l'asset : {asset.monnaie.name} {asset.qty}")

                    # Il y a assez de monnaie dans l'asset
                    # pour payer en totalité ce qui reste
                    if asset.qty > 0 and asset.qty >= reste:

                        self._to_db_article_vendu(article, qty, asset)
                        # Ajout de l'asset dans la liste des assets utilisés
                        self._used_assets(asset, reste)
                        asset.qty += - reste
                        reste = 0
                        break

                    elif asset.qty > 0:
                        # Il reste un peu dans l'asset,
                        # mais pas assez pour tout payer
                        qty_payable = ((qty * asset.qty) / reste)
                        logger.info(f"    qty_payable : {qty_payable}")

                        self._to_db_article_vendu(article, qty_payable, asset)
                        # Ajout de l'asset dans la liste des assets utilisés
                        self._used_assets(asset, asset.qty)

                        reste += - asset.qty
                        qty = qty - qty_payable
                        asset.qty = 0

            self.reponse['route'] = "transaction_nfc"

    # RECHARGE_EUROS = 'RE'
    def methode_RE(self, article, qty):
        total = dround(article.prix * qty)
        reste = total
        self.total_vente_article += total

        # On va chercher l'asset principal de la carte.
        # S'il n'existe pas, cette fonction le créera.
        local_euro = self.asset_principal()
        local_euro.qty += reste

        self._refill_assets(local_euro, reste)

        ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            carte=self.carte_db,
            membre=self.carte_db.membre,
            responsable=self.responsable,
            moyen_paiement=self.moyen_paiement,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

        self.reponse['route'] = "transaction_ajout_monnaie_virtuelle"

    # RECHARGE CASHLESS MONNAIE EXTERIEUR FIDUCIAIRE NON CADEAU
    def methode_RF(self, article, qty):
        total = dround(article.prix * qty)
        reste = total
        self.total_vente_article += total

        # On va chercher l'asset correspondant à l'article de recharge
        asset_fedow: MoyenPaiement = article.subscription_fedow_asset
        if not asset_fedow:
            raise NotAcceptable("No fedow asset connected.")
        # Fabrication du token de la carte avec cet asset
        token_card, created = self.carte_db.assets.get_or_create(monnaie=asset_fedow)
        token_card.qty += reste

        self._refill_assets(token_card, reste)

        ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            carte=self.carte_db,
            membre=self.carte_db.membre,
            responsable=self.responsable,
            moyen_paiement=self.moyen_paiement,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

        self.reponse['route'] = "transaction_ajout_monnaie_virtuelle"

    # RECHARGE_CADEAU = 'RC'
    def methode_RC(self, article, qty):
        total = dround(article.prix * qty)
        # On va chercher l'asset gift.
        # S'il n'existe pas, cette fonction le créera.
        asset_principal_cadeau = self.asset_principal_cadeau()
        asset_principal_cadeau.qty += total

        self._refill_assets(asset_principal_cadeau, total)

        # sinon recharge prises en compte par rapport comptable
        moyen_paiement = self.moyen_paiement if self.moyen_paiement.categorie == MoyenPaiement.OCECO else None

        ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            carte=self.carte_db,
            membre=self.carte_db.membre,
            responsable=self.responsable,
            moyen_paiement=moyen_paiement,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

        self.reponse['route'] = "transaction_ajout_monnaie_virtuelle"

    # FIDELITY
    def methode_FD(self, article, qty):
        # On charge la carte
        asset_carte = self.carte_db.assets.get(monnaie__categorie=MoyenPaiement.FIDELITY)
        asset_carte.qty += qty

        # On informe fedow :
        self._refill_assets(asset_carte, qty)

        # Enregsitrement en DB
        art = ArticleVendu.objects.create(
            article=article,
            prix=article.prix,
            qty=qty,
            pos=self.point_de_vente,
            carte=self.carte_db,
            membre=self.carte_db.membre,
            responsable=self.responsable,
            moyen_paiement=None,  # sinon recharge prises en compte par rapport comptable
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )
        self.reponse['route'] = "transaction_ajout_fidelity"

    # ADHESIONS = 'AD'
    def methode_AD(self, article, qty):
        total = round((article.prix * qty), 2)
        carte_db: CarteCashless = self.carte_db
        self.total_vente_article += total
        primary_card_fisrtTagId = self.responsable.CarteCashless_Membre.first()
        if not carte_db:
            logger.error('methode_adhesion : Pas de carte')
            raise NotAcceptable(
                detail=_("Pas de carte."),
                code=None
            )

        # On permet de payer avec de la monnaie cashless, mais on vérifie quand même :
        if self.moyen_paiement.categorie == MoyenPaiement.LOCAL_EURO:
            # TODO: Accepter les monnaies cashless Locale Euro et Fedéré uniquement
            # vérifier le total wallet > prix adhésion & faire la transaction coté fédow
            raise NotAcceptable(
                detail=_("Travail en cours. "
                         "Désolé, les adhésions n'acceptent que espèce ou CB."),
                code=None
            )

        # Check carte fedow :
        fedowAPI = FedowAPI()
        fedow_serialized_card = fedowAPI.NFCcard.cached_retrieve(carte_db.tag_id)

        # Si wallet ephemère = pas d'email
        # if fedow_serialized_card.get('is_wallet_ephemere'):
        #     logger.error('methode_adhesion : Pas de membre sur cette carte')
        #     raise NotAcceptable(
        #         detail=_("Pas d'email lié sur cette carte.\n"
        #                "Merci de lier un email à cette carte en scannant son QRCode."),
        #         code=None
        #     )

        adh = fedowAPI.subscription.create_sub(
            wallet=f"{fedow_serialized_card['wallet']['uuid']}",
            amount=int(self.total_vente_article * 100),
            article=article,
            user_card_firstTagId=carte_db.tag_id,
            primary_card_fisrtTagId=primary_card_fisrtTagId.tag_id
        )

        # On va chercher l'adhérant
        # if carte_db.membre:
        #     adherant: Membre = carte_db.membre
        #
        #     # if adherant.a_jour_cotisation():
        #     #     raise NotAcceptable(
        #     #         detail=f"Le membre {adherant.name} à déja adhéré le {adherant.date_derniere_cotisation} "
        #     #                f"via l'interface : {adherant.choice_str(Membre.ORIGIN_ADHESIONS_CHOICES, adherant.adhesion_origine)}.",
        #     #         code=None
        #     #     )
        #
        #     aujourdhui = datetime.now().date()
        #     adherant.date_derniere_cotisation = aujourdhui
        #     adherant.cotisation = total
        #
        #     if not adherant.date_inscription:
        #         adherant.date_inscription = aujourdhui
        #
        #     adherant.save()

        if not adh['verify_hash']:
            raise NotAcceptable(
                detail="Erreur fédération.\n"
                       "Contactez un administrateur.",
                code=None
            )

        ArticleVendu.objects.create(
            article=article,
            prix=total,
            qty=1,
            pos=self.point_de_vente,
            carte=carte_db,
            membre=carte_db.membre,
            responsable=self.responsable,
            moyen_paiement=self.moyen_paiement,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
            hash_fedow=adh['hash'],
            sync_fedow=True,
        )

        # if not adherant and self.configuration.adhesion_suspendue:
        #     carte_db.adhesion_suspendue = True
        #     carte_db.save()
        #
        #     logger.warning('methode_adhesion : Pas de membre sur cette carte, on lance une adhesion suspendue')

    # RETOUR_CONSIGNE = 'CR'
    def methode_CR(self, article, qty):
        # def methode_CR(self, article, qty):

        total = round((article.prix * qty), 2)
        self.total_vente_article += total

        # si ce n'est pas un paiement par carte NFC :
        if self.moyen_paiement.categorie != MoyenPaiement.LOCAL_EURO:
            self._to_db_cash_cb(article, qty)

        # si c'est un paiement par carte NFC :
        elif self.moyen_paiement.categorie == MoyenPaiement.LOCAL_EURO:
            ### FEDOW ###
            wallet = self.carte_db.get_wallet()
            fedowApi = FedowAPI()
            asset_local_euro = MoyenPaiement.get_local_euro()
            serialized_transaction = fedowApi.transaction.refill_wallet(
                amount=int(abs(total) * 100),
                wallet=f"{wallet.uuid}",
                asset=f"{asset_local_euro.pk}",
                user_card_firstTagId=f"{self.carte_db.tag_id}",
                primary_card_fisrtTagId=self.primary_card_fisrtTagId,
            )

            asset_principal = self.asset_principal()
            asset_principal.qty += - total

            ArticleVendu.objects.create(
                article=article,
                prix=article.prix,
                qty=qty,
                pos=self.point_de_vente,
                carte=self.carte_db,
                membre=self.carte_db.membre,
                responsable=self.responsable,
                moyen_paiement=self.moyen_paiement,
                commande=self.uuid_commande,
                uuid_paiement=self.uuid_paiement,
                table=self.table,
                ip_user=self.ip_user,
            )

            self.reponse['route'] = "transaction_retour_consigne_nfc"

    # VIDER_CARTE = 'VC'
    def methode_VC(self, article, qty):
        asset_principal = self.asset_principal()
        # La monnaie euro locale
        ex_qty_token_local = abs(asset_principal.qty)

        # La monnaie fédérée :
        token_primaire = self.asset_stripe_primaire()
        ex_qty_token_primaire = dround(token_primaire['value'] / 100) if token_primaire else 0
        asset_primaire = MoyenPaiement.objects.get(
            pk=token_primaire['asset']['uuid'],
            categorie=MoyenPaiement.STRIPE_FED,
        ) if token_primaire else None

        ### FEDOW ###
        # On prévient Fedow qu'on vide la carte :
        fedowApi = FedowAPI()
        serialized_card_refunded = fedowApi.NFCcard.refund(
            user_card_firstTagId=f"{self.carte_db.tag_id}",
            primary_card_fisrtTagId=self.primary_card_fisrtTagId,
        )

        if ex_qty_token_primaire and asset_primaire :
            ArticleVendu.objects.create(
                article=article,
                prix=ex_qty_token_primaire,
                qty=1,
                pos=self.point_de_vente,
                carte=self.carte_db,
                membre=self.carte_db.membre,
                responsable=self.responsable,
                moyen_paiement=asset_primaire,
                commande=self.uuid_commande,
                uuid_paiement=self.uuid_paiement,
                table=self.table,
                ip_user=self.ip_user,
            )
        # Creation d'un article de vente
        # pour encaisser les asset primaire TiBillet Fédéré
        # avant de les rembourser.

        a_rembourser = abs(ex_qty_token_local + ex_qty_token_primaire)
        ArticleVendu.objects.create(
            article=article,
            prix=-a_rembourser, # en négatif car ce sont des remboursement en espèce
            qty=1,
            pos=self.point_de_vente,
            carte=self.carte_db,
            membre=self.carte_db.membre,
            responsable=self.responsable,
            moyen_paiement=self.configuration.moyen_paiement_espece,
            commande=self.uuid_commande,
            uuid_paiement=self.uuid_paiement,
            table=self.table,
            ip_user=self.ip_user,
        )

        self.total_vente_article = a_rembourser
        # Asset principal :
        asset_principal.qty = 0

        for asset in self.payments_assets:
            # Si l'asset gift existe, on le vide
            if asset.monnaie.categorie == MoyenPaiement.LOCAL_GIFT:
                asset.qty = 0
            # Si l'asset fed stripe existe, on le vide
            if asset.monnaie.categorie == MoyenPaiement.STRIPE_FED:
                asset.qty = 0


        self.reponse['route'] = "transaction_vider_carte"


@login_required
@api_view(['GET'])
def table_solo_et_commande(request, *args, **kwargs):
    start = timezone.now()
    if request.method == 'GET':
        pk_table = kwargs.get('table')
        if pk_table:
            table = get_object_or_404(Table, pk=kwargs.get('table'))
            serializer = TableSerializerWithCommand(table)

            data = {
                'table': serializer.data,
            }

            logger.info(f"{timezone.now()} {timezone.now() - start} /wv/table_solo_et_commande/{table}")
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response("Mauvais numéro de table", status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(['POST', 'GET'])
def tables_et_commandes(request):
    start = timezone.now()

    serializer = TableSerializerWithCommand(Table.objects.filter(archive=False), many=True)

    data = {
        'tables': serializer.data,
    }
    logger.info(f"{timezone.now()} - durée d'execution : {timezone.now() - start} /wv/tables_et_commandes")
    # import ipdb; ipdb.set_trace()
    return Response(data, status=status.HTTP_200_OK)


@login_required
@api_view(['POST', 'GET'])
def tables(request):
    serializer = TableSerializer(Table.objects.filter(archive=False), many=True)
    data = {
        'tables': serializer.data,
    }
    # logger.info(f"{timezone.now()} - durée d'execution : {timezone.now() - start} /wv/tables_et_commandes")
    return Response(data, status=status.HTTP_200_OK)


@login_required
@api_view(['POST'])
def paiement(request):
    """
    Première action.
    A la validation d'une commande par le front client, on reçoit le json avec tout les éléments.
    Si le json est valide, on crée un objet Commande

    :param request: json :
    :return: Commande
    """
    if request.method == 'POST':
        validator = DataAchatDepuisClientValidator(data=request.data)
        if validator.is_valid():
            # logger.info(f"/wv/paiement - validator.is_valid()")
            data = validator.validated_data
            logger.debug(f"\n\n/wv/paiement : initial data : {data}\n\n")
            ip_user = get_ip_user(request)
            if ip_user:
                data['ip_user'] = ip_user

            commande = Commande(data)
            reponse = commande.validation()

            return Response(reponse, status=status.HTTP_200_OK)

        logger.error(
            f"/wv/paiement validator.errors : {validator.errors}")
        # errors = [validator.errors[error][0] for error in validator.errors]
        # import ipdb; ipdb.set_trace()
        return Response(validator.errors, status=status.HTTP_406_NOT_ACCEPTABLE)

    return HttpResponseNotFound()
