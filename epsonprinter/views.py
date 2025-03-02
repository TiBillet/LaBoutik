import dateutil.parser
import json

import time
import uuid

import requests
import unicodedata
import logging

from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

from webview.serializers import debut_fin_journee
from APIcashless.models import CommandeSauvegarde, GroupementCategorie, ArticleCommandeSauvegarde, Configuration, \
    ArticleVendu

'''
https://python-escpos.readthedocs.io/en/latest/user/raspi.html
Lancer un flask sur un raspberry !

'''

# Variables globales pour imprimante thermique TM20-III
CUTPERJOB, CUTPERPAGE, NOCUT = "CutPerJob", "CutPerPage", "NoCut"
PRINTER203 = "TM-20III-203"
PRINTER180 = "TM-20III-180"
NB_TIRETS = 32
LINE = "-" * NB_TIRETS + "\n"


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode("latin-1")  # utf-8
def nb_spacex(spacex) :
    nb_car = round(len(spacex) / 2)
    nb_space = round(NB_TIRETS/2 - nb_car)
    return nb_space

def centrer(input_centre):
    if not input_centre:
        return " "
    if len(input_centre) < NB_TIRETS:
        input_centre = " " * nb_spacex(input_centre) + input_centre
    else:
        ligne_32_caracteres = input_centre[:NB_TIRETS-1]# la ligne de 32 caracteres sans le "\n"
        dernier_espace = ligne_32_caracteres.rfind(" ")
        ligne_complement = input_centre[dernier_espace:len(input_centre)]
        if dernier_espace != -1 and dernier_espace <32:
            ligne_32_caracteres = ligne_32_caracteres[:dernier_espace]
            #nb_car = round(len(ligne_32_caracteres) / 2)
            #nb_space = round(NB_TIRETS/2 - nb_car)
            #ligne_32_caracteres = " " * nb_space +ligne_32_caracteres
            ligne_32_caracteres = " " * nb_spacex(ligne_32_caracteres) + ligne_32_caracteres

            #nb_car2 = round(len(ligne_complement) / 2)
            #nb_space2 = round(NB_TIRETS/2 - nb_car2)
            #input_centre = ligne_32_caracteres + "\n" + " " * nb_space2 + ligne_complement
            input_centre = ligne_32_caracteres + "\n" + " " * nb_spacex(ligne_complement) + ligne_complement
        # import ipdb;ipdb.set_trace()
    return input_centre


def align_right(input_right):  # align droite: couper la str en 2 avec comme repere ":" et supprimer ":" lors impression
    if len(input_right) < 32:
        position_2points = input_right.find(":") + 1
        nb_car = len(input_right)
        nb_right = (32 - nb_car)+2 # le +2 pour tenir compte des indices de \n titi=toto\n =>len(titi)=5 et position_2points = input_right.find(":") + 1
        input_right = input_right[:position_2points - 1] + " " * nb_right + input_right[position_2points:]
    return input_right


class print_billet_qrcode():
    pass


