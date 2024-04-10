import json
from APIcashless.models import *
from datetime import datetime, timedelta

from APIcashless.models import *
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import dateutil.parser



class Command(BaseCommand):
    def handle(self, *args, **options):
        self.migrationBisik()

    def migrationBisik(self):
        with open('SaveDb/migrationV2/dataBisik') as datafile:
            jsonData = datafile.readlines()[0]

        true = True
        false = False
        null = False

        data = json.loads(jsonData)

        membre_pk = {}
        pdv_pk = {}
        pdv_page = {}
        article_pk = {}
        carte_pk = {}
        mpaiement = {}
        article_name = {}
        configuration = Configuration.objects.get()

        for entry in data:
            if entry['model'] == "APIcashless.membres":
                membre = entry['fields']
                try:
                    m = Membre.objects.get_or_create(
                        name=membre.get('name'),
                        pseudo=membre.get('pseudo'),
                        email=membre.get('email'),
                        code_postal=membre.get('codePostal'),
                        date_naissance=datetime.fromisoformat(membre.get('dateNaissance')).date() if membre.get(
                            'dateNaissance') else None,
                        tel=membre.get('tel'),
                        date_inscription=datetime.fromisoformat(membre.get('dateInscription')).date() if membre.get(
                            'dateInscription') else None,
                        date_derniere_cotisation=datetime.fromisoformat(
                            membre.get('dateDerniereCotisation')).date() if membre.get(
                            'dateDerniereCotisation') else None,
                        date_ajout=datetime.fromisoformat(membre.get('dateAjout')).date() if membre.get(
                            'dateAjout') else None,
                        cotisation=membre.get('cotisation'),
                        demarchage=membre.get('demarchage', False),
                        commentaire=membre.get('commentaire'),
                        ajout_cadeau_auto=False,
                    )[0]

                except Exception as e:
                    print(f"erreur {e} {membre.get('name')}")
                    m = Membre.objects.get(name=membre.get('name'))

                membre_pk[entry['pk']] = m.pk
                print(membre['name'])

            if entry['model'] == "APIcashless.pointofsale":
                page = entry['fields']
                if "Bisik" not in page['name']:
                    p = PointDeVente.objects.get_or_create(
                        name=page['name'].capitalize())[0]
                    pdv_page[entry['pk']] = p.pk

            # if entry['model'] == "APIcashless.pointofsale":
            #     pdv = entry['fields']
            #     p = PointDeVente.objects.get_or_create(
            #         name=pdv['name']
            #     )[0]
            #     pdv_pk[entry['pk']] = p.pk

            if entry['model'] == "APIcashless.articles":
                article = entry['fields']
                print(article)
                if article['page'] not in [3, 5]:
                    if article['name'] == "Retour Consigne":
                        a = Articles.objects.get(name="Retour Consigne")
                    else:
                        a = Articles.objects.get_or_create(
                            name=article['name'],
                            prix=article['prix'],
                            prix_achat=article['prixAchat'],
                            poid_liste=article['poidListe'],

                        )[0]
                    article_pk[entry['pk']] = a.pk
                else:
                    article_name[entry['pk']] = article['name']

            if entry['model'] == "APIcashless.cartecashless":
                carte = entry['fields']
                print(carte)
                c = CarteCashless.objects.get_or_create(
                    tag_id=carte['tagId'],
                    number=carte['number'],
                    membre_id=membre_pk.get(carte['membre']),
                )[0]
                if carte.get('peaksu') >= 0:
                    a = Assets.objects.get_or_create(
                        carte=c,
                        qty=carte.get('peaksu'),
                        monnaie=configuration.monnaie_principale,
                        last_date_used=timezone.now()
                    )

                elif carte.get('peaksu') < 0:
                    a = Assets.objects.get_or_create(
                        carte=c,
                        qty=carte.get('peaksu'),
                        monnaie=configuration.monnaie_principale_ardoise,
                        last_date_used=timezone.now()

                    )

                if carte.get('peaksuCadeau') > 0:
                    a = Assets.objects.get_or_create(
                        carte=c,
                        qty=carte.get('peaksuCadeau'),
                        monnaie=configuration.monnaie_principale_cadeau,
                        last_date_used=timezone.now()
                    )
                carte_pk[entry['pk']] = c.pk

            if entry['model'] == 'APIcashless.moyenpaiement':
                if entry['model'] not in mpaiement:
                    mp = entry['fields']['name']
                    if mp == "PeakSu":
                        mpaiement[entry['pk']] = configuration.monnaie_principale
                    elif mp == "Ardoise":
                        mpaiement[entry['pk']] = configuration.monnaie_principale_ardoise
                    elif mp == "Cash/CB":
                        mpaiement[entry['pk']] = configuration.moyen_paiement_espece
                    elif mp == "Cadeau":
                        mpaiement[entry['pk']] = configuration.monnaie_principale_cadeau
                    elif mp == "PeakSu Cadeau":
                        mpaiement[entry['pk']] = configuration.monnaie_principale_cadeau

        for key, value in article_name.items():
            print(key, value)
            if value == "PeakSu +0.5":
                article_pk[key] = Articles.objects.get(name="+0.5").pk
            elif value == "PeakSu +1":
                article_pk[key] = Articles.objects.get(name="+1").pk
            elif value == "PeakSu +5":
                article_pk[key] = Articles.objects.get(name="+5").pk
            elif value == "PeakSu +10":
                article_pk[key] = Articles.objects.get(name="+10").pk
            elif value == "PeakSu +20":
                article_pk[key] = Articles.objects.get(name="+20").pk
            elif value == "PeakSu +x":
                article_pk[key] = Articles.objects.get(name="+x").pk
            elif value == "PSu Cadeau +1":
                article_pk[key] = Articles.objects.get(name="Cadeau +1").pk
            elif value == "PSu Cadeau +5":
                article_pk[key] = Articles.objects.get(name="Cadeau +5").pk
            elif value == "Rtr Cons Cash":
                article_pk[key] = Articles.objects.get(name="Retour Consigne").pk
            elif value == "Rtr Cons Carte":
                article_pk[key] = Articles.objects.get(name="Retour Consigne").pk
            elif value == "Retour Consigne Carte":
                article_pk[key] = Articles.objects.get(name="Retour Consigne").pk
            elif value == "Retour Consigne":
                article_pk[key] = Articles.objects.get(name="Retour Consigne").pk
            elif value == "VIDER CARTE":
                article_pk[key] = Articles.objects.get(name="VIDER CARTE").pk
            elif value == "Adhésion":
                article_pk[key] = Articles.objects.get(name="Adhésion").pk
            elif value == "Erreur":
                article_pk[key] = Articles.objects.get(name="+x").pk
            elif value == "GRATUIT":
                article_pk[key] = Articles.objects.get_or_create(name="GRATUIT")[0].pk

        bar = PointDeVente.objects.get(name="Bar")
        cashless = PointDeVente.objects.get(name="Cashless")
        change_moyenpaiement_cadeau = False

        for entry in data:
            if entry['model'] == 'APIcashless.articlesvendus':
                vente = entry['fields']
                print(vente)
                date = dateutil.parser.parse(vente.get('dateTps'))
                article = Articles.objects.get(id=article_pk[vente.get('article')])

                if change_moyenpaiement_cadeau:
                    moyen_paiement_vente = configuration.monnaie_principale_cadeau
                    change_moyenpaiement_cadeau = False
                else:
                    moyen_paiement_vente = mpaiement.get(vente.get('moyenPaiement'))

                if article.name == "GRATUIT":
                    change_moyenpaiement_cadeau = True
                    continue

                if article.methode == configuration.methode_vente_article:
                    pos = bar
                else:
                    pos = cashless

                v = ArticleVendu.objects.get_or_create(
                    article=article,
                    prix=vente.get('prix'),
                    qty=vente.get('qty'),
                    pos=pos,
                    date_time=date,
                    membre_id=membre_pk.get(vente.get('membre')),
                    carte_id=carte_pk.get(vente.get('carte')),
                    responsable_id=membre_pk.get(vente.get('responsable')),
                    moyen_paiement=moyen_paiement_vente,
                    commande=(uuid.uuid4())
                )[0]

                if carte_pk.get(vente.get('carte')):
                    asset = Assets.objects.filter(carte_id=carte_pk.get(vente.get('carte')),
                                                  monnaie=mpaiement.get(vente.get('moyenPaiement')))

                    if len(asset) > 0:
                        if asset[0].last_date_used > timezone.now() - timedelta(days=1):
                            asset.update(last_date_used=date)
                        elif asset[0].last_date_used < date:
                            asset.update(last_date_used=date)
