"""
Tests unitaires des fonctions d'adhesion (couleur + recuperation Lespass).
/ Unit tests for the membership helpers (color + fetch from Lespass).

LOCALISATION : webview/tests_adhesion.py
Lancer : docker exec laboutik_django poetry run python manage.py test webview.tests_adhesion -v 2

SimpleTestCase : ces fonctions ne touchent pas la base. / No DB access here.
"""
from unittest.mock import patch, MagicMock

import requests
from django.test import SimpleTestCase, override_settings
from django.core.cache import cache

from webview.adhesion import (
    couleur_adhesion,
    fetch_adhesions,
    tester_connexion_lespass,
    COULEUR_VALIDE,
    COULEUR_EXPIREE,
    COULEUR_AUCUNE,
    CACHE_ADHESIONS_VALIDE,
)


class CouleurAdhesionTest(SimpleTestCase):
    def test_au_moins_une_valide_donne_vert(self):
        # Au moins une adhesion valide -> vert / At least one valid -> green
        adhesions = [{"is_valid": False}, {"is_valid": True}]
        self.assertEqual(couleur_adhesion(adhesions), COULEUR_VALIDE)

    def test_toutes_expirees_donne_orange(self):
        # Des adhesions, mais toutes expirees -> orange / All expired -> orange
        adhesions = [{"is_valid": False}, {"is_valid": False}]
        self.assertEqual(couleur_adhesion(adhesions), COULEUR_EXPIREE)

    def test_aucune_adhesion_donne_neutre(self):
        # Liste vide -> neutre / Empty list -> neutral
        self.assertEqual(couleur_adhesion([]), COULEUR_AUCUNE)

    def test_none_donne_none(self):
        # Lespass injoignable -> None / Lespass unreachable -> None
        self.assertIsNone(couleur_adhesion(None))


