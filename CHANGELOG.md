# CHANGELOG — LaBoutik

Journal des changements notables. Le plus récent en haut.
/ Notable changes log. Most recent on top.

---

## 3. Borne kiosk TPE : plus jamais d'écran « Annulé » sans annulation réelle / Kiosk terminal: no "canceled" screen without a real cancellation

**Date :** 2026-07-22

**Quoi / What :** Quand la surveillance d'un paiement TPE se terminait sans succès ni
annulation — délai de 120 s dépassé, ou Stripe injoignable — la borne affichait
« Annulé » alors que **rien n'était annulé chez Stripe**. Le lecteur WisePOS restait
armé. La tâche annule désormais réellement l'action du lecteur **et** l'intention de
paiement, relit le statut chez Stripe, et choisit l'écran d'après ce statut : une carte
présentée juste avant l'annulation affiche donc un vrai succès.
/ When payment polling ended without a terminal status (120 s timeout, or Stripe
unreachable), the kiosk showed "canceled" while nothing was actually canceled on
Stripe — the reader stayed armed. The task now really cancels the reader action and
the payment intent, re-reads the status, and picks the screen from it.

**Pourquoi / Why :** Le lecteur resté armé accepte encore une carte. Le paiement était
alors encaissé par Stripe et la carte créditée par Fedow (via son webhook), **derrière
un écran affichant « Annulé »**. Trois conséquences sur le terrain : l'usager croit
avoir échoué et recharge une seconde fois ; le client **suivant** peut taper sa carte
et créditer celle du précédent ; et tant que `cancel_action` n'est pas appelé, le
lecteur refuse la transaction d'après — borne bloquée jusqu'à intervention.
/ An armed reader still charges a late tap: money taken and card credited behind a
"canceled" screen, double top-ups, the next customer crediting the previous one's
card, and a reader stuck until someone intervenes.

### Fichiers modifiés / Modified files
| Fichier / File | Changement / Change |
|---|---|
| `htmxview/tasks.py` | Nouvelle fonction `cancel_payment_on_stripe()` : annule l'action du lecteur **et** l'intention de paiement, puis relit le statut réel (persisté en base par `get_from_stripe()`). Appelée par **tous** les chemins de sortie non nominaux — c'est l'invariant : aucun écran « Annulé » ne part sans annulation tentée |
| `htmxview/tasks.py` | L'écran final est choisi d'après le statut lu chez Stripe, jamais d'après la raison de sortie de boucle. `success.html` si le paiement a abouti pendant l'annulation |
| `htmxview/tasks.py` | L'appel Stripe est protégé **itération par itération** (`MAX_CONSECUTIVE_STRIPE_ERRORS = 5`). Une coupure réseau d'une seconde ne fait plus sortir de la boucle en sautant l'envoi de l'écran final — cas courant sur le réseau d'un festival |
| `htmxview/tasks.py` | Le `except` global pousse un écran final au lieu de retourner en silence, et passe à `logger.exception` pour conserver la stacktrace côté Sentry |
| `htmxview/tasks.py` | Docstring de `poll_payment_intent_status` réécrite : l'ancienne annonçait un arrêt sur `REQUIRES_PAYMENT_METHOD` que le code n'a jamais fait |
| `htmxview/consumers.py` | Le rejeu d'état lit avec `filter().first()` : `payment_intent_stripe_id` n'est ni `unique` ni indexé, et un `MultipleObjectsReturned` levé **après** `accept()` envoyait la borne en boucle de reconnexion |
| `htmxview/consumers.py` | `ChatConsumer` et `HtmxConsumer` ferment le socket au lieu de lever, comme `PrintConsumer` et `TerminalConsumer` |
| `APIcashless/tests.py` | Quatre blocs d'assertions avaient été enveloppés dans `try: … except: ipdb.set_trace()`. Un `except` nu avale l'`AssertionError` : ces tests passaient au vert quoi qu'il arrive. Retour au motif du projet — `if <anomalie>: set_trace()` **puis** l'assertion, qui survit |
| `htmxview/tests.py` | **Nouveau.** Trois tests de `cancel_payment_on_stripe()` contre un lecteur **simulé** Stripe (`simulated_wisepos_e`), sans matériel. Ignorés (`skipUnless`) si `STRIPE_TEST_API_KEY` est absent ou n'est pas une clé `sk_test_` |

### Migration
- **Migration nécessaire / Migration required :** Non / No

### Vérification faite / Verification performed
La séquence d'annulation a été **exécutée contre l'API Stripe de test** avec un lecteur
simulé. Résultats :
- Après `process_payment_intent` sans carte présentée, le lecteur reste
  `action.status = in_progress` : **le bug d'origine est reproduit**, le lecteur restait
  bien armé derrière l'écran « Annulé ».
