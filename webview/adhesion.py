"""
Statut d'adhesion au paiement NFC : couleur du popup + recuperation Lespass.
/ Membership status on NFC payment: popup color + fetch from Lespass.

LOCALISATION : webview/adhesion.py

Utilise par webview/views.py (classe Commande) au moment d'un paiement NFC reussi,
si l'option Configuration.verifier_adhesion_paiement_nfc est activee.

FLUX :
1. Commande a le wallet_uuid Fedow de la carte qui paie.
2. fetch_adhesions() interroge Lespass (cache 24h, timeout court) -> liste d'adhesions.
3. couleur_adhesion() en deduit la couleur de fond du popup de validation.
"""
import logging
import uuid

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Couleurs du fond du popup selon le statut d'adhesion (palette existante).
# / Popup background colors by membership status.
COULEUR_VALIDE = '#339448'    # vert  : au moins une adhesion valide
COULEUR_EXPIREE = '#b85521'   # orange: adhesions presentes mais toutes expirees
COULEUR_AUCUNE = '#1a1e25'    # neutre: aucune adhesion (paiement OK)

# On NE cache QUE les reponses contenant au moins une adhesion VALIDE (etat stable
# pour un moment). Les reponses "aucune valide" (liste vide OU adhesions toutes
# expirees) ne sont PAS cachees : un renouvellement ou une nouvelle adhesion doit
# etre visible des le prochain scan, sans attendre l'expiration d'un cache.
# Pourquoi : 'is_valid' est un booleen TEMPOREL. Cacher un False fige un faux
# "non valide" apres un renouvellement (incident terrain #413 : adhesion remise a
# jour mais POS affiche "non valide" jusqu'au lendemain a cause du cache 24h).
# / Only responses with at least one VALID membership are cached (stable for a while).
#   "None valid" responses (empty OR all expired) are NOT cached, so a renewal or a new
#   membership shows up on the next scan. is_valid is a TEMPORAL boolean; caching a
#   False froze a stale "not valid" after a renewal (field incident #413).
CACHE_ADHESIONS_VALIDE = 60 * 60 * 24    # 24h : au moins une adhesion valide


def couleur_adhesion(adhesions):
    """
    Renvoie la couleur de fond du popup selon la liste d'adhesions de Lespass.
    / Returns the popup background color from the memberships list.

    adhesions : liste de dict {"is_valid": bool, ...}.
                None => indisponible (Lespass injoignable) => None (le front
                garde alors sa couleur de succes habituelle).
    """
    if adhesions is None:
        return None
    if any(adhesion.get('is_valid') for adhesion in adhesions):
        return COULEUR_VALIDE
    if len(adhesions) > 0:
        return COULEUR_EXPIREE
    return COULEUR_AUCUNE


def fetch_adhesions(wallet_uuid, config):
    """
    Recupere les adhesions d'un wallet aupres de Lespass (cache 24h).
    / Fetches a wallet's memberships from Lespass (24h cache).

    Renvoie une liste de dict, ou None si indisponible (pas de cle, timeout,
    erreur HTTP, Lespass injoignable). None => couleur neutre cote front,
    le paiement n'est jamais bloque.
    """
    if not config.lespass_api_key:
        return None

    cache_key = f"adhesion:{wallet_uuid}"
    en_cache = cache.get(cache_key)
    if en_cache is not None:
        return en_cache

    try:
        # On garde le "/api/..." apres billetterie_url (qui finit deja par "/")
        # pour rester identique au pattern existant (signals.py).
        # / Same URL pattern as the existing products call.
        reponse = requests.get(
            f"{config.billetterie_url}/api/v2/memberships/by-wallet/",
            params={"wallet_uuid": str(wallet_uuid)},
            headers={"Authorization": f"Api-Key {config.lespass_api_key}"},
            timeout=1.5,
            verify=bool(not settings.DEBUG),
        )
        if reponse.status_code != 200:
            logger.warning(f"fetch_adhesions : status {reponse.status_code}")
            return None
        # reponse.json() peut lever ValueError si Lespass renvoie un 200 avec un
        # corps non-JSON (page d'erreur d'un proxy, reponse tronquee). On degrade
        # alors en None : Fedow a deja valide le paiement, on ne le bloque jamais.
        # / .json() may raise ValueError on a non-JSON 200 body; degrade to None so
        #   the payment (already accepted by Fedow) is never blocked.
        adhesions = reponse.json().get('memberships', [])
    except requests.RequestException as e:
        logger.warning(f"fetch_adhesions : Lespass injoignable : {e}")
        return None
    except ValueError as e:
        logger.warning(f"fetch_adhesions : reponse non-JSON de Lespass : {e}")
        return None

    # On ne cache QUE s'il y a au moins une adhesion VALIDE (etat stable). Sinon
    # (aucune valide : liste vide ou toutes expirees), on ne cache PAS : un
    # renouvellement / une nouvelle adhesion est visible des le prochain scan.
    # / Cache only if at least one VALID membership (stable). Otherwise (none valid)
    #   we don't cache, so a renewal / new membership shows up on the next scan.
    au_moins_une_valide = any(adhesion.get('is_valid') for adhesion in adhesions)
    if au_moins_une_valide:
        cache.set(cache_key, adhesions, CACHE_ADHESIONS_VALIDE)
    return adhesions


def tester_connexion_lespass(config):
    """
    Teste la connexion a Lespass avec la cle configuree.
    / Tests the connection to Lespass with the configured key.

    Utilise par l'admin quand on active la verification d'adhesion : on n'active
    la case que si cet appel repond 200. On envoie un wallet_uuid bidon : un
    wallet inconnu renvoie 200 + liste vide, ce qui valide la chaine
    cle + IP + permission `membership` sans dependre d'aucune donnee.
    / Used by the admin when enabling the membership check: only keep the box
      ticked if this call returns 200. A random wallet_uuid (unknown wallet)
      returns 200 + empty list, which validates key + IP + permission.

    Renvoie (succes: bool, message: str).
    """
    if not config.lespass_api_key:
        return False, "aucune clé API Lespass renseignée."
    if not config.billetterie_url:
        return False, "aucune URL de billetterie (Lespass) configurée."

    wallet_test = uuid.uuid4()  # wallet bidon : un wallet inconnu renvoie 200 + liste vide
    try:
        reponse = requests.get(
            f"{config.billetterie_url}/api/v2/memberships/by-wallet/",
            params={"wallet_uuid": str(wallet_test)},
            headers={"Authorization": f"Api-Key {config.lespass_api_key}"},
            timeout=3,
            verify=bool(not settings.DEBUG),
        )
    except requests.RequestException as e:
        return False, f"Lespass injoignable ({e})."

    if reponse.status_code == 200:
        return True, "connexion OK."
    if reponse.status_code in (401, 403):
        return False, "refusé par Lespass (clé invalide ou IP non autorisée)."
    return False, f"réponse inattendue de Lespass (status {reponse.status_code})."
