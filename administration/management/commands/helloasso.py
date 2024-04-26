# #! /usr/bin/env python
from django.core.management.base import BaseCommand
import json, os
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter

requests.adapters.DEFAULT_RETRIES = 5

from APIcashless.models import Membre


def get_token():
    session = requests.session()
    url = "https://api.helloasso.com/oauth2/token"
    header = {
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'client_id': os.environ.get('HELLOASSO_CLIENT_ID'),
        'client_secret': os.environ.get('HELLOASSO_SECRET'),
    }

    r = session.post(url, data=data, headers=header)

    if r.status_code == 200:
        token = json.loads(r.text).get('access_token')

        session.close()
        print(f"Token ok ")
        return token
    else:
        raise Exception(f'Erreur Token, code non 200 : {r.status_code} ')


def get_items_sold():
    session = requests.session()
    page_index: int = 1
    organisation = os.environ.get('HELLOASSO_SLUG')
    date_depuis = datetime.now().date() - timedelta(days=7)

    def seturl():
        url = f"https://api.helloasso.com/v5/organizations/{organisation}/items" \
              f"?pageIndex={page_index}" \
              f"&pageSize=100" \
              f"&withDetails=false" \
              f"&retrieveAll=false" \
              f"&from={date_depuis}"

        return url

    header = {
        "accept": "application/json",
        'authorization': f'Bearer {get_token()}'
    }

    request = session.get(seturl(), headers=header, timeout=10)

    if request.status_code == 200:

        data = json.loads(request.text)['data']
        all_data = data.copy()

        while len(data) == 100:
            page_index += 1
            request = session.get(seturl(), headers=header, timeout=10)

            if request.status_code == 200:
                data = json.loads(request.text)['data']
                all_data += data
            else:
                raise Exception(f'Erreur items, code non 200 : {request.status_code} ')

        session.close()
        print(f"data item ok. len : {len(all_data)}")
        return all_data
    else:
        raise Exception(f'Erreur items, code non 200 : {request.status_code} ')


def data_serializer():
    events = {}
    # for item in self.orders :
    for item in get_items_sold():

        events[item['order']['formSlug']] = events.get(item['order']['formSlug'], {})
        event = events[item['order']['formSlug']]

        # on va ranger par numero de commande (donc par email )
        event[item['order']['id']] = event.get(item['order']['id'], {})
        order = event[item['order']['id']]

        # on rajoute les noms :
        nom = f"{item['user']['lastName'].upper()} {item['user']['firstName'].capitalize()}"
        order['noms'] = order.get('noms', [])
        if nom not in order['noms']:
            order['noms'].append(nom)

        if item['payer'].get('lastName'):
            order['payer'] = item['payer']

        order['type'] = item['name']
        order['qty'] = len(order['noms'])

    print(f"Serializer ok, envents : { [event for event in events] }" )
    return events


class Command(BaseCommand):

    def handle(self, *args, **options):
        events = data_serializer()
        for event in events:
            for order in events[event]:
                ord = events[event][order]
                payeur = ord['payer']

                nom_event = f"{event}"[:20]

                # pas top, mais pour l'instant... vivement la billeterie !
                commentaire = f"- {nom_event}... \n" \
                              f"    {ord['qty']} Billets  au nom de :\n" \
                              f"    {', '.join([nom for nom in ord['noms']])}\n" \
                              f"    {ord['type']} \n"
                print(f"{payeur} : payeur")
                membre, created = Membre.objects.get_or_create(email=payeur['email'].lower())

                if created:
                    print(payeur['email'])
                    print(f"{payeur['lastName'].upper()} {payeur['firstName'].capitalize()}")

                    membre.name = payeur['lastName'].upper()
                    membre.prenom = payeur['firstName'].capitalize()
                    membre.code_postal = payeur.get('zipCode')
                    membre.adhesion_origine = Membre.HELLOASSO

                if not membre.commentaire or \
                        commentaire not in membre.commentaire:
                    print(commentaire)
                    membre.commentaire = f"{commentaire} \n" \
                                         f"\n" \
                                         f"{membre.commentaire}"

                membre.save()