class print_command():

    def __init__(self,
                 commande,
                 groupement_solo=None
                 ):
        """

        @type commande: CommandeSauvegarde
        @type billet: ArticleVendu
        """

        self.config = Configuration.get_solo()

        self.commande: CommandeSauvegarde = commande
        self.date = commande.datetime.astimezone().strftime("%H:%M %d-%m-%Y")
        self.table = commande.table

        self.lignes_article = commande.articles.all()
        self.articles = [ligne_article.article for ligne_article in self.lignes_article]

        if groupement_solo:
            self.groupements = GroupementCategorie.objects.filter(pk=groupement_solo.pk)
        else:
            self.groupements = GroupementCategorie.objects.filter(categories__articles__in=self.articles).distinct()

        self.articles_classes = self._articles_classes()

    def _header(self, groupe):
        header = str()
        header += LINE
        header += f"{groupe.name.upper()}\n"
        header += f"{self.date}\n"
        header += f"TABLE : {self.table.name}\n"
        header += f"RESPONSABLE : {self.commande.responsable.name}\n"
        header += f"ID COMMANDE : {self.commande.id_commande()[:3]}\n"
        header += f"SERVICE : {self.commande.id_service()[:3]}\n"
        header += LINE
        header = remove_accents(header)
        return header.upper()

    def _footer(self):
        footer = str()
        footer += LINE

        if len(self.commande.commentaire) > 0:
            footer += f"COMMENTAIRE : \n"
            footer += f"{self.commande.commentaire}\n"
            footer += LINE

        footer += "\n"
        footer = remove_accents(footer)
        return footer

    def _articles_classes(self):
        groupements = self.groupements
        lignes_articles = self.lignes_article

        article_groupee = {}
        for groupement in groupements:
            categories_groupee = groupement.categories.all()
            article_groupee[groupement] = []

            for ligne_article in lignes_articles:
                if ligne_article.article.categorie in categories_groupee:
                    article_groupee[groupement].append(ligne_article)

        return article_groupee

    def _txt_article(self, lignes_articles):
        corps = f"\n"

        for ligne in lignes_articles:
            ligne: ArticleCommandeSauvegarde
            corps += f"{int(ligne.qty)} x {ligne.article.name}\n"

        corps += f"\n"
        corps = remove_accents(corps)
        return corps

    # def to_string(self):
    #
    #     tickets_string = []
    #     for groupe in self.articles_classes:
    #         tickets_string.append(
    #             f"{self._header_commande(groupe)}"
    #             f"{self._txt_article(self.articles_classes[groupe])}"
    #             f"{self._footer()}"
    #         )
    #     return tickets_string

    def can_print(self):
        for groupe in self.articles_classes:
            if groupe.printer:
                return True

        return False

    # noinspection PyStatementEffect
    def to_printer(self):

        for groupe in self.articles_classes:
            header = f"{self._header(groupe)}"
            body = f"{self._txt_article(self.articles_classes[groupe])}"
            footer = f"{self._footer()}"

            if groupe.printer:

                data = self.commande.numero_du_ticket_imprime
                title = ""
                if data.get(groupe.name):
                    title = f"{groupe.name} {data.get(groupe.name)}"
                else:
                    groupe.compteur_ticket_journee += 1
                    self.commande.numero_du_ticket_imprime[groupe.name] = groupe.compteur_ticket_journee
                    groupe.save()
                    self.commande.save()

                    title = f"{groupe.name} {groupe.compteur_ticket_journee}"

                # Pour serveur sous flask :
                req = requests.session()
                reponse = req.post(f'{groupe.printer.serveur_impression}',
                                   data={
                                       'coucouapi': groupe.printer.api_serveur_impression,
                                       'adresse_printer': groupe.printer.thermal_printer_adress,
                                       'copy': groupe.qty_ticket,

                                       'title': title,
                                       'header': header,
                                       'body': body,
                                       'footer': footer,
                                   })

                logger.info(f"REPONSE Serveur impression : {reponse.status_code} - {reponse.text}")

                req.close()


