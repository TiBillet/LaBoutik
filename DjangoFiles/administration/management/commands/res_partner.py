from APIcashless.models import Membre
from django.core.management.base import BaseCommand
import datetime, csv

class Command(BaseCommand):

    def handle(self, *args, **options):
        # argument in a dict here :
        print(options)
        file = open('res.partner.csv')
        csv_parser = csv.reader(file)
        l = 0
        for line in csv_parser:
            debut_adhesion_str = line[1]
            fin_adhesion_str = line[2]
            email = line[3]
            if l > 0 and debut_adhesion_str and fin_adhesion_str and email :
                debut_date = datetime.datetime.strptime(debut_adhesion_str, "%Y-%m-%d").date()
                fin_date = datetime.datetime.strptime(fin_adhesion_str, "%Y-%m-%d").date()
                derniere_cotisation = fin_date - datetime.timedelta(days=365)

                mbrs = Membre.objects.filter(email=email)
                if len(mbrs) == 1 :
                    print(mbrs)
                    mbrs.update(date_inscription=debut_date, date_derniere_cotisation=derniere_cotisation)

            l += 1
