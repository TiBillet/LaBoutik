# Couleur d'adhésion sur le message de validation de paiement NFC — Plan d'implémentation

> **Pour les workers agentiques :** SOUS-SKILL REQUIS — utiliser `superpowers:subagent-driven-development` (recommandé) ou `superpowers:executing-plans`. Les étapes utilisent des cases à cocher (`- [ ]`).

> **⚠️ RÈGLE GIT — À LIRE AVANT TOUT.** NE JAMAIS lancer de commande git : pas de `commit`, `push`, `add`, `checkout --`, `stash`, `reset --hard`, `restore --`, `clean -f`. Le mainteneur committe lui-même. Les étapes « Point de commit » ne font qu'**afficher le message suggéré** — ne pas l'exécuter. **JAMAIS de `Co-Authored-By` dans les messages.**

**Goal :** Colorer le fond du popup de validation de paiement NFC (LaBoutik) selon le statut d'adhésion (valide/expirée/aucune) du porteur, et lister ses adhésions.

**Architecture :** Lespass expose une lecture `GET /api/v2/memberships/by-wallet/?wallet_uuid=` (auth + IP via `SemanticApiKeyPermission`/`ExternalApiKey` existants). LaBoutik appelle cet endpoint au paiement NFC réussi (avec un cache 24h et un timeout), calcule une couleur, et l'injecte dans le popup. Si Lespass est injoignable → couleur neutre, le paiement n'est jamais bloqué.

**Tech Stack :** Django + DRF (Lespass api_v2, multi-tenant django-tenants ; LaBoutik single-tenant), memcached (cache LaBoutik), JS vanilla (popup POS).

**Spec :** `TECH_DOC/SESSIONS/couleur-adhesion-paiement-nfc/spec.md`

**Conteneurs / tests :**
- Lespass : `lespass_django` (actif) — `docker exec lespass_django poetry run pytest <path> -q`
- LaBoutik : `laboutik_django` (**à démarrer** : `docker compose up -d` dans `/home/jonas/TiBillet/dev/LaBoutik`) — `docker exec laboutik_django poetry run python manage.py test <module>`

---

## Découpage fichiers

**Lespass**
- `api_v2/serializers.py` — + `MembershipStatusSerializer` (4 champs).
- `api_v2/views.py` — `MembershipViewSet` : + action `by_wallet`.
- `tests/pytest/test_membership_by_wallet.py` (créé) — test DB-only.

**LaBoutik**
- `APIcashless/models.py` — `Configuration` : + 2 champs (+ migration).
- `webview/adhesion.py` (créé) — `couleur_adhesion()` + `fetch_adhesions()`.
- `webview/tests_adhesion.py` (créé) — tests unitaires des 2 fonctions.
- `webview/views.py` — `Commande` : injection dans `self.reponse`.
- `webview/static/webview/js/modules/fonctions.js` — `popup()` : couleur optionnelle.
- `webview/static/webview/js/RetourPosts.js` — couleur + liste dans le popup NFC.
- `administration/adminstaff.py` — exposer les 2 champs config.

---

## Task 1 (Lespass) : endpoint `by-wallet` + serializer + tests

**Files:**
- Modify: `api_v2/serializers.py`
- Modify: `api_v2/views.py` (`MembershipViewSet`, ~ligne 336)
- Test: `tests/pytest/test_membership_by_wallet.py` (créer)

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/pytest/test_membership_by_wallet.py` :

```python
"""
Test DB-only - API v2 : lecture des adhesions par wallet_uuid.
/ DB-only test - API v2: read memberships by wallet_uuid.

Run: docker exec lespass_django poetry run pytest tests/pytest/test_membership_by_wallet.py -q
"""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient

HOST = "lespass.tibillet.localhost"