# Cache local isole pour ne pas toucher au memcached partage.
# / Isolated local cache so we don't touch the shared memcached.
@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class FetchAdhesionsTest(SimpleTestCase):
    class FakeConfig:
        billetterie_url = "https://lespass.example/"
        lespass_api_key = "AB.cle"

    def setUp(self):
        cache.clear()

    def test_pas_de_cle_renvoie_none(self):
        # Sans cle configuree, pas d'appel : None / No key -> None
        cfg = self.FakeConfig()
        cfg.lespass_api_key = None
        self.assertIsNone(fetch_adhesions("w-uuid", cfg))

    @patch("webview.adhesion.requests.get")
    def test_succes_renvoie_liste_et_met_en_cache(self, mock_get):
        # Succes : renvoie la liste et la met en cache (pas de 2e appel)
        # / Success: returns list and caches it (no 2nd call)
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"memberships": [{"is_valid": True}]},
        )
        result = fetch_adhesions("w-uuid", self.FakeConfig())
        self.assertEqual(result, [{"is_valid": True}])

        fetch_adhesions("w-uuid", self.FakeConfig())  # 2e appel -> cache
        self.assertEqual(mock_get.call_count, 1)

    @patch("webview.adhesion.requests.get", side_effect=requests.RequestException("down"))
    def test_lespass_injoignable_renvoie_none(self, mock_get):
        # Lespass injoignable -> None (paiement jamais bloque)
        # / Lespass unreachable -> None (payment never blocked)
        self.assertIsNone(fetch_adhesions("w-uuid-2", self.FakeConfig()))

    @patch("webview.adhesion.requests.get")
    def test_status_non_200_renvoie_none(self, mock_get):
        # 403 (mauvaise cle / IP) -> None / 403 -> None
        mock_get.return_value = MagicMock(status_code=403, json=lambda: {})
        self.assertIsNone(fetch_adhesions("w-uuid-3", self.FakeConfig()))

    @patch("webview.adhesion.requests.get")
    def test_reponse_200_non_json_renvoie_none(self, mock_get):
        # 200 mais corps non-JSON (proxy / page HTML) : .json() leve ValueError
        # -> on degrade en None, la vente n'est jamais bloquee.
        # / 200 with non-JSON body: .json() raises ValueError -> None.
        mock_response = MagicMock(status_code=200)
        mock_response.json.side_effect = ValueError("No JSON could be decoded")
        mock_get.return_value = mock_response
        self.assertIsNone(fetch_adhesions("w-uuid-4", self.FakeConfig()))

    @patch("webview.adhesion.cache")
    @patch("webview.adhesion.requests.get")
    def test_au_moins_une_valide_cache_longtemps(self, mock_get, mock_cache):
        # Au moins une adhesion valide -> etat stable -> cache long (24h).
        # / At least one valid membership -> stable -> long cache (24h).
        mock_cache.get.return_value = None
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"memberships": [{"is_valid": True}]},
        )
        fetch_adhesions("w-valide", self.FakeConfig())
        mock_cache.set.assert_called_once_with(
            "adhesion:w-valide", [{"is_valid": True}], CACHE_ADHESIONS_VALIDE,
        )

    @patch("webview.adhesion.cache")
    @patch("webview.adhesion.requests.get")
    def test_liste_vide_pas_de_cache(self, mock_get, mock_cache):
        # Une liste vide n'est PAS cachee : une nouvelle adhesion apparait des le
        # prochain scan (pas de faux negatif fige).
        # / An empty list is NOT cached: a new membership shows up on the next scan.
        mock_cache.get.return_value = None
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"memberships": []},
        )
        result = fetch_adhesions("w-vide", self.FakeConfig())
        self.assertEqual(result, [])
        mock_cache.set.assert_not_called()

    @patch("webview.adhesion.cache")
    @patch("webview.adhesion.requests.get")
    def test_adhesions_toutes_expirees_pas_de_cache(self, mock_get, mock_cache):
        # Incident terrain #413 : une adhesion EXPIREE (liste non vide, aucune valide)
        # ne doit PAS etre cachee, sinon un renouvellement reste fige "non valide"
        # (POS affichait "non valide" jusqu'au lendemain). On ne cache pas -> le
        # renouvellement est visible des le prochain scan.
        # / Field incident #413: an EXPIRED membership must NOT be cached, otherwise a
        #   renewal stays frozen "not valid". Not cached -> visible on the next scan.
        mock_cache.get.return_value = None
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"memberships": [{"is_valid": False}]},
        )
        result = fetch_adhesions("w-expiree", self.FakeConfig())
        self.assertEqual(result, [{"is_valid": False}])
        mock_cache.set.assert_not_called()


class TesterConnexionLespassTest(SimpleTestCase):
    """
    Test du test de connexion Lespass utilise par l'admin a l'activation.
    / Tests the Lespass connection check used by the admin on enable.
    """
    class FakeConfig:
        billetterie_url = "https://lespass.example/"
        lespass_api_key = "AB.cle"

    def test_pas_de_cle_echoue(self):
        # Sans cle : echec, pas d'appel reseau. / No key: failure, no network call.
        cfg = self.FakeConfig()
        cfg.lespass_api_key = None
        succes, message = tester_connexion_lespass(cfg)
        self.assertFalse(succes)

    @patch("webview.adhesion.requests.get")
    def test_status_200_reussit(self, mock_get):
        # 200 : cle + IP + permission valides -> succes. / 200 -> success.
        mock_get.return_value = MagicMock(status_code=200)
        succes, message = tester_connexion_lespass(self.FakeConfig())
        self.assertTrue(succes)

    @patch("webview.adhesion.requests.get")
    def test_status_403_echoue(self, mock_get):
        # 403 : cle invalide ou IP non autorisee -> echec. / 403 -> failure.
        mock_get.return_value = MagicMock(status_code=403)
        succes, message = tester_connexion_lespass(self.FakeConfig())
        self.assertFalse(succes)

    @patch("webview.adhesion.requests.get", side_effect=requests.RequestException("down"))
    def test_lespass_injoignable_echoue(self, mock_get):
        # Lespass injoignable -> echec (on ne coche pas la case).
        # / Lespass unreachable -> failure (box stays unticked).
        succes, message = tester_connexion_lespass(self.FakeConfig())
        self.assertFalse(succes)
