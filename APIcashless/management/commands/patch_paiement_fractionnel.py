from fontTools.varLib.instancer.names import pruningUnusedNames

from APIcashless.models import Methode, Configuration, Articles, MoyenPaiement

configuration = Configuration.get_solo()

paiement_fractionne = Methode.objects.get_or_create(name="PaiementFractionne")[0]

moyen_de_paiement_fractionne = MoyenPaiement.objects.get_or_create(name="Paiement Fractionné")[0]

configuration.methode_paiement_fractionne = paiement_fractionne
configuration.moyen_paiement_fractionne = moyen_de_paiement_fractionne
configuration.save()

try :
    art = Articles.objects.get(methode_choices = Articles.FRACTIONNE)
except Articles.DoesNotExist:
    art = Articles.objects.get_or_create(name="Paiement Fractionné",
                                         categorie=None,
                                         prix=1,
                                         prix_achat=1,
                                         fractionne=True,
                                         methode_choices = Articles.FRACTIONNE,
                                         methode=paiement_fractionne)[0]

except Exception as e:
    print(e)