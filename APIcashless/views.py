#! /usr/bin/env python

import decimal
import json
import logging
from datetime import timedelta, datetime
from decimal import Decimal
from uuid import UUID

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
from APIcashless.serializers import CarteCashlessSerializerForQrCode
from APIcashless.validator import DataOcecoValidator, SaleFromLespassValidator, \
    ProductFromLespassValidator
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

class trigger_product_update(APIView):
    permission_classes = [HasAPIKey]
    # Lors de la création d'un nouveau produit adhésion sur Lespass, on lance un fedow_update pour récupérer l'objet
    def post(self, request):
        logger.info(f"trigger_product_update : fedowAPI.place.get_accepted_assets()")
        try :
            fedowAPI = FedowAPI()
            fedowAPI.place.get_accepted_assets()

            # Recherche des modif' des produits adhésions associés
            # Mise à jour si besoin
            product_pk = request.data['product_pk']
            if MoyenPaiement.objects.filter(pk=product_pk).exists():
                config = Configuration.get_solo()
                retrieve_product = requests.get(
                    f"{config.billetterie_url}/api/products/{product_pk}/", # Ex : Si une adhésion est créé, le MP.pk est créé avec l'uuid de
                    verify=bool(not settings.DEBUG))

                if retrieve_product.status_code == 200 :
                    # Fabrique et mets à jour les articles adhésions ou badges
                    product = ProductFromLespassValidator(data=retrieve_product.json(),
                                                          context={
                                                              'MoyenPaiement': MoyenPaiement.objects.get(pk=product_pk),
                                                          })
                    if not product.is_valid():
                        for error in product.errors:
                            logger.error(error)
                        raise Exception(
                            f"create_article_membreship_badge : Création d'Asset Adhésion ou Badge {product.errors}")
                else :
                    # Peut arriver si Lespass à envoyé des assets membership sur fedow, qui les as gardé.
                    # Fedow envoie les ref' à Laboutik, qui va vérifier sur Lespass
                    # Ça n'existe plus, donc ça plante.
                    logger.warning("Asset non visible sur Lespass, as t il été créé puis supprimé avant le onboard ?")



            return Response("update ok", status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"trigger_product_update : {str(e)}")
            return Response(
                {"error": f"Failed to trigger_product_update : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StripeBankDepositFromLespass(APIView):
    permission_classes = [HasAPIKey]
    def post(self, request):
        logger.debug(request.data)
        payload = request.data
        transfert, created = Articles.objects.get_or_create(name="Stripe TiBillet transfert",
                                                 prix=1,
                                                 methode_choices=Articles.TRANSFERT)

        # Amount est un entier.
        amount = payload['data']['object']['amount'] / 100
        id = payload['fedow_transaction_uuid']

        if ArticleVendu.objects.filter(uuid=id).exists():
            return Response("Déja enregistré", status=status.HTTP_208_ALREADY_REPORTED)

        # Création si besoin du pos Fedow
        try :
            pos = PointDeVente.objects.get(name=_('Fedow'))
        except PointDeVente.DoesNotExist:
            pos = PointDeVente.objects.create(name=_('Fedow'), hidden=True)

        try:
            mp = MoyenPaiement.objects.get(categorie=MoyenPaiement.STRIPE_NOFED)
        except MoyenPaiement.DoesNotExist:
            mp = MoyenPaiement.objects.create(name="Web (Stripe)", blockchain=False,
                                                     categorie=MoyenPaiement.STRIPE_NOFED)[0]

        try:
            vente_depuis_lespass = ArticleVendu.objects.create(
                uuid=payload['fedow_transaction_uuid'],
                article=transfert,
                prix=amount,
                date_time=datetime.fromtimestamp(payload['data']['object']['created']),
                qty=1,
                pos=pos,
                tva=0,
                membre=None,
                responsable=None,
                carte=None,
                moyen_paiement=mp,
                uuid_paiement=payload['fedow_transaction_uuid'],
                commande=payload['fedow_transaction_uuid'],
                sync_fedow=True,
                hash_fedow=payload['fedow_transaction_hash'],
            )
            return Response("", status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error creating ArticleVendu StripeBankDepositFromLespass :  {str(e)}")
            return Response(
                {"error": f"Failed to create ArticleVendu StripeBankDepositFromLespass : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RefundFromLespass(APIView):
    permission_classes = [HasAPIKey]
    def post(self, request):
        logger.info(f"SaleFromLespass : ")
        logger.info(request.data)

        # Récupération de la vente a rembourser
        refund_sale_uuid = request.data['metadata']['original_lignearticle_uuid']
        vente_depuis_lespass = get_object_or_404(ArticleVendu, uuid=refund_sale_uuid)

        validator = SaleFromLespassValidator(data=request.data)
        if not validator.is_valid():
            logger.error(f"Sale from lespass not valid : {validator.errors}")
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        if Decimal(validator.data.get('qty')) > 0:
            return Response("Refund qty > 0", status=status.HTTP_400_BAD_REQUEST)

        try:
            refund_depuis_lespass = ArticleVendu.objects.create(
                uuid=validator.validated_data['uuid'],
                article=vente_depuis_lespass.article,
                prix=vente_depuis_lespass.prix,
                date_time=validator.validated_data['datetime'],
                qty=Decimal(validator.data.get('qty')),
                pos=vente_depuis_lespass.pos,
                tva=vente_depuis_lespass.tva,
                membre=None,
                responsable=None,
                carte=None,
                moyen_paiement=vente_depuis_lespass.moyen_paiement,
                uuid_paiement=refund_sale_uuid,
                commande=refund_sale_uuid,
                metadata=validator.validated_data['metadata'],
            )
            return Response("", status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error creating ArticleVendu SaleFromLespass: {str(e)}")
            return Response(
                {"error": f"Failed to create ArticleVendu SaleFromLespass: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        import ipdb; ipdb.set_trace()

class SaleFromLespass(APIView):
    permission_classes = [HasAPIKey]
    def post(self, request):
        logger.info(f"SaleFromLespass : ")
        logger.info(request.data)
        validator = SaleFromLespassValidator(data=request.data)

        if not validator.is_valid():
            logger.error(f"Sale from lespass not valid : {validator.errors}")
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        price_uuid =  validator.validated_data['pricesold']['price']['uuid']
        product_uuid =  validator.validated_data['pricesold']['price']['product']
        moyen_paiement = MoyenPaiement.objects.get(categorie=validator.validated_data['payment_method'])
        if validator.validated_data.get('asset'):
            moyen_paiement = MoyenPaiement.objects.get(pk=validator.validated_data['asset'])

        # Amount est un entier.
        amount = validator.validated_data['amount'] / 100

        # On va vérifier les produit sur Lespass et créer les articles manquants
        config = Configuration.get_solo()
        retrieve_product = requests.get(
            f"{config.billetterie_url}/api/products/{product_uuid}/",
            verify=bool(not settings.DEBUG))

        if retrieve_product.status_code == 200:
            # On mets à jour les produits assets Fedow
            fedowAPI = FedowAPI()
            fedowAPI.place.get_accepted_assets()
            # Mets à jour tout les articles adhésions ou badges
            # import ipdb; ipdb.set_trace()
            logger.info(retrieve_product.json())
            product = ProductFromLespassValidator(data=retrieve_product.json())
            if not product.is_valid():
                logger.error(product.errors)
                raise Exception(
                    f"create_article_membreship_badge : Création d'Asset Adhésion ou Badge {product.errors}")

        article = Articles.objects.get(pk=price_uuid)
        pos, created = PointDeVente.objects.get_or_create(name=_('Billetterie'))

        try:
            vente_depuis_lespass = ArticleVendu.objects.create(
                uuid=validator.validated_data['uuid'],
                article=article,
                prix=amount,
                date_time=validator.validated_data['datetime'],
                qty=validator.validated_data['qty'],
                pos=pos,
                tva=validator.validated_data['vat'],
                membre=None,
                responsable=None,
                carte=None,
                moyen_paiement=moyen_paiement,
                uuid_paiement=validator.validated_data['uuid'],
                commande=validator.validated_data['uuid'],
                metadata=validator.validated_data.get('metadata'),
            )
            return Response("", status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error creating ArticleVendu SaleFromLespass: {str(e)}")
            return Response(
                {"error": f"Failed to create ArticleVendu SaleFromLespass: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

