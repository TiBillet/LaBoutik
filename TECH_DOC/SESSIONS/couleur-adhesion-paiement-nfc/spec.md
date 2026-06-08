# Chantier — Couleur d'adhésion sur le message de validation de paiement NFC

Date : 2026-05-23

## Objectif

Lors d'un paiement par carte NFC au POS LaBoutik, **colorer le fond du popup de
validation de paiement** selon le statut d'adhésion du porteur de la carte, et
**lister ses adhésions** dans le popup.

3 états de couleur :
- 🟢 adhésion valide
- 🟠 adhésion(s) présente(s) mais toutes expirées
- ⚪ aucune adhésion (paiement OK quand même)

## Périmètre : 2 dépôts

- **Lespass** : source de vérité des adhésions (expose une lecture).
- **LaBoutik** : POS, fait l'appel et l'affichage.

## Décisions verrouillées (et pourquoi)

| Décision | Raison |
|---|---|
| Statut = **validité** (3 états), pas seulement présence | Fedow ne porte pas la `deadline` d'adhésion (tokens `SUB` = présence + `start_membership_date` uniquement). La validité vient de Lespass (`Membership.is_valid()`). |
| Lookup par **wallet_uuid** Fedow (pas tag_id) | Lespass relie l'user via le wallet (`TibilletUser.objects.filter(wallet__uuid=...)`, cf. `fedow_connect/views.py:44`), jamais par tag_id. LaBoutik a déjà le wallet_uuid au moment du paiement → **0 appel Fedow en plus**. |
| Canal = **api_v2 + ExternalApiKey** (clé API + IP) | Mécanisme existant. `SemanticApiKeyPermission` vérifie déjà clé + IP + permission `membership`. Aucun nouveau canal ni signature à coder. |
| Setup **manuel par un admin** | L'admin crée la clé dans Lespass et la colle dans LaBoutik (cf. § Setup). |
| **Cache 24h** côté LaBoutik | L'adhésion change rarement d'un jour à l'autre. Au plus 1 appel/jour/carte. |
| Timeout court + dégradation neutre | Lespass lent/down → couleur neutre, **le paiement n'est jamais bloqué ni retardé**. |

## A. Côté Lespass (`api_v2`)

### Endpoint (lecture seule)

```
GET /api/v2/memberships/by-wallet/?wallet_uuid=<uuid>
Header : Authorization: Api-Key <clé ExternalApiKey>
```

- **Implémentation** : `@action(detail=False, methods=["get"], url_path="by-wallet")`
  sur `MembershipViewSet` (`api_v2/views.py:336`).
- **Auth** : la permission existante `SemanticApiKeyPermission` du viewset
  (`get_apikey_valid`, `ApiBillet/permissions.py:24-44`) vérifie automatiquement :
  clé API → `ExternalApiKey`, **IP** (`ExternalApiKey.ip`), permission `membership`.
  → **Rien à coder pour l'IP ni la clé.**
- **Logique** (même résolution que le webhook existant) :
  ```python
  user = TibilletUser.objects.filter(wallet__uuid=wallet_uuid).first()
  memberships = user.memberships.all() if user else []
  ```
- **Réponse** :
  ```json
  {
    "wallet_uuid": "…",
    "memberships": [
      {"product_name": "Adhésion annuelle", "price_name": "Tarif normal",
       "is_valid": true, "deadline": "2026-09-01T23:59:59Z"}
    ]
  }
  ```
  Wallet éphémère / pas d'user → `"memberships": []`.
- **Serializer** : petit serializer dédié minimal dans `api_v2/serializers.py`
  (`product_name`, `price_name`, `is_valid`, `deadline`). On NE réutilise PAS le
  gros `MembershipSerializer` d'ApiBillet (trop de champs inutiles ici).

### Migration Lespass

**Aucune.** `ExternalApiKey.ip` et `.membership` existent déjà.

## B. Côté LaBoutik

### Migration — 2 champs sur `Configuration` (`APIcashless/models.py`)

- `lespass_api_key = CharField(max_length=100, blank, null)` — la clé `ExternalApiKey` collée par l'admin.
- `verifier_adhesion_paiement_nfc = BooleanField(default=False)` — active la feature.

### Au paiement NFC réussi (`Commande`, `webview/views.py`)

