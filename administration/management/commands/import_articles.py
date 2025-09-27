import csv
from decimal import Decimal

from django.core.management.base import BaseCommand

from APIcashless.models import dround, Categorie, ArticleVendu, Articles, PointDeVente, TauxTVA


class Command(BaseCommand):
    def handle(self, *args, **options):
        print(
            "CSV format: titre, categorie, prix, tva")
        # file = open('data/retour_usine_raff_gen_2.csv')
        input_fichier_csv = input('path fichier csv ? \n')
        csv_file = open(input_fichier_csv)
        csv_parser = csv.reader(csv_file)

        # Contruction de la liste des objets
        list_articles = []
        for line in csv_parser:
            print(line)

            titre = line[0].capitalize()[:30]
            if not type(titre) == str or not titre:
                raise Exception('titre')

            categorie = line[1].capitalize()
            if not categorie or not type(categorie) == str :
                raise Exception('categorie')

            tarif = Decimal(line[2].replace(',','.')).quantize(Decimal('1.00'))
            if not type(tarif) == Decimal or not tarif:
                raise Exception('tarif')

            tva = Decimal(Decimal(line[3]) *100).quantize(Decimal('1.00'))
            if not type(tva) == Decimal or not tva:
                raise Exception('Tva')

            print(f"categorie: {categorie}, titre: {titre}, tarif: {tarif}")
            list_articles.append((titre, categorie, tarif, tva))
        csv_file.close()

        pdv = PointDeVente.objects.get(name='RESTO')
        for article in list_articles:
            tva, created = TauxTVA.objects.get_or_create(taux=article[3], name=f"{article[3]}%")
            cat, created = Categorie.objects.get_or_create(name=article[1], tva=tva)
            art, created = Articles.objects.get_or_create(categorie=cat, name=article[1], prix=article[2])
            pdv.articles.add(art)