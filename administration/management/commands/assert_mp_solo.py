import os

from django.core.management import BaseCommand

from APIcashless.models import Configuration, MoyenPaiement


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.CASH)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name="Espece", blockchain=False, categorie=MoyenPaiement.CASH)
        except Exception as e:
            raise e

        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.CREDIT_CARD_NOFED)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name="Carte bancaire", blockchain=False,
                                                categorie=MoyenPaiement.CREDIT_CARD_NOFED)
        except Exception as e:
            raise e

        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.STRIPE_NOFED)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name="Web (Stripe)", blockchain=False,
                                                categorie=MoyenPaiement.STRIPE_NOFED)
        except Exception as e:
            raise e

        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.COMMANDE)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name="Commande", blockchain=False,
                                                categorie=MoyenPaiement.COMMANDE)
        except Exception as e:
            raise e

        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.OCECO)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name="Web (Oceco)", blockchain=False,
                                                categorie=MoyenPaiement.OCECO)
        except Exception as e:
            raise e

        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name=os.environ.get('NOM_MONNAIE'),
                                                blockchain=True,
                                                categorie=MoyenPaiement.LOCAL_EURO)
        except Exception as e:
            raise e

        try:
            MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name=f"{os.environ.get('NOM_MONNAIE')} Cadeau",
                                                cadeau=True,
                                                blockchain=True,
                                                categorie=MoyenPaiement.LOCAL_GIFT)
        except Exception as e:
            raise e

        try:
            assert MoyenPaiement.objects.get(categorie=MoyenPaiement.STRIPE_FED)
        except MoyenPaiement.DoesNotExist:
            MoyenPaiement.objects.get_or_create(name=f"TiBillet (Fédérée)",
                                                is_federated=True,
                                                blockchain=True,
                                                categorie=MoyenPaiement.STRIPE_FED)
        except Exception as e:
            raise e

        CATEGORIES = MoyenPaiement.CATEGORIES
        for categorie in CATEGORIES:
            if categorie[0] not in [MoyenPaiement.CHEQUE, MoyenPaiement.ARDOISE]:
                print(categorie)
                assert MoyenPaiement.objects.get(categorie=categorie[0])

        for mp in MoyenPaiement.objects.all():
            print(f"{mp.name} : {mp.categorie}")
