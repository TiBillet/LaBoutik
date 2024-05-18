import uuid, csv, datetime
from collections import Counter

# PREFIX = input("entrez le préfixe. \n ex : https://{PREFIX}.tibillet.re/qr/ :")
PREFIX = "yourplace"
assert PREFIX

url = f"https://{PREFIX}.tibillet.coop/qr/"

csv_file = f"qrcode_url_and_number_for_print_{PREFIX}.csv"

csv_columns = ['qrcode url', 'number to print']
liste_carte = []

list_exist_cards = []



# on vérifie si il n'y a pas de doublons et nous créons la liste des cartes existantes.
with open('exist_cards', 'r') as exist_cards_read :
    exist_cards_lines = [_.rstrip('\n') for _ in exist_cards_read.readlines()]

for line in exist_cards_lines:
    if len(line) == 8 :
        if line not in list_exist_cards :
            list_exist_cards.append(line)
        else :
            print(line)
            raise Exception(f'doublons ! {line}')
    else :
        print(line)


exist_cards = open('exist_cards', 'a')
exist_cards.writelines('\n')
exist_cards.writelines('\n')
exist_cards.writelines(f'{PREFIX} {datetime.datetime.now().date()}\n')
exist_cards.writelines('\n')
exist_cards.writelines('\n')



for x in range(0,2200):
    uid = uuid.uuid4()
    first_block_uuid = str(uid).split('-')[0]

    # si le premier morceau de l'uuid est un entier, on supprime.
    try:
        int(first_block_uuid)
    except Exception as e:
        pass
    else:
        print(f'Int Only : {first_block_uuid}')
        continue

    # si il n'y a qu'un "e" et que des chiffres, on supprime,
    # c'est considéré comme une puissance de 10 par excel
    # ça a foiré l'impréssion paske l'usine utilise excel ...
    x_int = 0
    x_e = Counter(first_block_uuid)['e']
    for x in first_block_uuid :
        if x.isdigit():
            x_int += 1

    if x_int == 7 and x_e == 1 :
        print(f'Int with e Only : {first_block_uuid}')
        continue



    id_to_print = first_block_uuid.upper()

    if id_to_print not in list_exist_cards :
        liste_carte.append(
            {
            'qrcode url':f'{url}{uid}',
            'number to print': id_to_print,
            }
            )
        exist_cards.writelines(f'{id_to_print}\n')

try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in liste_carte:
            writer.writerow(data)
except IOError:
    print("I/O error")

exist_cards.close()