@pytest.fixture
def wallet_setup(db):
    from Customers.models import Client
    from AuthBillet.models import Wallet, TibilletUser
    from BaseBillet.models import ExternalApiKey, Product, Price, Membership
    from rest_framework_api_key.models import APIKey

    tenant = Client.objects.get(schema_name="lespass")
    suffix = uuid.uuid4().hex[:6]

    with tenant_context(tenant):
        wallet = Wallet.objects.create(origin=tenant)
        user = TibilletUser.objects.create(
            email=f"adh-{suffix}@example.org", wallet=wallet,
        )
        product = Product.objects.create(name=f"Adhesion {suffix}", categorie_article=Product.ADHESION)
        price = Price.objects.create(product=product, name="Normal", prix=10, subscription_type=Price.YEAR)
        membership = Membership.objects.create(
            user=user, price=price,
            last_contribution=timezone.localtime(),
            deadline=timezone.localtime() + timedelta(days=30),  # valide
        )

        api_obj, key_str = APIKey.objects.create_key(name=f"laboutik-{suffix}")
        ext_key = ExternalApiKey.objects.create(name=f"laboutik-{suffix}", key=api_obj, membership=True)

    data = {"tenant": tenant, "wallet": wallet, "key": key_str}
    yield data

    with tenant_context(tenant):
        membership.delete(); price.delete(); product.delete()
        user.delete(); wallet.delete()
        ext_key.delete(); api_obj.delete()


def _get(wallet_uuid, key=None):
    client = APIClient()
    extra = {"SERVER_NAME": HOST}
    if key:
        extra["HTTP_AUTHORIZATION"] = f"Api-Key {key}"
    return client.get(f"/api/v2/memberships/by-wallet/?wallet_uuid={wallet_uuid}", **extra)


def test_by_wallet_sans_cle_est_refuse(wallet_setup):
    resp = _get(wallet_setup["wallet"].uuid)
    assert resp.status_code == 403


def test_by_wallet_wallet_inconnu_renvoie_liste_vide(wallet_setup):
    resp = _get(uuid.uuid4(), key=wallet_setup["key"])
    assert resp.status_code == 200
    assert resp.json()["memberships"] == []


def test_by_wallet_adhesion_valide(wallet_setup):
    resp = _get(wallet_setup["wallet"].uuid, key=wallet_setup["key"])
    assert resp.status_code == 200
    memberships = resp.json()["memberships"]
    assert len(memberships) == 1
    assert memberships[0]["is_valid"] is True
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

