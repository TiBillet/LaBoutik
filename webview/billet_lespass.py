"""
Envoi d'une vente de billet vers Lespass (API v2).
/ Sends a POS ticket sale to Lespass (API v2).

LOCALISATION : webview/billet_lespass.py

Cas d'usage : un billet d'évènement est vendu en caisse (article avec
methode_choices = BILLET). Le billet doit exister côté Lespass pour que
le client puisse être scanné à l'entrée.

FLUX :
1. webview/views.py : Commande.methode_BI appelle CETTE FONCTION
2. POST https://lespass/api/v2/reservations/ avec la clé API Lespass
3. Lespass déduit l'évènement depuis le tarif (uuid de l'article)
4. Lespass crée : Reservation valide + Tickets + ligne de vente
5. On retourne le JSON de la réservation créée

COMMUNICATION :
- Auth : header Authorization Api-Key (Configuration.lespass_api_key)
- La clé API doit avoir la permission "reservation" côté Lespass.
- L'uuid d'un Article LaBoutik = l'uuid du tarif (Price) Lespass.
  C'est déjà le cas pour tous les articles importés depuis Lespass
  (voir APIcashless/validator.py : ProductFromLespassValidator).

En cas d'échec, on lève EnvoiBilletErreur avec un message lisible :
l'appelant transforme ce message en refus de vente (NotAcceptable).
La transaction atomique de la commande est alors annulée : rien n'est
débité, rien n'est enregistré en caisse.
/ On failure, raises EnvoiBilletErreur with a readable message: the
caller refuses the sale and the atomic transaction rolls back.
"""
import logging

import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class EnvoiBilletErreur(Exception):
    """
    Erreur d'envoi du billet vers Lespass.
    / Ticket creation error on the Lespass side.
    """
    pass


def envoyer_reservation_billet(article, qty, email, payment_method, config):
    """
    Crée la réservation côté Lespass pour un billet vendu en caisse.
    / Creates the reservation on Lespass for a ticket sold at the POS.

    :param article: Articles (LaBoutik) — son pk est l'uuid du tarif Lespass
    :param qty: quantité de billets vendus (int)
    :param email: email du client (carte NFC) ou de la caisse (anonyme)
    :param payment_method: "cash" ou "card" (vocabulaire API v2 Lespass)
    :param config: Configuration (LaBoutik)
    :return: dict JSON de la réservation créée (schema.org/Reservation)
    :raises EnvoiBilletErreur: si Lespass refuse ou est injoignable
    """
    if not config.lespass_api_key:
        raise EnvoiBilletErreur(_("Billetterie : clé API Lespass non configurée."))
    if not config.billetterie_url:
        raise EnvoiBilletErreur(_("Billetterie : adresse Lespass non configurée."))

    # Le payload suit le vocabulaire schema.org de l'API v2 Lespass.
    # Pas de reservationFor : Lespass déduit l'évènement depuis le tarif.
    # / schema.org payload; no reservationFor: Lespass resolves the event.
    payload = {
        "@context": "https://schema.org",
        "@type": "Reservation",
        "underName": {"@type": "Person", "email": email},
        "reservedTicket": [
            {
                "@type": "Ticket",
                "identifier": str(article.pk),
                "ticketQuantity": int(qty),
            }
        ],
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "paymentMethod", "value": payment_method},
        ],
    }

    try:
        # Timeout obligatoire (connexion 3s, lecture 5s) : la caisse ne doit
        # jamais rester bloquée si Lespass est lent.
        # / Mandatory timeout: the POS must never hang on a slow Lespass.
        reponse = requests.post(
            f"{config.billetterie_url}api/v2/reservations/",
            json=payload,
            headers={"Authorization": f"Api-Key {config.lespass_api_key}"},
            timeout=(3, 5),
            verify=bool(not settings.DEBUG),
        )
    except requests.RequestException as e:
        logger.error(f"envoyer_reservation_billet : Lespass injoignable : {e}")
        raise EnvoiBilletErreur(
            _("Billetterie injoignable. Vente annulée, rien n'a été débité."))

    if reponse.status_code != 201:
        # Lespass renvoie un détail JSON lisible (ex : évènement introuvable,
        # jauge atteinte, plusieurs évènements possibles...).
        # / Lespass returns a readable JSON detail (event not found, sold out...).
        logger.error(
            f"envoyer_reservation_billet : statut {reponse.status_code} : {reponse.text[:500]}")
        raise EnvoiBilletErreur(
            _("Billetterie : vente refusée par Lespass : ") + reponse.text[:200])

    try:
        reservation = reponse.json()
    except ValueError as e:
        logger.error(f"envoyer_reservation_billet : réponse non-JSON : {e}")
        raise EnvoiBilletErreur(_("Billetterie : réponse illisible de Lespass."))

    logger.info(
        f"envoyer_reservation_billet : réservation {reservation.get('identifier')} créée sur Lespass")
    return reservation
