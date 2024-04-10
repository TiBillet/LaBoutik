from django.core.management.base import BaseCommand

from APIcashless.models import ArticleVendu, Categorie


class Command(BaseCommand):
    def handle(self, *args, **options):
        for categorie in Categorie.objects.filter(tva__isnull=False):
            art_cat = ArticleVendu.objects.filter(article__categorie=categorie)
            art_cat.update(tva=categorie.tva.taux)
            print(f"{categorie} : {art_cat.count()}")


