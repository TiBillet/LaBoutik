"""
Tests de la borne kiosk TPE Stripe.
/ Kiosk Stripe terminal tests.

LOCALISATION : htmxview/tests.py

Ces tests parlent a la VRAIE API Stripe, en mode test, avec un lecteur SIMULE
(`simulated_wisepos_e`). Ils ne demandent aucun materiel.

POURQUOI DE VRAIS APPELS RESEAU PLUTOT QU'UN MOCK :
ce qu'on veut verifier n'est pas « le code appelle bien telle methode », c'est
« Stripe se comporte-t-il comme on le croit ». Un mock repondrait ce qu'on lui a
appris et laisserait passer le bug d'origine : le lecteur qui reste ARME apres un
timeout. Seul le vrai simulateur peut le prouver.
/ Real network calls, not mocks: what we verify is Stripe's actual behaviour, which
a mock would happily fake.

ILS SONT IGNORES si `STRIPE_TEST_API_KEY` est absent de l'environnement — donc en
integration continue sans cle, la suite passe sans eux.
"""
import logging
import os
from unittest import skipUnless

import stripe
from django.test import TestCase, override_settings

from APIcashless.models import (
    ConfigurationStripe,
    PaymentsIntent,
    PointDeVente,
    Terminal,
)
from htmxview.tasks import cancel_payment_on_stripe

logger = logging.getLogger(__name__)

# La cle doit etre une cle de TEST. On ne lance jamais ces tests sur autre chose :
# ils creent des intentions de paiement et arment un lecteur.
# / The key must be a TEST key: these tests create payment intents.
CLE_STRIPE_DE_TEST = os.environ.get("STRIPE_TEST_API_KEY", "")
CLE_STRIPE_DE_TEST_PRESENTE = CLE_STRIPE_DE_TEST.startswith("sk_test_")


