from django.core.management import BaseCommand

from APIcashless.models import Categorie, ArticleVendu, ClotureCaisse, ClotureCaisse
from administration.ticketZ import TicketZ


class Command(BaseCommand):
    def handle(self, *args, **options):
        # les id de cat qui on des articles vendu a zero tva :
        cat_ids = [71, 72, 73, 74, 75, 76, 77, 78, 79, 80]
        for cat in Categorie.objects.filter(id__in=cat_ids):
            # cat : Categorie
            articles_vendu = ArticleVendu.objects.filter(categorie=cat)
            articles_vendu.update(tva=cat.tva.taux)

        # On va refaire les clotures mensuelles et annuelle :
        clotures = ClotureCaisse.objects.filter(categorie__in=[ClotureCaisse.MENSUEL, ClotureCaisse.ANNUEL])
        for cloture in clotures:
            start, end = cloture.start, cloture.end
            ticketZ = TicketZ(start_date=start, end_date=end)
            if ticketZ.calcul_valeurs():
                ticketz_json = ticketZ.to_json
                cloture.ticketZ = ticketz_json
                cloture.save()