class article_direct_to_printer():

    def __init__(self, article_vendu):
        """

        @type article_vendu : ArticleVendu
        """
        self.article_vendu: ArticleVendu = article_vendu
        self.nbr_billet_vendu = self._check_nbr_billet_vendu()
        self.qrcode = None

    def _check_nbr_billet_vendu(self):
        nbr_billet_vendu = None
        if self.article_vendu.article.decompte_ticket:
            debut, fin = debut_fin_journee()
            nbr_billet_vendu = ArticleVendu.objects.filter(date_time__gte=debut,
                                                           article__decompte_ticket=True).aggregate(Sum('qty')).get(
                'qty__sum', 0)

            logger.info(f"nbr_billet_vendu : {nbr_billet_vendu}")

        return nbr_billet_vendu

    def _title(self):
        title = str()
        title += self.article_vendu.article.name
        title = remove_accents(title)
        return title

    def _header(self):
        header = str()
        header += LINE
        header += f"{self.article_vendu.article.name.upper()}\n"
        header += f"{self.article_vendu.date_time.strftime('%d-%m-%Y %H:%M')}\n"
        header += f"ID : {self.article_vendu.id_commande()}\n"
        header += f"RESPONSABLE : {self.article_vendu.responsable.name}\n"
        if self.article_vendu.membre:
            header += f"MEMBRE : {self.article_vendu.membre}\n"
        header += f"PRIX : {self.article_vendu.article.prix} euros\n"
        header = remove_accents(header)
        return header.upper()

    def _footer(self):
        config = Configuration.get_solo()

        footer = str()
        footer += LINE
        footer += f"{config.structure}\n"
        footer += f"{config.adresse}\n"
        footer += f"{config.siret}\n"
        footer += f"{config.telephone}\n"
        footer += f"{config.email}\n"
        footer += LINE
        footer += f"{config.pied_ticket}\n"
        footer += LINE
        footer = remove_accents(footer)
        return footer

    def can_print(self):
        if self.article_vendu.article.direct_to_printer:
            return True
        return False

    # noinspection PyStatementEffect
    def to_printer(self):

        # On itère de 0 à qty pour imprimer autant de ticket que de billets vendus
        for num_qty in range(0, int(self.article_vendu.qty)):
            title = self._title()
            header = self._header()
            body = ''
            qrcode = None
            footer = self._footer()

            # si le numéro de billet doit être affiché
            # et s'il y en a plusieurs à imprimmer,
            # on décompte des quantités vendues pour avoir
            # un numéro différent à chaque impréssion :
            if self.nbr_billet_vendu:
                numero_ticket = self.nbr_billet_vendu - num_qty
                title += f" N:{int(numero_ticket)}"
                # header += f"NUMERO {int(numero_ticket)}\n"
                # qrcode = f"T{num_qty}-{self.article_vendu.id_commande()}"

            # Pour serveur sous flask :
            req = requests.session()

            printer = self.article_vendu.article.direct_to_printer

            busy = True
            nb_try = 0
            while busy == True and nb_try < 20:
                busy = False
                nb_try += 1
                reponse = req.post(f'{printer.serveur_impression}',
                                   data={
                                       'coucouapi': printer.api_serveur_impression,
                                       'adresse_printer': printer.thermal_printer_adress,
                                       'copy': 1,
                                       'title': title,
                                       'header': header,
                                       'body': body,
                                       'qrcode': qrcode,
                                       'footer': footer,
                                   })
                if "Resource busy" in reponse.text:
                    time.sleep(0.5)
                    busy = True
                    logger.info(f"nb_try : {nb_try}")
                logger.info(f"REPONSE Serveur impression : {reponse.status_code} - {reponse.text}")

            req.close()