@skipUnless(
    CLE_STRIPE_DE_TEST_PRESENTE,
    "STRIPE_TEST_API_KEY absent ou non 'sk_test_' : tests du TPE simule ignores",
)
# DEMO doit etre desactive : en mode demo, `cancel_payment_on_stripe` ne parle pas a
# Stripe du tout (il n'y a pas de TPE a annuler) et ces tests n'auraient aucun sens.
# / DEMO must be off: in demo mode the function never talks to Stripe.
@override_settings(DEMO=False)
class AnnulationPaiementSurStripeTest(TestCase):
    """
    Verifie `htmxview.tasks.cancel_payment_on_stripe`.

    L'INVARIANT PROTEGE : aucun ecran « Annule » ne doit atteindre la borne sans que
    l'annulation ait ete reellement faite chez Stripe. Tant que l'action du lecteur
    n'est pas annulee, le WisePOS reste arme et encaisse encore une carte presentee
    tardivement — derriere un ecran qui affiche « Annule ».
    / Protected invariant: no "canceled" screen without a real Stripe cancellation.
    """

    @classmethod
    def setUpClass(cls):
        """Cree un lecteur simule chez Stripe, partage par tous les tests de la classe."""
        super().setUpClass()
        stripe.api_key = CLE_STRIPE_DE_TEST

        cls.location_stripe = stripe.terminal.Location.create(
            display_name="TEST LaBoutik kiosk",
            address={
                "line1": "1 rue du Test",
                "city": "Saint-Denis",
                "country": "FR",
                "postal_code": "97400",
            },
        )
        cls.lecteur_simule = stripe.terminal.Reader.create(
            registration_code="simulated-wpe",
            label="TEST LaBoutik kiosk",
            location=cls.location_stripe.id,
        )

    @classmethod
    def tearDownClass(cls):
        """Supprime le lecteur simule et sa location : on ne laisse rien derriere nous."""
        stripe.api_key = CLE_STRIPE_DE_TEST
        try:
            stripe.terminal.Reader.delete(cls.lecteur_simule.id)
            stripe.terminal.Location.delete(cls.location_stripe.id)
        except Exception as erreur_de_nettoyage:
            logger.error(f"Nettoyage du lecteur simule impossible -- {erreur_de_nettoyage}")
        super().tearDownClass()

    def setUp(self):
        """Prepare le minimum en base : la config Stripe, un TPE et un point de vente."""
        # stripe_mode_test=True fait pointer get_stripe_api() sur STRIPE_TEST_API_KEY.
        # / stripe_mode_test=True makes get_stripe_api() return the test key.
        configuration_stripe = ConfigurationStripe.get_solo()
        configuration_stripe.stripe_mode_test = True
        configuration_stripe.save()

        self.terminal_de_test = Terminal.objects.create(
            name="TPE de test",
            type=Terminal.STRIPE_WISEPOS,
            stripe_id=self.lecteur_simule.id,
        )
        self.point_de_vente = PointDeVente.objects.create(name="Kiosk de test")

    def armer_le_lecteur_avec_une_nouvelle_intention(self, montant_en_centimes=1000):
        """
        Cree une intention de paiement, l'envoie au lecteur simule, et renvoie
        l'objet PaymentsIntent enregistre en base.

        Reproduit ce que fait `PaymentsIntent.send_to_terminal` (APIcashless/models.py)
        sans dependre de la configuration Fedow, hors sujet ici.
        / Mirrors send_to_terminal without the Fedow configuration, out of scope here.
        """
        intention_stripe = stripe.PaymentIntent.create(
            amount=montant_en_centimes,
            currency="eur",
            payment_method_types=["card_present"],
            capture_method="automatic",
        )
        stripe.terminal.Reader.process_payment_intent(
            self.lecteur_simule.id,
            payment_intent=intention_stripe.id,
        )
        return PaymentsIntent.objects.create(
            amount=montant_en_centimes,
            terminal=self.terminal_de_test,
            pos=self.point_de_vente,
            payment_intent_stripe_id=intention_stripe.id,
            status=PaymentsIntent.IN_PROGRESS,
        )

    def statut_action_du_lecteur(self):
        """Renvoie le statut de la derniere action du lecteur, ou None s'il est au repos."""
        lecteur = stripe.terminal.Reader.retrieve(self.lecteur_simule.id)
        if not lecteur.action:
            return None
        return lecteur.action.status

    def test_le_lecteur_reste_arme_tant_qu_on_ne_l_annule_pas(self):
        """
        Sans annulation, le lecteur reste ARME apres l'envoi du paiement.

        C'est la raison d'etre de `cancel_payment_on_stripe` : ce test echouerait si
        Stripe desarmait tout seul, et la fonction deviendrait inutile.
        / This is why cancel_payment_on_stripe exists.
        """
        self.armer_le_lecteur_avec_une_nouvelle_intention()

        self.assertEqual(
            self.statut_action_du_lecteur(),
            "in_progress",
            "Le lecteur devrait rester arme tant qu'aucune annulation n'est faite",
        )

    def test_l_annulation_desarme_le_lecteur_et_annule_le_paiement(self):
        """
        Le cas du timeout : aucune carte presentee, la surveillance s'arrete.
        Apres annulation, le lecteur est au repos et le paiement est annule en base.
        """
        payment_intent = self.armer_le_lecteur_avec_une_nouvelle_intention()

        cancel_payment_on_stripe(payment_intent)

        self.assertNotEqual(
            self.statut_action_du_lecteur(),
            "in_progress",
            "Le lecteur doit etre au repos : arme, il encaisserait une carte tardive",
        )

        payment_intent.refresh_from_db()
        self.assertEqual(
            payment_intent.status,
            PaymentsIntent.CANCELED,
            "Le statut annule doit etre PERSISTE : le websocket le relit au rejeu d'etat",
        )

    def test_un_paiement_abouti_reste_un_succes_malgre_la_tentative_d_annulation(self):
        """
        Le cas de la course : la carte est presentee juste avant que la surveillance
        n'abandonne. Stripe refuse alors d'annuler un paiement deja abouti.

        Le statut final doit etre SUCCEEDED — c'est lui qui fait afficher « Reussite »
        a la borne. Afficher « Annule » ici reviendrait a mentir sur un encaissement
        reel : l'usager rechargerait une seconde fois.
        / A finished payment must stay a success: showing "canceled" would lie about
        real money taken.
        """
        payment_intent = self.armer_le_lecteur_avec_une_nouvelle_intention(montant_en_centimes=1500)

        # La carte est presentee : le paiement aboutit avant la tentative d'annulation.
        # / The card is presented: payment succeeds before the cancellation attempt.
        stripe.terminal.Reader.TestHelpers.present_payment_method(self.lecteur_simule.id)

        cancel_payment_on_stripe(payment_intent)

        payment_intent.refresh_from_db()
        self.assertEqual(
            payment_intent.status,
            PaymentsIntent.SUCCEEDED,
            "Un paiement abouti doit rester un succes, meme si l'annulation a ete tentee",
        )