- Après la séquence du correctif : lecteur au repos, PaymentIntent `canceled`.
- Carte présentée juste avant l'annulation : Stripe **refuse** l'annulation
  (`InvalidRequestError … status of succeeded`), le statut relu vaut `succeeded`, et
  c'est bien `success.html` qui est choisi. C'est pourquoi les deux annulations sont
  isolées chacune dans leur `try` et le statut relu **après**.
/ The cancellation sequence was run against the Stripe test API with a simulated
reader; the original bug (reader left armed) was reproduced, and both fixed paths
verified.

### Dette laissée en place / Known debt left as is
- Les assertions fédération Fedow commentées dans `APIcashless/tests.py`
  (`len(get_accepted_assets) == 9`, `assertIn('BDG', cats)`, bloc badgeuse/adhésions
  en `"""`) sont **conservées telles quelles** : elles dépendent du contrat
  Fedow/Lespass, c'est au mainteneur de trancher la valeur attendue.
- `APIcashless/tests.py` porte un `ipdb.set_trace()` **inconditionnel** en fin de
  `CashlessTest` (« TOUT PASSE ! On mets un ipdb pour s'amuser »). Il vient de `main`,
  pas de cette branche, mais il fige la suite en exécution non interactive.
- Aucun test automatique ne couvre encore la branche timeout ni le rejeu d'état WS.
- `start_celery.sh` lance le worker sans `--concurrency` ni queue dédiée : chaque
  paiement kiosk monopolise un process pendant jusqu'à 120 s de `time.sleep`, sur la
  même file que l'impression de tickets. Saturation ⇒ `views.py` renvoie un 500 alors
  que le lecteur est **déjà armé**. À traiter dans un chantier séparé.

---

## Comment tester (à la main) / Manual test

### Test 1 — le timeout annule vraiment (le cas critique)
1. Sur la borne kiosk, lancer une recharge (par ex. 10 €) vers le TPE WisePOS.
2. **Ne rien faire** : ne pas présenter de carte, laisser passer les 120 s.
3. Attendu à l'écran de la borne : « Annulé ».
4. **Attendu sur le TPE : il est revenu au repos**, il n'affiche plus « présentez
   votre carte ». C'est le point à vérifier en priorité.
5. Présenter une carte bancaire sur le TPE : **rien ne doit être débité**.
6. Dans le dashboard Stripe, le PaymentIntent doit être en `canceled`.
7. Dans les logs : `Fin de polling sans statut terminal … -- annulation Stripe`.

### Test 2 — paiement juste avant le timeout : c'est le succès qui gagne
1. Lancer une recharge, attendre ~115 s, **puis** présenter la carte.
2. Attendu : la borne affiche **« Réussite »**, jamais « Annulé », et la carte
   cashless est bien créditée.
3. Ce test vérifie que l'écran est choisi d'après Stripe et non d'après la sortie de
   boucle. Le rejouer plusieurs fois : c'est une course, elle doit toujours tomber du
   bon côté.

### Test 3 — coupure réseau brève pendant le polling
1. Lancer une recharge, puis couper l'accès Internet du serveur ~3 s, le rétablir.
2. Attendu : le paiement se poursuit normalement, l'écran ne se fige pas.
3. Logs attendus : `erreur Stripe 1/5`, `2/5`… puis reprise du polling normal.

### Test 4 — coupure réseau de la borne (rejeu d'état)
1. Lancer une recharge, présenter la carte, et **couper le wifi de la borne**
   immédiatement après validation.
2. Rétablir le wifi au bout de ~30 s.
3. Attendu : à la reconnexion du websocket, la borne affiche l'écran final
   (« Réussite ») au lieu de rester sur le spinner.
4. Logs attendus : `Rejeu d'etat WS pour <payment_intent_id> -> kiosk/success.html`.

### Test 5 — bouton ANNULER (non-régression)
1. Lancer une recharge, cliquer sur **❌ ANNULER**.
2. Attendu : TPE au repos, écran « Annulé », PaymentIntent `canceled` chez Stripe.

### Vérif DB — aucun paiement ne doit rester bloqué en cours
```python
from APIcashless.models import PaymentsIntent
from django.utils import timezone
from datetime import timedelta
# Intentions non terminales de plus de 5 minutes : il ne devrait plus y en avoir.
bloquees = PaymentsIntent.objects.filter(
    datetime__lt=timezone.now() - timedelta(minutes=5),
).exclude(status__in=[PaymentsIntent.SUCCEEDED, PaymentsIntent.CANCELED])
for p in bloquees:
    print(p.pk, p.status, p.datetime, p.amount)
```

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
