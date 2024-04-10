import csv
from datetime import datetime

from APIcashless.models import CarteCashless, Membre
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        file = open('data/pareypaparey.csv')
        csv_parser = csv.reader(file)
        l = 1
        csv_list = []
        email = ""
        for line in csv_parser:
            print(line)
            csv_list.append(line)
            nom = line[0]
            prenom = line[1]
            tarif = line[2]
            email = line[3]
            telephone = line[4].replace(' ','')
            codePostal = line[5].replace(' ','')
            dNaissance = line[6]

            # print(f"{nom} {prenom} {tarif} {email} {telephone} {codePostal} {dNaissance}")
            if email :

                mbrs = Membre.objects.filter(email=email)
                if len(mbrs) > 0 :
                    mbr = mbrs[0]

                else :
                    mbr, created = Membre.objects.get_or_create(
                        email=email,
                        name=nom.upper(),
                        prenom=prenom,
                    )

            else :
                mbr, created = Membre.objects.get_or_create(
                        name=nom.upper(),
                        prenom=prenom,
                    )

            mbr.commentaire=f"PPP : {tarif}"

            if telephone:
                mbr.tel = telephone
            if codePostal:
                mbr.code_postal = int(codePostal)
            if dNaissance:
                date_n = datetime.strptime(dNaissance,"%d/%m/%Y")
                mbr.date_naissance=date_n

            mbr.save()


            # print(f"uuid_qrcode: {uuid_qrcode} number: {number} tag_id: {tag_id}")

            l += 1
        file.close()