Run : `docker exec lespass_django poetry run pytest tests/pytest/test_membership_by_wallet.py -q`
Attendu : ÉCHEC (404 sur la route `by-wallet` qui n'existe pas encore).

- [ ] **Step 3 : Ajouter le serializer**

Dans `api_v2/serializers.py`, ajouter :

```python
class MembershipStatusSerializer(serializers.Serializer):
    """
    Sortie minimale du statut d'adhesion pour LaBoutik.
    / Minimal membership status output for LaBoutik.
    """
    product_name = serializers.SerializerMethodField()
    price_name = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    deadline = serializers.DateTimeField()

    def get_product_name(self, obj):
        return obj.price.product.name if obj.price and obj.price.product else None

    def get_price_name(self, obj):
        return obj.price.name if obj.price else None

    def get_is_valid(self, obj):
        return obj.is_valid()
```

- [ ] **Step 4 : Ajouter l'action sur `MembershipViewSet`**

Dans `api_v2/views.py`, en haut, s'assurer des imports :
```python
from AuthBillet.models import TibilletUser
from BaseBillet.models import Membership
from api_v2.serializers import MembershipStatusSerializer
from rest_framework.decorators import action
```

Dans `class MembershipViewSet`, ajouter la méthode :
```python
    @action(detail=False, methods=["get"], url_path="by-wallet")
    def by_wallet(self, request):
        """
        Liste les adhesions d'un porteur a partir de son wallet Fedow.
        / Lists a holder's memberships from their Fedow wallet uuid.
        Auth + IP + permission `membership` geres par SemanticApiKeyPermission.
        """
        wallet_uuid = request.query_params.get("wallet_uuid")
        if not wallet_uuid:
            return Response({"detail": "wallet_uuid is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = TibilletUser.objects.filter(wallet__uuid=wallet_uuid).first()
        memberships = user.memberships.all() if user else Membership.objects.none()
        serializer = MembershipStatusSerializer(memberships, many=True)
        return Response(
            {"wallet_uuid": wallet_uuid, "memberships": serializer.data},
            status=status.HTTP_200_OK,
        )
```

- [ ] **Step 5 : Lancer les tests, vérifier qu'ils passent**

Run : `docker exec lespass_django poetry run pytest tests/pytest/test_membership_by_wallet.py -q`
Attendu : 3 PASS. (Si `Product.ADHESION` / `Price.YEAR` ont d'autres noms, ajuster le test d'après `BaseBillet/models.py`.)

- [ ] **Step 6 : Point de commit** (le mainteneur committe — NE PAS lancer git)

Message suggéré : `feat(api_v2): lecture des adhesions par wallet_uuid (by-wallet)`

---

## Task 2 (LaBoutik) : champs config + admin

**Files:**
- Modify: `APIcashless/models.py` (`Configuration`)
- Modify: `administration/adminstaff.py`
- Create (auto): `APIcashless/migrations/0XXX_*.py`

- [ ] **Step 1 : Ajouter les 2 champs sur `Configuration`**

Dans `APIcashless/models.py`, classe `Configuration`, près des autres champs `billetterie_*` (~ligne 2145) :

```python
    # Clé API ExternalApiKey (Lespass) pour lire les adhesions au paiement NFC.
    # Collee a la main par l'admin (cf. spec). / Lespass key to read memberships.
    lespass_api_key = models.CharField(max_length=100, blank=True, null=True,
                                       verbose_name=_("Clé API Lespass (adhésions)"))

    # Active la verification d'adhesion + couleur a chaque paiement NFC.
    # / Enables membership check + color on each NFC payment.
    verifier_adhesion_paiement_nfc = models.BooleanField(default=False,
                                       verbose_name=_("Vérifier l'adhésion à chaque paiement NFC"))
```

- [ ] **Step 2 : Générer et appliquer la migration**

Run :
```
docker exec laboutik_django poetry run python manage.py makemigrations APIcashless
docker exec laboutik_django poetry run python manage.py migrate APIcashless
```
Attendu : nouvelle migration créée + appliquée sans erreur.

- [ ] **Step 3 : Exposer les champs en admin**

Dans `administration/adminstaff.py`, repérer l'admin de `Configuration` (chercher `class ConfigurationAdmin` ou `fieldsets`/`fields` listant `billetterie_url`). Ajouter `lespass_api_key` et `verifier_adhesion_paiement_nfc` à la même section que `billetterie_url`. (Si l'admin utilise `fields`/`fieldsets` explicites, les y ajouter ; sinon vérifier qu'ils apparaissent.)

- [ ] **Step 4 : Vérifier l'admin**

Démarrer si besoin, puis ouvrir l'admin LaBoutik → Configuration → vérifier que les 2 champs sont éditables. (Vérif manuelle.)

- [ ] **Step 5 : Point de commit** (mainteneur — NE PAS lancer git)

Message suggéré : `feat(config): champs lespass_api_key + verifier_adhesion_paiement_nfc`

---

## Task 3 (LaBoutik) : fonction couleur (pure, TDD)

**Files:**
- Create: `webview/adhesion.py`
- Test: `webview/tests_adhesion.py` (créer)

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `webview/tests_adhesion.py` :

```python
from django.test import TestCase
from webview.adhesion import couleur_adhesion, COULEUR_VALIDE, COULEUR_EXPIREE, COULEUR_AUCUNE


class CouleurAdhesionTest(TestCase):
    def test_au_moins_une_valide_donne_vert(self):
        adhesions = [{"is_valid": False}, {"is_valid": True}]
        self.assertEqual(couleur_adhesion(adhesions), COULEUR_VALIDE)

    def test_toutes_expirees_donne_orange(self):
        adhesions = [{"is_valid": False}, {"is_valid": False}]
        self.assertEqual(couleur_adhesion(adhesions), COULEUR_EXPIREE)

    def test_aucune_adhesion_donne_neutre(self):
        self.assertEqual(couleur_adhesion([]), COULEUR_AUCUNE)

    def test_none_donne_none(self):
        # Lespass injoignable : le front garde sa couleur succes
        self.assertIsNone(couleur_adhesion(None))
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

Run : `docker exec laboutik_django poetry run python manage.py test webview.tests_adhesion -v 2`
Attendu : ÉCHEC (ImportError : `webview.adhesion` n'existe pas).

- [ ] **Step 3 : Écrire la fonction couleur**

Créer `webview/adhesion.py` :

```python
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Couleurs du fond du popup selon le statut d'adhesion (palette existante).
# / Popup background colors by membership status.
COULEUR_VALIDE = '#339448'    # vert  : au moins une adhesion valide
COULEUR_EXPIREE = '#b85521'   # orange: adhesions presentes mais toutes expirees
COULEUR_AUCUNE = '#1a1e25'    # neutre: aucune adhesion (paiement OK)


def couleur_adhesion(adhesions):
    """
    Renvoie la couleur de fond selon la liste d'adhesions recue de Lespass.
    / Returns the popup background color from the memberships list.

    adhesions : liste de dict {"is_valid": bool, ...}.
                None => indisponible (Lespass injoignable) => None (le front
                garde sa couleur de succes).
    """
    if adhesions is None:
        return None
    if any(adhesion.get('is_valid') for adhesion in adhesions):
        return COULEUR_VALIDE
    if len(adhesions) > 0:
        return COULEUR_EXPIREE
    return COULEUR_AUCUNE
```

- [ ] **Step 4 : Lancer le test, vérifier qu'il passe**

Run : `docker exec laboutik_django poetry run python manage.py test webview.tests_adhesion -v 2`
Attendu : 4 PASS.

- [ ] **Step 5 : Point de commit** (mainteneur — NE PAS lancer git)

Message suggéré : `feat(adhesion): fonction couleur_adhesion (vert/orange/neutre)`

---

## Task 4 (LaBoutik) : récupération + cache 24h (TDD mock)

**Files:**
- Modify: `webview/adhesion.py`
- Test: `webview/tests_adhesion.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à `webview/tests_adhesion.py` :

```python
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from webview.adhesion import fetch_adhesions


class FakeConfig:
    billetterie_url = "https://lespass.example/"
    lespass_api_key = "AB.cle"


class FetchAdhesionsTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_pas_de_cle_renvoie_none(self):
        cfg = FakeConfig(); cfg.lespass_api_key = None
        self.assertIsNone(fetch_adhesions("w-uuid", cfg))

    @patch("webview.adhesion.requests.get")
    def test_succes_renvoie_liste_et_met_en_cache(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200,
            json=lambda: {"memberships": [{"is_valid": True}]})
        result = fetch_adhesions("w-uuid", FakeConfig())
        self.assertEqual(result, [{"is_valid": True}])
        # 2e appel : cache, requests.get pas rappele
        fetch_adhesions("w-uuid", FakeConfig())
        self.assertEqual(mock_get.call_count, 1)

    @patch("webview.adhesion.requests.get", side_effect=__import__("requests").RequestException("down"))
    def test_lespass_injoignable_renvoie_none(self, mock_get):
        self.assertIsNone(fetch_adhesions("w-uuid-2", FakeConfig()))
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `docker exec laboutik_django poetry run python manage.py test webview.tests_adhesion.FetchAdhesionsTest -v 2`
Attendu : ÉCHEC (ImportError : `fetch_adhesions` n'existe pas).

- [ ] **Step 3 : Écrire `fetch_adhesions`**

Ajouter à `webview/adhesion.py` :

```python
def fetch_adhesions(wallet_uuid, config):
    """
    Recupere les adhesions d'un wallet aupres de Lespass (cache 24h).
    / Fetches a wallet's memberships from Lespass (24h cache).

    Renvoie une liste de dict, ou None si indisponible (pas de cle, timeout,
    erreur, Lespass injoignable). None => couleur neutre cote front.
    """
    if not config.lespass_api_key:
        return None

    cache_key = f"adhesion:{wallet_uuid}"
    en_cache = cache.get(cache_key)
    if en_cache is not None:
        return en_cache

    try:
        reponse = requests.get(
            f"{config.billetterie_url}/api/v2/memberships/by-wallet/",
            params={"wallet_uuid": str(wallet_uuid)},
            headers={"Authorization": f"Api-Key {config.lespass_api_key}"},
            timeout=1.5,
            verify=bool(not settings.DEBUG),
        )
    except requests.RequestException as e:
        logger.warning(f"fetch_adhesions : Lespass injoignable : {e}")
        return None

    if reponse.status_code != 200:
        logger.warning(f"fetch_adhesions : status {reponse.status_code}")
        return None

    adhesions = reponse.json().get('memberships', [])
    cache.set(cache_key, adhesions, 60 * 60 * 24)  # 24h
    return adhesions
```

> Note : on garde le `/api/...` après `billetterie_url` (qui finit déjà par `/`) pour rester identique au pattern existant `signals.py:164` (le double `//` est toléré).

- [ ] **Step 4 : Lancer, vérifier le succès**

Run : `docker exec laboutik_django poetry run python manage.py test webview.tests_adhesion -v 2`
Attendu : tous les tests (Task 3 + 4) PASS.

- [ ] **Step 5 : Point de commit** (mainteneur — NE PAS lancer git)

Message suggéré : `feat(adhesion): fetch_adhesions vers Lespass avec cache 24h et timeout`

---

## Task 5 (LaBoutik) : injection dans la réponse de paiement NFC

**Files:**
- Modify: `webview/views.py` (classe `Commande`)

- [ ] **Step 1 : Importer les fonctions**

En haut de `webview/views.py`, ajouter :
```python
from webview.adhesion import fetch_adhesions, couleur_adhesion
```

- [ ] **Step 2 : Injecter dans `self.reponse` au succès NFC**

Dans `Commande.validation()`, repérer la branche qui construit la réponse d'un
paiement NFC réussi (anchor : la ligne qui fait `self.reponse['route'] = "transaction_nfc"`).
**Juste après** cette ligne, ajouter :

```python
        # Couleur + liste d'adhesions (si l'option est activee en config).
        # / Membership color + list (if enabled in config).
        if self.configuration.verifier_adhesion_paiement_nfc:
            wallet_uuid = self.carte_db.get_wallet().uuid
            adhesions = fetch_adhesions(wallet_uuid, self.configuration)
            self.reponse['adhesions'] = adhesions or []
            self.reponse['adhesion_couleur'] = couleur_adhesion(adhesions)
```

> `self.configuration` = `Configuration.get_solo()` (déjà chargé dans `__init__`, ligne 592). `self.carte_db` = la carte qui paie.

- [ ] **Step 3 : Vérifier qu'aucune régression d'import**

Run : `docker exec laboutik_django poetry run python manage.py check`
Attendu : `System check identified no issues`.

- [ ] **Step 4 : Point de commit** (mainteneur — NE PAS lancer git)

Message suggéré : `feat(paiement): expose adhesions + couleur dans la reponse NFC`

---

## Task 6 (LaBoutik, front) : popup couleur + liste — vérif manuelle

**Files:**
- Modify: `webview/static/webview/js/modules/fonctions.js` (`popup`, ~ligne 119)
- Modify: `webview/static/webview/js/RetourPosts.js` (`afficherRetourVenteDirecte`)

- [ ] **Step 1 : `popup()` accepte une couleur explicite**

Dans `modules/fonctions.js`, fonction `popup(options)`, remplacer la ligne 135 :
```js
  style_fond = 'background-color:' + type_message[options.type].coul_fond + ';'
```
par :
```js
  // Couleur explicite (ex: statut d'adhesion) prioritaire sur le type.
  // / Explicit color (e.g. membership status) overrides the type color.
  let coul_fond = type_message[options.type].coul_fond
  if (options.couleur) {
    coul_fond = options.couleur
  }
  style_fond = 'background-color:' + coul_fond + ';'
```

- [ ] **Step 2 : `RetourPosts.js` passe la couleur + affiche la liste**

Dans `afficherRetourVenteDirecte`, juste avant l'appel `fn.popup({ message: msg, type: typeMsg })` de la branche NFC réussie (~ligne 686), construire la liste et passer la couleur :
```js
  // Liste des adhesions du porteur (si fournie par le serveur).
  // / Holder's memberships list (if provided by the server).
  let adhesionsHtml = ''
  if (retour.adhesions && retour.adhesions.length > 0) {
    adhesionsHtml = '<div class="popup-adhesions" style="margin-top:1rem;">'
    for (const adh of retour.adhesions) {
      const etat = adh.is_valid ? '✅' : '⛔'
      adhesionsHtml += `<div class="popup-adhesion-row">${etat} ${adh.product_name || ''}</div>`
    }
    adhesionsHtml += '</div>'
  }
```
puis remplacer l'appel par :
```js
  fn.popup({ message: msg + adhesionsHtml, type: typeMsg, couleur: retour.adhesion_couleur })
```
> `retour.adhesion_couleur` vaut `null` si Lespass est injoignable → `fn.popup` garde alors la couleur du `type` (succès). Comportement inchangé si l'option config est désactivée (le serveur n'envoie pas `adhesions`).

