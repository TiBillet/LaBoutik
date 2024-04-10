import csv
from uuid import UUID
from APIcashless.models import CarteCashless
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):

        # file = open('data/retour_usine_raff_gen_2.csv')
        input_fichier_csv = input('path fichier csv ? \n')
        file = open(input_fichier_csv)

        csv_parser = csv.reader(file)
        list_csv = []
        l=0
        for line in csv_parser:
            uuid_qrcode = UUID(line[0].partition('/qr/')[2])
            number = line[1]
            tag_id = line[2]
            print(f"uuid_qrcode: {uuid_qrcode} number: {number} tag_id: {tag_id}")
            CarteCashless.objects.get_or_create(
                uuid_qrcode=uuid_qrcode,
                tag_id=tag_id,
                number=number,
            )

            l += 1
        file.close()