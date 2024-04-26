# import json
#
# import os
#
# import requests
# from _decimal import Decimal
#
# from APIcashless.models import Assets, MoyenPaiement, Configuration
# from APIcashless.tasks import update_federated_asset
#
# import logging
#
# from Cashless import settings
#
# logger = logging.getLogger(__name__)
#
#
# class WalletConnector:
#     def __init__(self,
#                  asset: Assets = None,
#                  update_asset: Decimal = None,
#                  old_qty: Decimal = None,
#                  config=None,
#                  ):
#
#         # Le wallet est le portefeuille de l'utilisateur.
#         self.asset: Assets = asset
#         self.carte = self.asset.carte
#         self.wallet_uuid = self.carte.wallet
#         self.monnaie: MoyenPaiement = asset.monnaie
#
#         self.old_qty = old_qty
#         self.update_asset = update_asset
#
#         self.config = config
#         if self.config is None:
#             self.config = Configuration.get_solo()
#
#         self.push = None
#         self.pull = None
#
#     # On vérifie que le wallet a besoin d'être mis à jour.
#     def is_valid(self):
#         # on met en majuscule et on rajoute _ au début du nom de la catégorie.
#         try:
#             if self.update_asset is not None and self.old_qty is not None:
#                 trigger_name = f"push_wallet_{self.monnaie.categorie.upper()}"
#                 self.push = getattr(self, f"{trigger_name}", None)
#                 if self.push:
#                     return True
#             elif self.update_asset is None and self.old_qty is None:
#                 trigger_name = f"pull_wallet_{self.monnaie.categorie.upper()}"
#                 self.pull = getattr(self, f"{trigger_name}", None)
#                 if self.pull:
#                     return True
#         except Exception as exc:
#             logger.error(f"WalletConnector ERROR : {exc} - {type(exc)}")
#             raise exc
#
#         logger.info(f"Pas de WalletConnector pour MoyenPaiement {self.monnaie}")
#         return False
#
#     # FEDOW = 'FD'
#     def pull_wallet_FD(self):
#         logger.info(f"    WALLET CONNECTOR is valid : PULL pull_wallet_FD")
#
#         # Recherche de la valeur dans le serveur FEDOW
#         config = self.config
#         session = requests.session()
#         try:
#             request_fedow = session.get(
#                 f"https://{config.fedow_domain}/wallet/{self.wallet_uuid}/",
#                 headers={"Authorization": f"Api-Key {config.fedow_key}"},
#                 verify=bool(not settings.DEBUG),
#                 timeout=1,
#             )
#             # logger.info(f"    get_federated_asset_from_cashless vers {config.fedow_domain}")
#             session.close()
#         except Exception as exc:
#             logger.error(f"pull_wallet_SF ERROR : {exc} - {type(exc)}")
#             session.close()
#             return f"pull_wallet_SF ERROR : {exc} - {type(exc)}"
#
#         if request_fedow.status_code == 200:
#
#             logger.info(
#                 f"    =========================== WalletConnector : response from FEDOW : {request_fedow.status_code}")
#             data = json.loads(request_fedow.content)
#             logger.info(f"    ==> data : {data}")
#
#
#
#         logger.error(f"pull_wallet_SF ERROR : status code : {request_fedow.status_code}")
#         return request_fedow.status_code
#
#     # def push_wallet_SF(self):
#     #     logger.info(f"    WALLET CONNECTOR is valid : PUSH wallet_SF -> task update_federated_asset.delay")
#     #     logger.info(f"        self.old_qty : {self.old_qty}, self.update_asset : {self.update_asset}")
#     #
#     #     update_federated_asset.delay(self.asset.pk, self.old_qty, self.update_asset)