Si `config.verifier_adhesion_paiement_nfc` actif :
1. `wallet_uuid` = celui de la carte qui paie : `self.carte_db.get_wallet().uuid`
   (déjà chargé, cf. `webview/views.py:676`). En cas de paiement 2 cartes, on ne
   regarde que la carte principale `self.carte_db`.
2. Lecture cache `adhesion:{wallet_uuid}` (cache Django / memcached, **TTL 24h**).
3. Miss → appel HTTP :
   ```python
   requests.get(
       f"{config.billetterie_url}/api/v2/memberships/by-wallet/?wallet_uuid={wallet_uuid}",
       headers={"Authorization": f"Api-Key {config.lespass_api_key}"},
       timeout=1.5,
       verify=bool(not settings.DEBUG),
   )
   ```
   → succès : liste mise en cache 24h.
4. Flag off / timeout / erreur / clé absente → `adhesions=[]`, statut `unknown`.
5. Ajout à la réponse : `self.reponse['adhesions']` (liste) + `self.reponse['adhesion_couleur']`.

### Calcul de la couleur (serveur LaBoutik, fonction simple)

```
≥ 1 adhésion is_valid           → '#339448' (vert)
liste non vide, aucune valide   → '#b85521' (orange)
liste vide                      → '#1a1e25' (neutre)
unknown (Lespass injoignable)   → None (le front garde la couleur succès actuelle)
```

### Front (`webview/static/webview/js/`)

- `RetourPosts.js` (`afficherRetourVenteDirecte`, branche paiement NFC réussi) :
  si `retour.adhesions` présent, passer la couleur à `fn.popup` et injecter la
  **liste des adhésions** dans le corps du message. Uniquement sur succès
  (un échec garde le rouge habituel).
- `modules/fonctions.js` (`popup`, ligne 119) : ajouter un paramètre optionnel
  `couleur` à `fn.popup({…})` qui surcharge `style_fond` (ligne 135) quand il est
  fourni. Sinon comportement inchangé (couleur par `type`).

## Fichiers touchés

**Lespass**
- `api_v2/views.py` — `MembershipViewSet` : + action `by-wallet`.
- `api_v2/serializers.py` — + serializer minimal.

**LaBoutik**
- `APIcashless/models.py` — `Configuration` : + 2 champs (+ migration).
- `webview/views.py` — `Commande` : appel + cache + réponse + calcul couleur.
- `webview/static/webview/js/RetourPosts.js` — couleur + liste dans le popup.
- `webview/static/webview/js/modules/fonctions.js` — `popup` : couleur optionnelle.
- `administration/adminstaff.py` — exposer les 2 champs config (à vérifier).

## Setup admin (manuel, une fois par connexion)

1. **Lespass admin** → créer un `ExternalApiKey` : `membership=True`,
   `ip = <IP publique du serveur LaBoutik>`, copier la clé générée.
2. **LaBoutik admin** → `Configuration.lespass_api_key` = la clé,
   `verifier_adhesion_paiement_nfc` = activé.

## Robustesse / dégradation

- Lespass lent/down → timeout 1,5 s → couleur neutre, le paiement passe.
- Cache 24 h → au plus 1 appel/jour/carte.
- Clé absente / IP non autorisée → 403 côté Lespass → traité comme `unknown`.

## Hors périmètre (YAGNI)

- Le popup *check carte* (déjà coloré via présence Fedow) reste inchangé.
- Pas de signature RSA, pas de nouveau champ IP, pas de nouveau canal.

## Tests à prévoir

**Lespass**
- Clé valide + bonne IP + adhésion valide → liste avec `is_valid=true`.
- Adhésion expirée → `is_valid=false`.
- Wallet inconnu / éphémère → `memberships: []`.
- Sans clé / mauvaise IP → 403.

**LaBoutik**
- Calcul couleur : valide → vert, expiré → orange, vide → neutre, unknown → None.
- Cache : 2e paiement même carte dans 24 h → pas de 2e appel HTTP.
- Flag off → aucun appel.

**Manuel (POS réel)**
- Paiement NFC adhérent à jour → fond vert + liste.
- Adhérent expiré → fond orange.
- Non-adhérent → fond neutre.
- Lespass coupé → fond neutre, paiement validé normalement.
