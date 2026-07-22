# CHANGELOG — LaBoutik

Journal des changements notables. Le plus récent en haut.
/ Notable changes log. Most recent on top.

---

## 2. Adhésions : carte primaire refusée par Fedow / Memberships: primary card rejected by Fedow

**Date :** 2026-07-22

**Quoi / What :** L'encaissement d'une adhésion envoyait à Fedow
`responsable.CarteCashless_Membre.first()` — c'est-à-dire **une carte quelconque
du membre responsable**, sans aucun filtre sur son statut primaire et sans ordre
défini (`CarteCashless` n'a pas de `Meta.ordering`). L'adhésion utilise désormais
`self.primary_card_fisrtTagId`, la carte primaire de la caisse, comme toutes les
autres ventes. Même correction pour la badgeuse, qui passe maintenant par
`CarteMaitresse`.
/ Membership checkout used to send Fedow any card belonging to the responsible
member, with no primary filter and no defined ordering. It now sends the till's
primary card, like every other sale. Same fix for the badge path.

**Pourquoi / Why :** Fedow exige une carte déclarée primaire **pour ce lieu**.
Dès qu'un responsable porte plusieurs cartes (sa carte de gérant plus une carte
personnelle), PostgreSQL pouvait rendre la mauvaise et l'adhésion échouait avec
`{'primary_card_fisrtTagId': 'Carte primaire non valide'}` — de façon
intermittente, alors que la caisse s'ouvrait normalement et que les ventes
classiques passaient. Cas terrain constaté : un responsable avec deux cartes,
dont la première rendue n'était pas la carte maîtresse.

### Fichiers modifiés / Modified files
| Fichier / File | Changement / Change |
|---|---|
| `webview/views.py` | `methode_AD` : envoie `self.primary_card_fisrtTagId` au lieu d'une carte quelconque du responsable. Supprime aussi un `AttributeError` latent quand le responsable n'a aucune carte |
| `fedow_connect/fedow_api.py` | `NFCCard.badge` : carte primaire résolue via `CarteMaitresse` |
| `webview/views.py` | `valider_carte_maitresse` : la révocation d'une `CarteMaitresse` locale et la cause réelle des échecs (Fedow injoignable, clé refusée, carte inconnue) sont désormais tracées — elles étaient toutes avalées sous « Carte non primaire » sans aucun log |
| `fedow_connect/fedow_api.py` | `Subscription.create_sub` lève désormais au lieu de renvoyer un code HTTP ou un dictionnaire d'erreurs. L'appelant attend une transaction : ces retours dégradés le faisaient planter plus loin sur `'int' object is not subscriptable`, message sans rapport avec la cause. Le refus de carte primaire remonte maintenant « Carte primaire non valide », comme `refill_wallet` le faisait déjà |
| `webview/views.py` | `methode_AD` : le `except` laisse passer les `NotAcceptable` déjà explicites au lieu de les écraser par « Erreur fédération ». Les deux messages génériques passent sous `_()` |
| `fedow_connect/fedow_api.py` | Les 8 `NotAcceptable(code=…)` du fichier passent le code HTTP en chaîne (`create_sub`, `refill_wallet`, `to_place`). DRF attend une chaîne pour `code` ; un entier n'avait pas d'effet sur le statut HTTP renvoyé, mais faussait `exc.get_codes()`. Correction de type, sans changement de comportement |

### Migration
- **Migration nécessaire / Migration required :** Non / No

---

## Comment tester (à la main) / Manual test

### Test 1 — l'adhésion qui échouait
1. Prendre un responsable qui porte **deux** cartes, dont une seule est carte primaire.
2. Ouvrir la caisse avec la carte primaire, sélectionner ce responsable.
3. Vendre une adhésion sur une carte client vierge.
4. Attendu : l'adhésion passe. Dans les logs Fedow, plus de
   `validate_primary_card_fisrtTagId`.

### Test 1 bis — le message d'erreur est parlant
1. Prendre une carte **non** primaire et forcer son envoi comme carte primaire
   (ou retirer le statut primaire côté Fedow de la carte de la caisse).
2. Vendre une adhésion.
3. Attendu à l'écran : **« Carte primaire non valide »**, et non plus
   « Erreur fédération. Notez la transaction et contactez un administrateur ».
4. Attendu dans les logs : le dictionnaire d'erreur Fedow réel, et **plus** de
   `'int' object is not subscriptable`.