- [ ] **Step 3 : Vérification manuelle navigateur**

Démarrer le POS, faire un paiement NFC réussi avec une carte de test, vérifier
visuellement la couleur de fond + la liste. (Pas de test JS automatisé dans ce repo.)

- [ ] **Step 4 : Point de commit** (mainteneur — NE PAS lancer git)

Message suggéré : `feat(pos): couleur d'adhesion + liste sur le popup de paiement NFC`

---

## Task 7 : setup admin + recette end-to-end (manuel)

- [ ] **Step 1 : Provisionner la clé (Lespass)**

Admin Lespass → créer un `ExternalApiKey` : `membership=True`, `ip = <IP publique du serveur LaBoutik>`. Copier la clé générée.

- [ ] **Step 2 : Configurer LaBoutik**

Admin LaBoutik → `Configuration` → coller la clé dans `lespass_api_key`, activer `verifier_adhesion_paiement_nfc`.

- [ ] **Step 3 : Recette (POS réel)**

Vérifier les 4 cas :
1. Carte d'un adhérent **à jour** → fond **vert** + liste de ses adhésions.
2. Carte d'un adhérent **expiré** → fond **orange**.
3. Carte **sans adhésion** → fond **neutre**, paiement OK.
4. **Lespass coupé** (ou mauvaise IP) → fond **neutre/succès**, paiement validé normalement (jamais bloqué).

- [ ] **Step 4 : Vérifier le cache**

2e paiement avec la même carte dans les 24h → pas de nouvel appel HTTP (vérifier les logs Lespass / LaBoutik).

---

## Auto-revue (faite à l'écriture)

- **Couverture spec** : endpoint by-wallet (T1), 2 champs config (T2), couleur (T3), fetch+cache+dégradation (T4), injection réponse (T5), front couleur+liste (T6), setup+recette (T7). ✓
- **Cohérence des noms** : `couleur_adhesion`, `fetch_adhesions`, `COULEUR_VALIDE/EXPIREE/AUCUNE`, `lespass_api_key`, `verifier_adhesion_paiement_nfc`, `adhesion_couleur`/`adhesions` (réponse) — identiques entre tasks. ✓
- **Pas de placeholder** : code réel à chaque étape. Seules zones « à repérer » : l'anchor `transaction_nfc` (T5) et l'admin Configuration (T2) — anchors précis fournis. ✓
- **Point d'attention** : si `Product.ADHESION` / `Price.YEAR` ont d'autres constantes côté Lespass, ajuster le fixture du test T1 (vérifier `BaseBillet/models.py`).