class TicketZPrinter():

    def __init__(self, ticketz_json):
        self.config = Configuration.get_solo()
        self.ticketz_json = json.loads(ticketz_json)

    def _header(self):
        config = self.config
        header = str()
        start_date = dateutil.parser.parse(self.ticketz_json.get('start_date'))
        end_date = dateutil.parser.parse(self.ticketz_json.get('end_date'))

        header += LINE
        header += f"{centrer(config.structure)}\n"
        header += f"{centrer(config.adresse)}\n"
        header += f"{centrer('Siret:')}\n"
        header += f"{centrer(config.siret)}\n"
        header += LINE

        # Pour checker le formatage de date : https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
        header += align_right(f"Impression:{timezone.localtime().strftime('%d/%m/%Y %H:%M')}\n")
        header += align_right(f"Ouverture:{start_date.strftime('%d/%m/%Y %H:%M')}\n")
        header += align_right(f"Fermeture:{end_date.strftime('%d/%m/%Y %H:%M')}\n")

        header += LINE
        header += f""
        header = remove_accents(header)
        return header

    def _body(self):
        dict_from_json = self.ticketz_json.get('dict_moyenPaiement_euros')
        dict_TVA = self.ticketz_json.get('dict_TVA')
        body = str()

        # Tableau des moyens de paiments
        body += LINE

        for moyen_paiement, valeur in dict_from_json.items():
            body += align_right(f"{moyen_paiement.upper()}:{valeur} EUR\n")


        # Total HT&TTC
        body += LINE
        body += align_right(f"TOTAL HT:{self.ticketz_json.get('total_HT')} EUR\n")
        body += align_right(f"TOTAL TVA:{self.ticketz_json.get('total_collecte_toute_tva')} EUR\n")
        body += align_right(f"TOTAL TTC:{self.ticketz_json.get('total_TTC')} EUR\n")
        body += align_right(f"TOTAL Offert:{self.ticketz_json.get('total_gift_by_mp')} EUR\n")

        # Ventillation TVA
        body += LINE
        for tva, total in dict_TVA.items():
            body += align_right(f"TVA {tva}%:{total} EUR\n")
        # body += f"TOTAL TVA : {self.ticketz_json.get('dict_TVA')}  EUR\n"
        body += align_right(f"TOTAL TVA:{self.ticketz_json.get('total_collecte_toute_tva')} EUR\n")
        # import ipdb;ipdb.set_trace()

        # Cashless
        body += LINE
        body += f"{centrer('CASHLESS:')} \n"
        body += align_right(f"Recharge:{self.ticketz_json.get('total_recharge')} EUR\n")
        body += align_right(f"Recharge cadeau:{self.ticketz_json.get('total_recharge_cadeau')} EUR\n")
        body += align_right(f"Remboursement:{self.ticketz_json.get('total_remboursement')} EUR\n")

        # Fond de caisse :
        body += LINE
        body += f"{centrer('FOND DE CAISSE ESPECE :')} \n"
        body += align_right(f"Fond caisse initial:{self.ticketz_json.get('fond_caisse')} EUR\n")
        body += align_right(f"+ cashless esp:{self.ticketz_json.get('recharge_cash')} EUR\n")
        body += align_right(f"- cashless esp:{self.ticketz_json.get('remboursement_espece')} EUR\n")
        body += align_right(f"Adhésion en esp:{self.ticketz_json.get('adhesion_espece')} EUR\n")
        body += align_right(f"Ventes en esp:{self.ticketz_json.get('ventes_directe_espece')} EUR\n")
        body += align_right(f"Fond caisse final:{self.ticketz_json.get('total_cash')} EUR\n")
        body = remove_accents(body)
        return body

    def _footer(self):
        config = self.config
        pied = config.pied_ticket if config.pied_ticket else ""
        footer = str()
        footer += LINE
        footer += f"{centrer(pied)}"
        return footer

    def can_print(self):
        if self.config.ticketZ_printer:
            return True
        return False

    def to_printer(self):

        # On itère de 0 à qty pour imprimer autant de ticket que de billets vendus
        title = "TICKETZ"
        header = self._header()
        body = self._body()
        footer = self._footer()

        # Pour serveur sous flask :
        req = requests.session()

        printer = self.config.ticketZ_printer

        try :
            busy = True
            nb_try = 0
            while busy == True and nb_try < 20:
                busy = False
                nb_try += 1
                reponse = req.post(f'{printer.serveur_impression}',
                                   data={
                                       'coucouapi': printer.api_serveur_impression,
                                       'adresse_printer': printer.thermal_printer_adress,
                                       'copy': 1,
                                       'title': title,
                                       'header': header,
                                       'body': body,
                                       'footer': footer,
                                   })

                if "Resource busy" in reponse.text:
                    time.sleep(0.5)
                    busy = True
                    logger.info(f"nb_try : {nb_try}")
                logger.info(f"REPONSE Serveur impression : {reponse.status_code} - {reponse.text}")
        except ConnectionError :
            logger.error(f"TicketZPrinter ConnectionError")
        except Exception as e:
            logger.error(f"TicketZPrinter Exception : {e}")

        req.close()
