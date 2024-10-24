import csv
from decimal import Decimal

from django.core.management.base import BaseCommand

from APIcashless.models import dround, Categorie, ArticleVendu, Articles, PointDeVente


class Command(BaseCommand):
    def handle(self, *args, **options):
        print(
            "CSV format: categorie, tva, titre, prix")
        # file = open('data/retour_usine_raff_gen_2.csv')
        input_fichier_csv = input('path fichier csv ? \n')
        csv_file = open(input_fichier_csv)
        csv_parser = csv.reader(csv_file)

        # Contruction de la liste des objets
        list_articles = []
        for line in csv_parser:
            print(line)
            categorie = line[0].capitalize()
            if not categorie or not type(categorie) == str :
                raise Exception('categorie')

            titre = line[1].capitalize()[:30]
            if not type(titre) == str or not titre:
                raise Exception('titre')

            tarif = Decimal(line[2].replace(',','.')).quantize(Decimal('1.00'))
            if not type(tarif) == Decimal or not tarif:
                raise Exception('tarif')

            print(f"categorie: {categorie}, titre: {titre}, tarif: {tarif}")
            list_articles.append((categorie, titre, tarif))
        csv_file.close()

        boutique = PointDeVente.objects.get(name='Boutique')
        for article in list_articles:
            cat, created = Categorie.objects.get_or_create(name=article[0])
            art, created = Articles.objects.get_or_create(categorie=cat, name=article[1], prix=article[2])
            boutique.articles.add(art)