### Test 2 — la carte primaire révoquée côté Fedow
1. Retirer le statut primaire d'une carte côté Fedow (admin, ou `card/set_primary`
   avec `delete`).
2. Tenter d'ouvrir la caisse avec cette carte.
3. Attendu : refus, la `CarteMaitresse` locale est supprimée, et le log affiche
   `Carte <tag> non primaire chez Fedow : suppression de la CarteMaitresse locale.`

### Test 3 — Fedow injoignable
1. Arrêter Fedow, tenter d'ouvrir la caisse.
2. Attendu : message « Carte non primaire » à l'écran (inchangé), **mais** le log
   serveur porte maintenant `valider_carte_maitresse <tag> : ConnectionError - ...`.

### Vérif DB — repérer les responsables à risque
```python
from APIcashless.models import Membre, CarteMaitresse
for m in Membre.objects.filter(CarteCashless_Membre__isnull=False).distinct():
    cartes = list(m.CarteCashless_Membre.all())
    if len(cartes) > 1:
        maitresses = set(CarteMaitresse.objects.filter(carte__membre=m).values_list('carte__tag_id', flat=True))
        print(m, cartes[0].tag_id, cartes[0].tag_id in maitresses)
```

---

## 1. Popup de retour de transaction responsive / Responsive transaction return popup

**Date :** 2026-06-21
**Issue :** [#104](https://github.com/TiBillet/LaBoutik/issues/104)

**Quoi / What :** Refonte de l'affichage du popup affiché après une transaction
(vente, recharge, lecture de carte) sur le point de vente. Le portefeuille de la
carte passe d'une suite de grosses pastilles empilées à une seule carte dense
(en-tête + lignes `nom ··· valeur` séparées par de fins traits). Le total devient
l'élément dominant, les montants ne se coupent plus (valeur + symbole insécables),
les boutons TICKET et RETOUR sont regroupés dans une zone ancrée en bas, toujours
visible. En paysage court (Sunmi D3 mini), le contenu passe en 2 colonnes (infos
à gauche, adhésions à droite).
/ Redesign of the post-transaction popup (sale, top-up, card check) on the POS.
The card wallet goes from a stack of large pills to a single dense card (header +
`name ··· value` rows separated by hairlines). The total becomes the dominant
element, amounts no longer wrap (value + symbol kept together), and the TICKET and
RETURN buttons are grouped in a bottom-anchored, always-visible zone. In short
landscape (Sunmi D3 mini), the body splits into 2 columns (infos left, memberships
right).

**Pourquoi / Why :** Sur les terminaux Sunmi (V2s portrait, D3 mini paysage),
quand il y avait beaucoup d'informations (plusieurs monnaies, adhésions), le
contenu débordait de l'écran et le bouton RETOUR — indispensable — devenait
inaccessible, obligeant à redémarrer l'application.
/ On Sunmi terminals (V2s portrait, D3 mini landscape), when there was a lot of
information (several currencies, memberships), the content overflowed the screen
and the essential RETURN button became unreachable, forcing an app restart.

**Détails / Details :**
- Affichage du nom porteur `---` (cartes anonymes) masqué.
- Filet de sécurité paysage : une colonne trop chargée défile en interne sans
  jamais pousser les boutons hors de l'écran.
  / Anonymous-card holder name `---` is now hidden. Landscape safety net: an
  overloaded column scrolls internally without pushing the buttons off-screen.

### Fichiers modifiés / Modified files
| Fichier / File | Changement / Change |
|---|---|
| `webview/static/webview/css/modele00.css` | Styles `.popup-wallet*` (carte dense), layout `.popup-retour` (corps / colonnes / actions ancrées), media query paysage 2 colonnes, montants héros `nowrap` |
| `webview/static/webview/js/RetourPosts.js` | `messageRetourAssets()` génère la carte dense ; assemblage du retour (succès + erreur) en corps/colonnes/actions ; nom porteur `---`/vide masqué |
| `webview/templates/popup_check_carte.html` | Même structure (colonnes + carte dense + zone d'actions) ; fallback Fedow conservé à l'identique |

### Migration
- **Migration nécessaire / Migration required :** Non / No (CSS, JS et template uniquement)

### Compatibilité / Compatibility
- Toutes les classes `test-*` (vente + lecture de carte) sont préservées : aucun
  test E2E ni Django impacté. Aucun nouveau texte traduisible (pas de
  `makemessages`).
  / All `test-*` classes (sale + card check) preserved: no E2E or Django test
  impacted. No new translatable string (no `makemessages`).
