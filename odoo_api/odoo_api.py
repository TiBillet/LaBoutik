import decimal
import json

import requests

from APIcashless.models import Configuration, Odoologs, ArticleVendu, MoyenPaiement


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


class OdooAPI():

    def __init__(self, config=None):
        if not config:
            config = Configuration.get_solo()
        self.config = config

        # On test si l'url est bien formaté :
        self.url = self.config.odoo_url
        if not self.url.endswith("/"):
            self.url = f"{self.url}/"

    def _log(self, result):
        Odoologs.objects.create(log=f"{result}")


    def _post(self, path=None, params=None):
        header = {
            'content-type': 'application/json'
        }
        data = {
            "params": {
                "db": f"{self.config.odoo_database}",
                "login": f"{self.config.odoo_login}",
                "apikey": f"{self.config.odoo_api_key}",
            }
        }
        if params:
            data['params'].update(params)

        data_json = json.dumps(data, cls=DecimalEncoder)
        session = requests.session()
        url = f"{self.url}tibillet-api/xmlrpc/{path}/"
        request = session.post(url, data=data_json, headers=header)
        result = json.loads(request.content).get('result')
        return request, result

    def get_account_journal(self):
        return self._post(path="account_journal")

    def new_membership(self, article_vendu: ArticleVendu):
        PAYMENT_TO_JOURNAL = {
            MoyenPaiement.CASH : self.config.journal_odoo_espece,
            MoyenPaiement.CREDIT_CARD_NOFED: self.config.journal_odoo_cb,
            MoyenPaiement.STRIPE_NOFED: self.config.journal_odoo_stripe,
        }

        params  = {
            "create_invoice": self.config.odoo_create_invoice_membership,
            "set_payment": self.config.odoo_set_payment_auto,
            "journal_out_invoice_name": self.config.journal_out_invoice,
            "membre": {
                "name": f"{article_vendu.membre.prenom.capitalize()} {article_vendu.membre.name.upper()}",
                "email": f"{article_vendu.membre.email}"
            },
            "adhesion": {
                "category": f"{article_vendu.article.name}",
                "product_name": f"{article_vendu.article.name}",
                "price_unit": article_vendu.prix,
                "datetime_str": article_vendu.date_time.strftime("%Y-%m-%d"),
                # Doit être une string au même nom que le journal odoo
                "payment_method": PAYMENT_TO_JOURNAL.get(article_vendu.moyen_paiement.categorie)
            }
        }
        request, result = self._post(path="new_membership", params=params)
        self._log(result)
        if request.status_code != 200:
            raise ConnectionError(f"Status code : {request.status_code} - result : {result}")
        if result.get('error'):
            raise ValueError(f"{result.get('error')}")

        article_vendu.comptabilise = True
        article_vendu.save()
        return result


    def test_login(self):
        try :
            test_request, result = self._post(path="login")
        except Exception as e:
            raise ConnectionError(f"Odoo API not configured : {e}")
        if test_request.status_code != 200:
            raise ConnectionError(f"Status code : {test_request.status_code} - result : {result}")
        elif result.get('error'):
            raise ValueError(f"{result.get('error')}")

