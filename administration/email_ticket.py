from datetime import datetime, timedelta

import pytz
from django.core.mail import EmailMessage, send_mail
from prettytable import PrettyTable, MSWORD_FRIENDLY, MARKDOWN
from APIcashless.models import Configuration, CommandeSauvegarde, ArticleVendu, CarteCashless


class ticket_conso_jour():
    '''
    Besoin de ArticleVendu.objects.filter en input.
    Ex:
        date = datetime.now()
        carte = CarteCashless.objects.get(number='01E31CBB')
        t = ticket(carte, date)
        t.to_mail()

    '''

    def __init__(self, carte, date):
        self.configuration = Configuration.get_solo()
        self.nom_structure = self.configuration.structure if self.configuration.structure else "TiBillet"
        self.total_depense = 0
        self.total_recharge = 0

        self.date = self._date(date)
        self.carte_cashless: CarteCashless = carte

        self.ventes = self._recuperation_des_ventes()
        self.recharge = self.recuperation_des_rechargement_cashless()

        self.tableau = self._construction_tableau()
        self.longueur_ligne = len(self.tableau.get_string().partition('\n')[-0])
        self.header = self._construction_header()
        self.footer = self._construction_footer()

    def _date(self, date):
        if type(date) == str:
            date: str
            return datetime.strptime(date, "%d-%m-%Y")
        else:
            date: datetime
            return date.date()

    def intervale(self, date):
        tzlocal = pytz.timezone(self.configuration.fuseau_horaire)
        debut_jour = tzlocal.localize(
            datetime.combine(date, datetime.min.time()),
            is_dst=None) + timedelta(hours=4)

        lendemain_quatre_heure = tzlocal.localize(
            datetime.combine(date, datetime.max.time()),
            is_dst=None) + timedelta(hours=4)

        return debut_jour, lendemain_quatre_heure

    def _recuperation_des_ventes(self):
        debut_jour, lendemain_quatre_heure = self.intervale(self.date)

        articles_vendus = ArticleVendu.objects.filter(
            article__methode=self.configuration.methode_vente_article,
            membre=self.carte_cashless.membre,
            date_time__gte=debut_jour,
            date_time__lte=lendemain_quatre_heure
        )

        return articles_vendus

    def recuperation_des_rechargement_cashless(self):
        debut_jour, lendemain_quatre_heure = self.intervale(self.date)

        recharge_achetes = ArticleVendu.objects.filter(
            article__methode__in=[
                self.configuration.methode_ajout_monnaie_virtuelle,
                self.configuration.methode_ajout_monnaie_virtuelle_cadeau,
            ],
            membre=self.carte_cashless.membre,
            date_time__gte=debut_jour,
            date_time__lte=lendemain_quatre_heure
        )

        return recharge_achetes

    def _construction_header(self):
        header = f"\n" \
                 f"{'-' * self.longueur_ligne}\n" \
                 f"{self.nom_structure.upper()}\n" \
                 f"{self.configuration.adresse}\n" \
                 f"SIRET : {self.configuration.siret}\n" \
                 f"TEL : {self.configuration.telephone}\n" \
                 f"{self.configuration.email}\n" \
            # f"{'-' * self.longueur_ligne}\n" \
        # f"\n"

        return header

    def _construction_header_html(self):
        header = f"<br>" \
                 f"<p>{'-' * self.longueur_ligne}</p>" \
                 f"<p>{self.nom_structure.upper()}</p>" \
                 f"<p>{self.configuration.adresse}</p>" \
                 f"<p>SIRET : {self.configuration.siret}</p>" \
                 f"<p>TEL : {self.configuration.telephone}</p>" \
                 f"<p>{self.configuration.email}</p>" \

        return header

    def _construction_tableau(self):
        tableau = PrettyTable()
        tableau.field_names = ["Heure", "Article", "Qt", "Total"]
        tableau.title = f"{self.date.strftime('%d/%m/%Y')}"

        tableau.add_row([f"", f"", f"", f"", ])
        tableau.add_row([f"", f" - RECHARGE - ", f"", f"", ])
        tableau.add_row([f"", f"", f"", f"", ])

        for recharge in self.recharge:
            recharge: ArticleVendu
            self.total_recharge += recharge.total()

            tableau.add_row(
                [
                    f"{recharge.date_time.astimezone().strftime('%H:%M')}",
                    f"{recharge.moyen_paiement.name if recharge.moyen_paiement else self.configuration.monnaie_principale_cadeau.name} ",
                    f"",
                    f"{(recharge.qty * recharge.article.prix)}",
                ]
            )

        # Une ligne de séparation entre recharge et vente
        tableau.add_row([f"", f"", f"TOTAL", f"{self.total_recharge}", ])
        tableau.add_row([f"", f"", f"", f"", ])
        tableau.add_row([f"", f" - DEPENSE - ", f"", f"", ])
        tableau.add_row([f"", f"", f"", f"", ])

        for vente in self.ventes:
            vente: ArticleVendu
            self.total_depense += vente.total()
            self.carte_cashless: CarteCashless = vente.carte
            self.email = vente.membre.email

            # tableau.align["Heure"] = "l"
            # tableau.align["Total"] = "r"

            tableau.add_row(
                [
                    f"{vente.date_time.astimezone().strftime('%H:%M')}",
                    f"{vente.article.name}",
                    f"{vente.qty}",
                    f"{(vente.qty * vente.article.prix)}",
                ]
            )

        tableau.add_row([f"", f"", f"TOTAL", f"{self.total_depense}", ])
        tableau.add_row([f"", f"", f"", f"", ])

        return tableau

    def recuperation_assets(self, carte):
        """

        @type carte: CarteCashless
        """
        dict_assets = {}
        for asset in carte.assets.all():
            if asset.qty > 0:
                dict_assets[asset.monnaie.name] = asset.qty

        return dict_assets

    def _construction_footer(self):
        string_asset = "\n"
        dict_asset = self.recuperation_assets(self.carte_cashless)
        for asset in dict_asset:
            if float(dict_asset[asset]) > 0:
                string_asset += f"  - {dict_asset[asset]} {asset}\n"

        if string_asset == "\n":
            string_asset = " 0\n"

        footer = f"\n" \
                 f"TVA : {self.configuration.taux_tva}%\n" \
                 f"CARTE TIBILLET N° {self.carte_cashless}\n" \
                 f"Solde sur carte :" \
                 + string_asset + \
                 f"{'-' * self.longueur_ligne}\n" \
                 f"{self.configuration.pied_ticket}\n" \
                 f"{'-' * self.longueur_ligne}\n" \
                 f"\n"

        return footer

    def footer_html(self):
        string_asset = "\n"
        dict_asset = self.recuperation_assets(self.carte_cashless)
        for asset in dict_asset:
            if float(dict_asset[asset]) > 0:
                string_asset += f"<p> - {dict_asset[asset]} {asset}</p>"

        if string_asset == "\n":
            string_asset = "<p>  0</p> "

        footer_html = f"<br>" \
                 f"<p>TVA : {self.configuration.taux_tva}%</p>" \
                 f"<p>CARTE TIBILLET N° {self.carte_cashless}</p>" \
                 f"<p>Solde sur carte :</p>" \
                 + string_asset + \
                 f"<p>{self.configuration.pied_ticket}</p>" \

        return footer_html

    def print(self):
        print(
            f"{self.header}"
            f"{self.tableau}"
            f"{self.footer}"
        )

    def to_string(self):
        return (
            f"{self.header}"
            f"{self.tableau}"
            f"{self.footer}"
        )

    def to_mail(self):
        corps = f"Bonjour,\n" \
                f"\n" \
                f"Veuillez trouver ci dessous votre reçu pour toutes les transactions effectuées à l'aide de votre carte TiBillet à la date du {self.date.strftime('%d/%m/%Y')}.\n" \
                f"Bonne journée.\n\n" \
                f"L'équipe TiBillet.\n" \
                f"www.tibillet.re\n\n" \
                f"\n" \
                f"\n"

        corps += self.to_string()

        # from time import sleep; sleep(5)
        print(corps)
        # import ipdb; ipdb.set_trace()

        # print(f'from {self.configuration.email}')
        # print(f'to {self.email}')

        corps_html = "<p>Bonjour<p>" \
                     f"<p>Veuillez trouver ci dessous votre reçu pour toutes les transactions effectuées à l'aide de votre carte TiBillet à la date du {self.date.strftime('%d/%m/%Y')}.</p>" \
                     f"<p>Bonne journée</p>" \
                     f"<p>L'équipe TiBillet</p>" \
                     f"<p>www.tibillet.re</p>" \
                     f"<br>" \
                     f"{self._construction_header_html()}" \
                     f"{self.tableau.get_html_string()}" \
                     f"{self.footer_html()}" \

        try:
            send_mail(
                'Votre reçu TiBillet',
                corps,
                'contact@tibillet.re',
                [self.carte_cashless.membre.email],
                fail_silently=False,
                html_message=corps_html
            )
        except Exception as e:
            return e

        # email = EmailMessage(
        #     'Votre reçu TiBillet',
        #     corps,
        #     'contact@tibillet.re',
        #     [self.carte_cashless.membre.email],
        #     reply_to=[f"{self.configuration.email}"],
        #     headers={'Message-ID': 'foo'}
        # )
        #
        # try:
        #     return email.send(fail_silently=False)
        # except Exception as e:
        #     return e


def tableau_seul(self):
    tableau_seul = f"{self.tableau}".partition('|\n')[2]
    total = self.footer.split('\n')[2]
    text_seul = f"{tableau_seul} \n {total}"
    print(text_seul)
    return text_seul
