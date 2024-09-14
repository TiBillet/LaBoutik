# #! /usr/bin/env python

import decimal
import json
import logging
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4, UUID

import requests
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import HasAPIKey

from APIcashless.custom_utils import dict_to_b64
from APIcashless.models import Configuration, CarteCashless, Assets, Membre, PointDeVente, Articles, Table, \
    ArticleVendu, MoyenPaiement, CarteMaitresse
from APIcashless.serializers import MembreSerializer, CarteCashlessSerializerForQrCode
from APIcashless.validator import DataOcecoValidator, BilletterieValidator, AdhesionValidator, \
    EmailMembreValidator, RechargeCardValidator, MembreshipValidator, SaleFromLespassValidator
from Cashless import settings
from fedow_connect.fedow_api import FedowAPI
from fedow_connect.utils import sign_message, verify_signature
from webview.serializers import TableSerializerWithCommand
from webview.validators import DataAchatDepuisClientValidator
from webview.views import Commande

logger = logging.getLogger(__name__)

"""
Modèle pour fabriquer des clés :
https://florimondmanca.github.io/djangorestframework-api-key/guide/

from rest_framework_api_key.models import APIKey
APIKey.objects.count()
api_key, key = APIKey.objects.create_key(name="my-remote-service")
"""


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def get_client_ip(request):
    # logger.info(request.META)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    x_real_ip = request.META.get('HTTP_X_REAL_IP')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    elif x_real_ip:
        ip = x_real_ip
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip


# def same_domaine_origin(request, config: Configuration):
#     try:
#         origin = request.build_absolute_uri()
#         parse_origin = urlparse(origin)
#         hostname_origin: str = f"{parse_origin.hostname}"
#         domain_origin = '.'.join(hostname_origin.split('.')[-2:])
#
#         url_bill_config = config.billetterie_url
#         parse_url_bill_config = urlparse(url_bill_config)
#         hostname_url_bill_config: str = f"{parse_url_bill_config.hostname}"
#         domain_url_bill_config = '.'.join(hostname_url_bill_config.split('.')[-2:])
#
#         if domain_origin == domain_url_bill_config:
#             return True
#
#     except Exception as e:
#         logger.error(e)
#         raise e
#
#     logger.error(f"check api key : same_domaine_origin : {domain_origin} != {domain_url_bill_config}")
#     return False


def billetterie_white_list(request):
    start = timezone.now()
    key = request.META["HTTP_AUTHORIZATION"].split()[1]
    origin = request.META.get('HTTP_ORIGIN')
    api_key = APIKey.objects.get_from_key(key)
    configuration = Configuration.get_solo()
    ip = get_client_ip(request)

    logger.info(f"{timezone.now()} {timezone.now() - start} - {request.get_full_path()} - {ip} DATA : {request.data}")

    if api_key == configuration.key_billetterie :
        return True
    return False


class check_apikey(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        config = Configuration.get_solo()
        start = timezone.now()
        key = request.META["HTTP_AUTHORIZATION"].split()[1]
        api_key = APIKey.objects.get_from_key(key)
        ip = get_client_ip(request)

        if api_key == config.key_billetterie :
            logger.info(f"{timezone.now()} {timezone.now() - start} /api/check_apikey GET depuis {ip}")
            data = {
                "ip": ip,
                "api_key": api_key.name,
                "bill": bool(api_key == config.key_billetterie),
                "co": bool(api_key == config.key)
            }

            return Response(data, status=status.HTTP_200_OK)

        logger.error(f"{timezone.now()} {timezone.now() - start} ERROR /api/check_apikey GET depuis {ip}")
        return Response("Nop", status=status.HTTP_400_BAD_REQUEST)


class oceco_endpoint(APIView):
    '''
    exemple :
    curl -H "Authorization: Api-Key WDW7GZ4L.fJq05uXsi3taK1WrGtLWDis761YPSMrp" -X POST --data "number_printed=01E31CBB&qty_oceco=10" https://tibillet.demo.nasjo.fr/api/oceco_endpoint
    '''

    permission_classes = [HasAPIKey]

    # throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def post(self, request):
        start = timezone.now()
        key = request.META["HTTP_AUTHORIZATION"].split()[1]
        api_key = APIKey.objects.get_from_key(key)

        ip = get_client_ip(request)
        logger.info(f"{timezone.now()} {timezone.now() - start} /api/oceco_endpoint POST depuis {ip}")

        configuration = Configuration.get_solo()

        if api_key.name == "oceco_key" and ip == configuration.oceco_ip_white_list:
            # On vérifie avec le validator que la qty soit bien un chiffre, et que le numéro existe bien en carte
            # Le validator renvoie l'asset cadeau correspondant a la carte directement.
            validator_data_oceco = DataOcecoValidator(data=request.data)
            if validator_data_oceco.is_valid():
                asset_cadeau: Assets = validator_data_oceco.validated_data.get('number_printed')

                article_cadeau = Articles.objects.get(
                    methode_choices=Articles.RECHARGE_CADEAU,
                    prix=1
                )

                qty_cadeau = Decimal(configuration.valeur_oceco) * Decimal(
                    validator_data_oceco.validated_data.get('qty_oceco'))

                data_ext = {
                    "pk_responsable": Membre.objects.get_or_create(name="WEB OCECO")[0].pk,
                    "pk_pdv": PointDeVente.objects.filter(name="Cashless")[0].pk,
                    "tag_id": asset_cadeau.carte.tag_id,
                    # "moyen_paiement": configuration.moyen_paiement_oceco,
                    "moyen_paiement": 'Oceco',
                    "total": qty_cadeau,
                    "articles": [{
                        'pk': article_cadeau.pk,
                        'qty': qty_cadeau,
                    }, ],
                }

                validator_transaction = DataAchatDepuisClientValidator(data=data_ext)

                if validator_transaction.is_valid():
                    data = validator_transaction.validated_data
                    commande = Commande(data)

                    commande_valide = commande.validation()

                    logger.info(
                        f"{timezone.now()} {timezone.now() - start} /APIcashless/oceco_endpoint POST {validator_transaction.validated_data}")
                    return Response(f"Monnaie Cadeau ok ({commande_valide['carte']['total_monnaie']})",
                                    status=status.HTTP_200_OK)
                else:
                    logger.error(
                        f"{timezone.now()} {timezone.now() - start} /APIcashless/oceco_endpoint validator_transaction.errors : {validator_transaction.errors}")
                    return Response(validator_transaction.errors, status=status.HTTP_400_BAD_REQUEST)

            else:
                logger.error(
                    f"{timezone.now()} {timezone.now() - start} /APIcashless/oceco_endpoint validator.errors : {validator_data_oceco.errors}")
                return Response(validator_data_oceco.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.error(
                f"{timezone.now()} {timezone.now() - start} /APIcashless/oceco_endpoint Not valid : {ip} not {configuration.oceco_ip_white_list} or {api_key.name} not 'oceco_key' ")
            return Response(f"Not valid", status=status.HTTP_401_UNAUTHORIZED)


# ex api pre fedow
"""
class membre_check(APIView):
    permission_classes = [HasAPIKey]
    # permission_classes = [AllowAny]
    def post(self, request):
        if not billetterie_white_list(request):
            return Response('no no no', status=status.HTTP_401_UNAUTHORIZED)

        validator = EmailMembreValidator(data=request.data)

        if validator.is_valid():
            serializer = MembreSerializer(validator.data.get('membre'))
            return Response(serializer.data, status=status.HTTP_200_OK)

        logger.error(
            f"{timezone.now()} /api/membre_check POST validator.errors : {validator.errors}")
        return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)
"""


# ex api pre fedow
"""
class ChargeCard(APIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        if not billetterie_white_list(request):
            return Response('no no no', status=status.HTTP_401_UNAUTHORIZED)

        validator = RechargeCardValidator(data=request.data)
        if validator.is_valid():
            card: CarteCashless = validator.data.get('card')
            qty: int = validator.validated_data.get('qty')
            uuid_commande: int = validator.validated_data.get('uuid_commande')

            if not card.membre:
                email = validator.validated_data.get('email')
                if email:
                    membre, created = Membre.objects.get_or_create(email=email.lower())
                    if created:
                        membre.date_inscription = timezone.now().date()
                        membre.adhesion_origine = Membre.QRCODE
                        membre.save()

                    config = Configuration.get_solo()
                    if config.can_fedow():
                        fedowAPI = FedowAPI(config=config)
                        fedowAPI.NFCcard.link_user(email=email, card=card)

                    card.membre = membre
                    card.save()

            else:
                # Il existe un membre, on vérifie qu'il a un email
                if not card.membre.email:
                    email = validator.validated_data.get('email')
                    if email:
                        card.membre.email = email.lower()
                        card.membre.save()

            pos_cashless = PointDeVente.objects.filter(comportement=PointDeVente.CASHLESS)[0]

            # Bien mettre en majuscule, sinon get_or_create va créer un nouveau responsable avec le nom en Capitalisé
            responsable_web = Membre.objects.get_or_create(name="WEB STRIPE")[0]

            logger.info(
                f"{timezone.now()} ChargeCard {card.number} x {qty} - paiement stripe {uuid_commande}")

            data_ext = {
                "pk_responsable": responsable_web.pk,
                "pk_pdv": pos_cashless.pk,
                "tag_id": card.tag_id,
                "moyen_paiement": 'Web (Stripe)',
                "total": qty,
                "uuid_commande": uuid_commande,
                "articles": [{
                    'pk': Articles.objects.get(name="+1", methode_choices=Articles.RECHARGE_EUROS).pk,
                    'qty': qty,
                }],
            }
            validator = DataAchatDepuisClientValidator(data=data_ext)

            if validator.is_valid():
                data = validator.validated_data
                commande = Commande(data)
                commande_valide = commande.validation()
                return Response(f'{commande.reponse}', status=status.HTTP_202_ACCEPTED)

        logger.error(
            f"{timezone.now()} ChargeCard POST validator.errors : {validator.errors}")
        return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)
"""

class OnboardStripeReturn(APIView):
    permission_classes = [AllowAny]

    # AllowAny paske ça vient de Stripe
    def get(self, request, id_acc_connect):
        # Retour de stripe, une fois les informations de compte renseigné.
        # Une requete est envoyé au Fedow pour vérification des données valide.

        config = Configuration.get_solo()
        # config_node = FedowNodeConfig.get_solo()

        data = {
            "fedow_place_uuid": f"{config.fedow_place_uuid}",
            "id_acc_connect": f"{id_acc_connect}"
        }

        data_encoded = dict_to_b64(data)
        signature = sign_message(
            data_encoded,
            config.get_private_key()).decode('utf-8')

        # Ici, on s'auto vérifie :
        if not verify_signature(config.get_public_key(),
                                data_encoded,
                                signature):
            raise Exception("Erreur de signature")

        # Envoie de la requete à FEDOW : Dictionnaire + signature
        session = requests.Session()
        request_fedow = session.post(
            f"https://{config.fedow_domain}/onboard_stripe_return/",
            headers={
                "Authorization": f"Api-Key {config.fedow_place_admin_apikey}",
                "Signature": f"{signature}"
            },
            data=data,
            verify=bool(not settings.DEBUG),
        )
        session.close()

        if request_fedow.status_code == 200:
            config.stripe_connect_account = id_acc_connect
            config.stripe_connect_valid = True
            config.save()

            data = request_fedow.json()
            primary_stripe_asset_uuid = UUID(data.get('primary_stripe_asset_uuid'))
            primary_stripe_asset_name = data.get('primary_stripe_asset_name')

            # on test avec une carte primaire
            # Le serializer va créer les monnaies fédérées
            fedowApi = FedowAPI(config=config)
            serialized_card = fedowApi.NFCcard.retrieve(CarteMaitresse.objects.first()[0].carte.tag_id)

            mp_fedow, created = MoyenPaiement.objects.get_or_create(
                id=primary_stripe_asset_uuid,
                name=primary_stripe_asset_name,
                is_federated=True,
                blockchain=True,
                categorie=MoyenPaiement.STRIPE_FED,
            )

            config.monnaies_acceptes.add(mp_fedow)
            config.save()

            messages.add_message(request, messages.SUCCESS, f"Votre instance est maintenant fédérée !")
        else:
            messages.add_message(request, messages.ERROR, f"{request_fedow.status_code}")

        return HttpResponseRedirect('/adminstaff/APIcashless/configuration/#/tab/module_8/')


class Membership(APIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        if not billetterie_white_list(request):
            return Response('ip not in white list', status=status.HTTP_401_UNAUTHORIZED)

        validator = MembreshipValidator(data=request.data)
        if validator.is_valid():
            configuration = Configuration.get_solo()

            tarif_adhesion: int = validator.validated_data.get('adhesion')
            uuid_commande: uuid4 = validator.validated_data.get('uuid_commande')
            pos_cashless = PointDeVente.objects.filter(comportement=PointDeVente.CASHLESS)[0]
            responsable_web = Membre.objects.get_or_create(name="WEB STRIPE")[0]
            membre: Membre = validator.data.get('membre')

            carte = None
            if membre.CarteCashless_Membre.count() > 0:
                carte = membre.CarteCashless_Membre.all()[0]

            logger.info(f"{timezone.now()} paiement d'adhésion API pour {membre}")

            membre.date_derniere_cotisation = timezone.now().date()
            membre.save()

            ArticleVendu.objects.create(
                article=Articles.objects.get(name='Adhésion'),
                prix=tarif_adhesion,
                qty=1,
                pos=pos_cashless,
                membre=membre,
                responsable=responsable_web,
                carte=carte,
                moyen_paiement=configuration.moyen_paiement_mollie,
                commande=uuid_commande,
            )

            return Response(validator.validated_data, status=status.HTTP_200_OK)
        return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckCarteQrUuid(viewsets.ViewSet):
    permission_classes = [HasAPIKey]

    def retrieve(self, request, pk=None):
        if not billetterie_white_list(request):
            return Response('no no no', status=status.HTTP_401_UNAUTHORIZED)

        carte = get_object_or_404(CarteCashless, uuid_qrcode=pk)
        serializer = CarteCashlessSerializerForQrCode(carte)

        serializer_copy = serializer.data

        history = [{
            'date': f"{article_vendu.date_time}",
            'qty': f"{article_vendu.qty}",
            'article': f"{article_vendu.article}",
            'total': f"{article_vendu.total()}",
        } for article_vendu in
            ArticleVendu.objects.filter(carte=carte, date_time__gte=(timezone.now() - timedelta(days=1)))]
        serializer_copy['history'] = history

        return Response(serializer_copy)


class SaleFromLespass(APIView):
    permission_classes = [HasAPIKey]
    def post(self, request):
        logger.info(request.data)
        validator = SaleFromLespassValidator(data=request.data)
        if not validator.is_valid():
            logger.error(f"Sale from lespass not valid : {validator.errors}")
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        # Un seul article par requete
        try :
            price_lespass_uuid =  validator.validated_data['pricesold']['price']['uuid']
            wallet = validator.validated_data['user_uuid_wallet']
            moyen_paiement_stripe = MoyenPaiement.objects.get(categorie=MoyenPaiement.STRIPE_NOFED)

            try :
                article = Articles.objects.get(pk=price_lespass_uuid)
            except Articles.DoesNotExist:
                # Si l'article n'existe pas ? On va refresh les assets qui vont probablement le créer
                logger.warning(f"Article existe pas, on va le chercher dans Fedow")
                fedowAPI = FedowAPI()
                fedowAPI.place.get_accepted_assets()
                article = Articles.objects.get(pk=price_lespass_uuid)

            pos, created = PointDeVente.objects.get_or_create(name=_('Billetterie'))

            art = ArticleVendu.objects.create(
                article=article,
                prix=validator.validated_data['pricesold']['prix'],
                date_time=validator.validated_data['datetime'],
                qty=validator.validated_data['qty'],
                pos=pos,
                tva=validator.validated_data['vat'],
                membre=getattr(wallet,'membre', None),
                responsable=None,
                carte=wallet.cards.first(),
                moyen_paiement=moyen_paiement_stripe,
                uuid=validator.validated_data['uuid'],
                commande=validator.validated_data['uuid'],
                # ip_user=get_client_ip(request),
            )
            return Response("", status=status.HTTP_200_OK)

        except Articles.DoesNotExist:
            raise Exception('Pas de correspondance article - price')

# ex api pre fedow
"""
class billetterie_endpoint(APIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        if not billetterie_white_list(request):
            logger.warning('not billetterie white list')
            return Response('no no no', status=status.HTTP_401_UNAUTHORIZED)

        start = timezone.now()
        validator_data_billetterie = BilletterieValidator(data=request.data)

        if not validator_data_billetterie.is_valid():
            logger.error(
                f"{timezone.now()} {timezone.now() - start} /APIcashless/billetterie_endpoint validator_data_billetterie.errors : {validator_data_billetterie.errors}")
            return Response(validator_data_billetterie.errors, status=status.HTTP_400_BAD_REQUEST)

        configuration = Configuration.get_solo()
        carte = validator_data_billetterie.carte
        data = validator_data_billetterie.validated_data

        recharge_qty = data.get('recharge_qty')
        uuid_commande = data.get('uuid_commande')
        tarif_adhesion = data.get('tarif_adhesion')
        days_historique = int(data.get('days_historique', 1))

        pos_cashless = PointDeVente.objects.filter(comportement=PointDeVente.CASHLESS)[0]
        responsable_web = Membre.objects.get_or_create(name="WEB STRIPE")[0]

        json_reponse = {}

        if carte.membre:
            if carte.membre.email:
                json_reponse['email'] = carte.membre.email
                json_reponse['a_jour_cotisation'] = carte.membre.a_jour_cotisation()

        assets = [{
            "nom": f"{asset.monnaie.name}",
            "qty": f"{asset.qty}",
            "categorie_mp": f"{asset.monnaie.categorie}"
        } for asset in carte.assets.all()]

        json_reponse['assets'] = assets
        json_reponse['total_monnaie'] = carte.total_monnaie()

        # Historique des achats
        history = [{
            'date': f"{article_vendu.date_time}",
            'qty': f"{article_vendu.qty}",
            'article': f"{article_vendu.article}",
            'total': f"{article_vendu.total()}",
        } for article_vendu in
            ArticleVendu.objects.filter(
                carte=carte,
                date_time__gte=(timezone.now() - timedelta(days=days_historique))
            ).exclude(article__methode_choices__in=[Articles.FRACTIONNE, ])]

        json_reponse['history'] = history

        # c'est juste un check carte
        if not recharge_qty and not uuid_commande:
            logger.info(
                f"{timezone.now()} {timezone.now() - start} /APIcashless/billetterie_endpoint POST checkcarte: {carte}")
            return Response(json.dumps(json_reponse, cls=DecimalEncoder), status=status.HTTP_200_OK)

        # Adhésion par le web
        if tarif_adhesion and uuid_commande and carte.membre:
            logger.info(f"{timezone.now()} paiement d'adhésion billetterie_endpoint pour {carte.membre}")

            carte.membre.date_derniere_cotisation = timezone.now().date()
            carte.membre.save()

            ArticleVendu.objects.create(
                article=Articles.objects.get(name='Adhésion'),
                prix=float(tarif_adhesion),
                qty=1,
                pos=pos_cashless,
                membre=carte.membre,
                responsable=responsable_web,
                carte=carte,
                moyen_paiement=configuration.moyen_paiement_mollie,
                commande=uuid_commande,
            )

        # c'est une recharge de monnaie :
        # TODO: Sela ne semble plus utilisé ? La billetterie passe par chargecard lors d'une recharge ?
        if recharge_qty and uuid_commande:
            data_ext = {
                "pk_responsable": responsable_web.pk,
                "pk_pdv": pos_cashless.pk,
                "tag_id": carte.tag_id,
                "moyen_paiement": 'Web (Stripe)',
                "total": recharge_qty,
                "uuid_commande": uuid_commande,
                "articles": [{
                    'pk': Articles.objects.get(name="+1", methode_choices=Articles.RECHARGE_EUROS).pk,
                    'qty': recharge_qty,
                }],
            }

            logger.info(
                f"{timezone.now()} paiement de recharge monnaie billetterie_endpoint pour {carte.number}")

            validator = DataAchatDepuisClientValidator(data=data_ext)

            if validator.is_valid():
                data = validator.validated_data
                commande = Commande(data)
                commande_valide = commande.validation()

            else:
                logger.error(
                    f"{timezone.now()} {timezone.now() - start} /wv/billetterie_endpoint POST validator.errors : {validator.errors}")
                return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"{timezone.now()} {timezone.now() - start} /APIcashless/billetterie_endpoint POST paiement: {data}")
        return Response(json.dumps(json_reponse, cls=DecimalEncoder), status=status.HTTP_200_OK)
"""


# ex api pre fedow
"""

class billetterie_qrcode_adhesion(APIView):
    '''
    curl -H "Authorization: Api-Key gDXvlupm.laoE5Oy1YQdhAWYznXReMB2id8zjZ1iD" -X POST --data "card=01E31CBB&amount=10" http://localhost:8001/api/billetterie_endpoint
    '''
    permission_classes = [HasAPIKey]

    def post(self, request):
        start = timezone.now()
        key = request.META["HTTP_AUTHORIZATION"].split()[1]
        api_key = APIKey.objects.get_from_key(key)
        configuration = Configuration.get_solo()

        ip = get_client_ip(request)
        logger.info(
            f"{timezone.now()} {timezone.now() - start} /api/billetterie_qrcode_adhesion POST depuis {ip} data : {request.data}")

        if not billetterie_white_list(request):
            return Response('no no no', status=status.HTTP_401_UNAUTHORIZED)

        # on check si on a toute les infos
        validator_adhesionValidator = AdhesionValidator(data=request.data)
        if validator_adhesionValidator.is_valid():
            carte_cashless: CarteCashless = validator_adhesionValidator.carte
            data = validator_adhesionValidator.validated_data
            if carte_cashless.membre:
                if not carte_cashless.membre.email and data.get('email'):
                    # Le membre n'a pas son email de renseigné, on le met à jour
                    carte_cashless.membre.email = data.get('email').lower()
                    carte_cashless.membre.save()
                elif carte_cashless.membre.email != data.get('email'):
                    return Response(_('La carte est déja liée a une autre adresse email.'),
                                    status=status.HTTP_409_CONFLICT)

            membre, created = Membre.objects.get_or_create(email=data.get('email').lower())

            if created:
                membre.date_inscription = timezone.now().date()
                membre.adhesion_origine = Membre.QRCODE
                membre.save()
                return Response('nouveau membre créé, envoyez la suite', status=status.HTTP_201_CREATED)

            if not membre.name and data.get('name'):
                membre.name = data.get('name').upper()
            if not membre.prenom and data.get('prenom'):
                membre.prenom = data.get('prenom').capitalize()
            if not membre.tel and data.get('tel'):
                membre.tel = data.get('tel')

            # import ipdb; ipdb.set_trace()
            if not carte_cashless.membre:
                carte_cashless.membre = membre
                carte_cashless.save()

                if configuration.can_fedow():
                    fedowAPI = FedowAPI(config=configuration)
                    fedowAPI.NFCcard.link_user(email=membre.email, card=carte_cashless)

            membre.save()


            if not membre.name and not membre.prenom and not membre.tel:
                return Response('Membre existant mais zero informations', status=status.HTTP_204_NO_CONTENT)

            # Membre existant, mais information manquante
            if not membre.name or not membre.prenom or not membre.tel:
                info_membre = {
                    'name': membre.name,
                    'prenom': membre.prenom,
                    'tel': membre.tel
                }

                return Response(info_membre, status=status.HTTP_206_PARTIAL_CONTENT)

            if membre.name and membre.prenom and membre.tel:
                return Response('Membre existant, carte liée', status=status.HTTP_202_ACCEPTED)


        else:
            logger.error(f'{validator_adhesionValidator.errors}')
            return Response(validator_adhesionValidator.errors, status=status.HTTP_400_BAD_REQUEST)
"""


class preparations(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        start = timezone.now()
        serializer = TableSerializerWithCommand(Table.objects.all(), many=True)

        data = {
            'tables': serializer.data,
        }

        logger.info(f"{timezone.now()} {timezone.now() - start} /APIcashless/preparations POST")
        return Response(data, status=status.HTTP_200_OK)


class signed_key(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        config = Configuration.get_solo()
        public_pem = config.get_public_pem()
        signature = sign_message(
            public_pem.encode('utf-8'),
            config.get_private_key()).decode('utf-8')

        signed_key_response = {
            "public_pem": public_pem,
            "signature": signature,
        }
        return Response(signed_key_response, status=status.HTTP_200_OK)

