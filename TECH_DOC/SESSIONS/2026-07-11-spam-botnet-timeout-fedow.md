# Session 2026-07-11 — Spam botnet, timeout Fedow (dérive adhésion), défense anti-crawl

> Récap complet et autonome. Objectif : reprendre dans une session fraîche.
> Repos touchés : **LaBoutik**, **Fedow** (`/home/jonas/TiBillet/dev/Fedow`),
> **Lespass** (`/home/jonas/TiBillet/dev/Lespass`, branche `main`),
> **TraefikV3** (`/home/jonas/Gits/TraefikV3`, future stack, pas en prod).
> ⚠️ Rien n'a été committé ni déployé. Le git est à la main du mainteneur.

---

## 0. TL;DR

Deux problèmes distincts, découverts en cascade :

1. **Timeout Fedow `create_sub` → dérive d'adhésion** (Sentry `LABOUTIK_DJANGO-45`).
   Une adhésion espèce en caisse crée la souscription côté Fedow mais LaBoutik
   timeoute (read=5s) et n'enregistre pas la vente. **Récurrent** (polymorphe 10/07,
   raffinerie 11/07), pas isolé.
2. **La lenteur de Lespass** (qui cause le timeout Fedow) = **un botnet** qui crawle
   `tibillet.org` sur des URLs de doc récursives (spider-trap), saturant les workers.

Cause racine #1 : webhook synchrone Fedow→Lespass **sans timeout** (régression).
Cause racine #2 : un **middleware Lespass** redirige `/fr/*` en 302 (au lieu de 404),
nourrissant un crawler qui suit des liens relatifs empilés.

---

## 1. Incident initial — timeout Fedow `create_sub` (dérive adhésion)

**Symptôme :** `methode_AD fedowAPI.subscription.create_sub : ... Read timed out. (read timeout=5)`
sur `/wv/paiement`, moyen = espèce. Sentry `LABOUTIK_DJANGO-45`.

**Chaîne de cause (confirmée par admin Fedow + logs container + Sentry + git) :**
- LaBoutik `webview/views.py::methode_AD` appelle `create_sub` en **synchrone** (read timeout 5s).
- Fedow crée la souscription (transaction committée en ~150 ms), **puis** le signal
  `post_save` `transaction_webhook_new_membership` (`Fedow/fedow_core/signals.py`) fait un
  `requests.get(https://<lespass>/fwh/membership/<uuid>)` **synchrone**.
- Ce webhook n'avait **plus de timeout** → régression commit **`18d73ed`** (7 jan 2026,
  `timeout=1` retiré). Il a bloqué **~6,7 s** (Lespass saturé, cf. §2) > 5 s → LaBoutik
  abandonne → **pas d'`ArticleVendu`** créé, alors que la souscription **existe** côté Fedow.

**Occurrences (Sentry) :** 2 en 2 jours, 2 instances différentes
(polymorphe métropole 10/07 19:49 CEST ; raffinerie Réunion 11/07 16:29 CEST) → **récurrent**.

**Réconciliation faite :** `ArticleVendu 932` recréé sur **polymorphe** (carte `8BC3ACC5`,
1,00 €, date 2026-07-10 17:49:45 UTC, `sync_fedow=True`). Sûr car `trigger_AD` (post_save
ArticleVendu) ne re-pousse rien vers Fedow → pas de doublon.
**⏳ Reste à faire : réconcilier raffinerie** (carte `919DA1C1`, 3,00 €, 11/07).

**Décision produit :** **Lespass est la source de vérité de l'adhésion**, Fedow est
intermédiaire. Le webhook reste **best-effort + alerte** (pas de relance auto ni de
rollback ; Fedow n'a ni Celery ni management command).

**Fix Fedow appliqué** (`fedow_core/signals.py`, **non committé**, sur `main`) :
```python
try:
    reponse_webhook = requests.get(
        f"https://{url}/fwh/membership/{instance.uuid}",
        verify=bool(not settings.DEBUG),
        timeout=(1, 2))            # borne < 5 s LaBoutik (corrige la régression 18d73ed)
    reponse_webhook.raise_for_status()   # rend visibles les 4xx/5xx Lespass
except requests.RequestException:
    # Adhesion NON propagee a Lespass (source de verite). logger.exception -> event Sentry
    # avec stacktrace. Rattrapage manuel : rejouer le GET (handler idempotent, 208 si deja la).
    logger.exception(
        f"transaction_webhook_new_membership : webhook Lespass ECHEC pour la "
        f"transaction {instance.uuid} — adhesion NON propagee a Lespass. "
        f"Rattrapage : GET https://{url}/fwh/membership/{instance.uuid}")
```
Validé 2× par agent Fable. `logger.exception` remonte bien en event Sentry (LoggingIntegration
par défaut, `event_level=ERROR`). Handler Lespass `/fwh/membership/` **idempotent** (208 si déjà là).

---

## 2. Le vrai coupable de la lenteur Lespass — botnet spider-trap

**Ce n'est PAS un commit qui a alourdi le handler.** Lespass rame parce qu'un **botnet**
sature ses workers gunicorn en crawlant `tibillet.org` sur des URLs de doc **récursives** :
```
/fr/guide-des-lieux/.../guide-des-lieux/.../guide-des-lieux/...
```
(un segment racine du menu doc se **répète** → URL générée en boucle par un crawler).

**Origine du spider-trap :** le middleware Lespass
`Customers/middleware.py::CanonicalDomainRedirectMiddleware._redirection_doc_heritee`
redirige les vieux chemins Docusaurus v2 vers la doc v3 (github.io). Le préfixe **`/fr`**
(dans `PREFIXES_DOC_HERITES`) est **trop large** : **toute** URL `/fr/*` sur le ROOT public
répond **302** (au lieu de 404) → **encourage** le crawler (302 = "continue"), qui suit des
liens relatifs empilés → explosion combinatoire d'URLs.

**Le botnet (logs Traefik `traefik_wild`) :**
- **IPs résidentielles rotatives mondiales** (Mexique, Brésil, Ukraine, UK… ex
  `189.158.61.233`, `86.26.144.38`, `45.4.31.164`, `188.163.8.234`, `179.189.64.15`).
- UA `Mozilla/5.0 (Macintosh…) Chrome/133.0.0.0 Safari/537.36`, HTTP/2, headers réalistes.
- Cible : `tibillet.org` (site vitrine ROOT), chemins `/fr/…`. **Ignore le 410** (4h+).
- **Ne touche pas les caisses** (autres domaines) — juste le CPU mutualisé.

→ **Blocage par IP inutile** (rotation). **Tarpit contre-productif** (retient TES connexions
+ Traefik). Seules vraies parades : **réputation** (CrowdSec + blocklists) ou **challenge** (CDN).

---

## 3. Corrections Lespass appliquées (non committées, `main`)

| Fichier | Changement |
|---|---|
| `Customers/middleware.py` | **Retrait de la redirection doc héritée** (`_redirection_doc_heritee` + constantes/fonction `url_doc_v3_*`). **Gardé** la canonicalisation de domaine. → URLs doc = **404**. |
| `tests/pytest/test_middleware_doc_redirect.py` | **Supprimé** (testait la fonction retirée). |
| `BaseBillet/templates/reunion/partials/error_useful_links.html` | **Créé** — 4 liens (DRY, i18n, a11y, `data-testid`). |
| `BaseBillet/templates/404.html` + `500.html` | `{% include %}` du partial. |

**Les 4 liens des pages 404/500 :** Présentation → `https://tibillet.coop` ·
Documentation → `https://tibillet.github.io/documentation_v3/` · Créer son espace → `/onboard/` ·
Contribuer → `https://codecommun.tibillet.coop/contrib`.
**Validé visuellement dans Chrome** (via une route de preview temporaire, retirée depuis).

**⏳ À faire côté Lespass :** `makemessages`/`compilemessages` (6 nouveaux msgid FR :
`Découvrir TiBillet`, `Liens utiles TiBillet`, `Présentation du projet`, `Documentation`,
`Créer son espace`, `Contribuer à TiBillet`) ; `pytest tests/pytest/` ; brancher + commit.

---

## 4. Mitigation prod actuelle — nginx (anti-crawl + logs)

**Règle nginx** (à insérer avant `location /` dans la conf Lespass, ex `nginx_prod/lespass_prod.conf`).
On reste sur **`410`** (pas `444` : nginx est derrière Traefik → `444` = 502 + logs d'erreur Traefik).
`access_log off` pour ne pas gonfler le disque.

```nginx
    # Anti-crawl 1 : prefixes de doc herites (le bot est 100% sous /fr/). Aucun usage legitime.
    location ~ "^/(fr|en|docs|roadmap|search)(/|$)" {
        access_log off;
        return 410;
    }
    # Anti-crawl 2 : filet — URL de doc recursive (racine repetee)
    location ~ "/(guide-des-lieux|les-bases-et-valeurs-tibillet|guide-des-usagers|guide-des-benevoles|cas-dusages)/.+/(guide-des-lieux|les-bases-et-valeurs-tibillet|guide-des-usagers|guide-des-benevoles|cas-dusages)(/|$)" {
        access_log off;
        return 410;
    }
```
`nginx -t && nginx -s reload`.

---

## 5. ⭐ Amélioration du Traefik EXISTANT (prod actuelle) — options

> Le Traefik de prod actuel (`traefik_wild`) **n'a pas CrowdSec**. La future stack
> TraefikV3 (§6) l'apportera, mais **n'est pas déployée**. Options par ordre d'effort :

### 5.1 Immédiat, gratuit — passer les logs en WARN
Les logs Traefik prod sont en **`level="debug"`** → **3 lignes JSON énormes par requête**.
Avec le flood, c'est **la principale source de gonflage disque** (bien plus que nginx).
→ Passer `--log.level=WARN` (ou `INFO`). **Le changement le plus rentable immédiatement.**
(Dans le repo TraefikV3, le `log.level: DEBUG` est déjà commenté ; la prod tourne encore l'ancien.)

### 5.2 Court terme — mitigation sans CrowdSec
- Un **routeur prioritaire** `Host(\`tibillet.org\`) && PathPrefix(\`/fr/\`)` → middleware
  qui renvoie 403/410, pour couper le hop vers nginx (n'enlève pas le coût TLS).
- **logrotate** sur les logs (la future stack l'a déjà ; l'actuelle à vérifier).

### 5.3 La vraie amélioration — MIGRER vers TraefikV3 (avec CrowdSec)
C'est **LA** solution de fond (voir §6). Mais **ne pas déployer à chaud** en pleine attaque
sans validation (risque TLS/downtime). À préparer proprement puis basculer.

### 5.4 Limite structurelle à connaître
Le coût **TLS** (handshake par connexion) est **incompressible** tant qu'on accepte la
connexion. Contre un botnet à IPs rotatives, seul un **CDN qui absorbe le TLS**
(Cloudflare) l'élimine vraiment. CrowdSec bloque *après* le TLS (mais avant nginx).

**Décision retenue :** (a) WARN tout de suite, (b) finaliser + déployer TraefikV3+CrowdSec,
(c) Cloudflare/challenge gardé en **réserve d'escalade** si le flood vise des routes légitimes.

---

## 6. Future stack TraefikV3 + CrowdSec (`/home/jonas/Gits/TraefikV3`)

**État du check :** stack propre et bien faite (Traefik v3, bouncer CrowdSec sur `websecure`,
logrotate, ACME OVH/Gandi, debug commenté). La collection HTTP `crowdsecurity/traefik`
s'installe **au déploiement** (README étape 4.2) — **normal**, pas un défaut.

**Problème pour CE bot :** les scénarios standard (`http-crawl`, `http-probing`) bannissent
par **taux par IP** → **inefficaces** contre la rotation. → il faut un **scénario custom** +
les **blocklists console** + (idéalement) l'**AppSec**.

### 6.1 Scénario custom "ban à la 1ère occurrence" (validé Fable)
Cible : `crowdsec/config/scenarios/tibillet-http-spider-trap.yaml` (dossier root-owned → `sudo cp`).
Motif « racine doc répétée » = **zéro faux positif** → ban immédiat justifié.
```yaml
type: trigger
name: tibillet/http-doc-spider-trap
description: "Recursive documentation spider-trap URLs (repeated menu root segment)"
filter: |
  evt.Meta.log_type == 'http_access-log' &&
  evt.Meta.http_path matches '(?i)/(guide-des-lieux|les-bases-et-valeurs-tibillet|guide-des-usagers|guide-des-benevoles|cas-dusages)/.+/(guide-des-lieux|les-bases-et-valeurs-tibillet|guide-des-usagers|guide-des-benevoles|cas-dusages)(/|$)'
groupby: evt.Meta.source_ip
blackhole: 1m
labels:
  service: http
  type: scan
  remediation: true          # -> profiles.yaml bannit (Alert.Remediation==true & scope Ip) : ban 4h
  behavior: "http:crawl"
  confidence: 3
  spoofable: 0
```
Install : `sudo cp` → `docker exec crowdsec cscli collections install crowdsecurity/traefik`
→ `docker restart crowdsec` → `cscli scenarios list | grep spider-trap`.
Test à froid : `cscli explain --log '<ligne json access.log>' --type traefik`.

**⚠️ ANGLE MORT (Fable) :** `wildcard_conf/traefik.yml` filtre l'access.log sur
`200-299` et `400-599` → **les 3xx ne sont pas loggés**. Si les URLs répondent en **302**
(redirection doc, tant que le fix 404 n'est pas déployé), **CrowdSec ne voit rien**.
→ soit ajouter `"300-399"` au filtre, soit s'assurer qu'elles sortent en **4xx** (410 nginx / 404 Django).

### 6.2 AppSec (le vrai remède anti-rotation)
`traefik_dynamic.yml` : `crowdsecAppsecEnabled: false` → `true` (host déjà `crowdsec:7422`).
L'AppSec bloque **par requête** (inline, indépendant de l'IP) → seul mécanisme qui coupe la
**1ère** requête de chaque IP. Une règle AppSec custom sur le même motif = complément idéal.

### 6.3 Whitelist des caisses (à poser AVANT les scénarios génériques)
Cible : `crowdsec/config/parsers/s02-enrich/tibillet-whitelist-caisses.yaml` (whitelist au PARSING).
But : ne **jamais** bannir une caisse (cauchemar = couper une vente un soir d'événement).
```yaml
name: tibillet/whitelist-caisses
description: "Ne jamais bannir les flux critiques : caisses LaBoutik, webhooks, admins"
whitelist:
  reason: "Flux critique TiBillet (caisse / paiement) — ban interdit"
  ip:
    - "203.0.113.10"        # EXEMPLE — IP fixe d'un lieu (à remplacer)
  cidr:
    - "198.51.100.0/24"     # EXEMPLE — VPN admin / lieu
  expression:               # filet pour lieux à IP DYNAMIQUE (compromis : host non protégé)
    - "evt.Meta.http_host in ['laboutik.tibillet.coop', 'polymorphe.laboutik.tibillet.coop', 'raffinerie.cashless.tibillet.re']"
    - "evt.Meta.http_host endsWith '.cashless.tibillet.re'"
```
⚠️ Vérifier le nom du champ host (`evt.Meta.http_host` **ou** `evt.Parsed.target_fqdn`
selon version parser) via `cscli explain`. TTL/host = compromis assumé.

### 6.4 Idée : whitelist DYNAMIQUE pilotée par l'authentification
À concevoir (feature, pas conf). Principe : au `user_logged_in` d'un compte
**staff/caisse/kiosk**, Django ajoute l'IP réelle à une **allowlist CrowdSec** (API/`cscli
allowlists`, ≥ v1.6.4) avec un **TTL** (durée session + marge).
**Pièges :** TTL obligatoire (IP dynamiques) ; rôles de confiance uniquement ; cohérence
d'extraction d'IP (X-Forwarded-For) Django↔CrowdSec ; whitelist = tout le NAT ; **appel
best-effort/non-bloquant** (⚠️ même leçon que le webhook Fedow : timeout court + try/except,
ne jamais bloquer le login). Alternative plus simple : **VPN → IP fixe** pour les caisses.

### 6.5 Sécurité
Clé LAPI du bouncer **en clair** dans `traefik_dynamic.yml` (committée). Si le repo devient
distant/partagé : régénérer (`cscli bouncers add`) + injecter via env/secret.

---

## 7. Défense en profondeur (si le bot vise un jour des routes LÉGITIMES)

Le scénario spider-trap est **chirurgical** (motif mort). Sur des routes réelles
(`/event/`, API, caisses), il est aveugle, et on ne peut plus bannir à la 1ère requête.
Parades, par couche :
1. **Cache** (CDN/Varnish/nginx) des pages publiques → le flood tape le cache, pas Django. **Première ligne.**
2. **Rate limiting** par IP **et** global/route (protège la ressource sous rotation).
3. **Scénarios CrowdSec génériques** (attrapent les IPs récurrentes).
4. **Challenge** (Cloudflare Turnstile / Anubis) → **seule** parade contre la rotation sur routes légitimes.
5. **Whitelist des caisses** (§6.3/6.4) pour durcir le reste sans risque.
6. **Segmentation** : caisses/API sur un entrypoint séparé de la vitrine cacheable.

---

## 8. Options RETENUES (récap décisionnel)

| Sujet | Décision retenue | État |
|---|---|---|
| Webhook Fedow | Best-effort + `timeout=(1,2)` + `raise_for_status` + `logger.exception`. Lespass = source de vérité, pas de relance auto. | ✅ codé, ⏳ à committer/déployer |
| Redirection doc Lespass | **Retirée** → 404 (canonicalisation domaine gardée) | ✅ codé, ⏳ à déployer |
| Pages 404/500 | 4 liens (partial DRY) | ✅ codé |
| nginx anti-crawl | **410** + `access_log off` + blocage préfixes `/fr,/en,/docs,/roadmap,/search` | ✅ décidé, ⏳ à appliquer |
| Traefik actuel | Passer **DEBUG → WARN** ; migrer vers TraefikV3+CrowdSec | ⏳ à faire |
| Anti-botnet | **CrowdSec** (scénario custom + blocklists console + AppSec) — self-hosted | ⏳ future stack à finaliser |
| Whitelist caisses | IP fixe + filet host ; **avant** les scénarios génériques | ✅ préparé, ⏳ à poser |
| Whitelist dynamique (auth) | Idée retenue **à concevoir** ; VPN/IP fixe en intermédiaire | 💡 à cadrer (brainstorming) |
| Cloudflare/challenge | **Réserve d'escalade** (routes légitimes / si CPU insoutenable) | 💡 en réserve |

---

## 9. TODO — prochaines étapes (session fraîche)

1. **Déployer le fix Fedow** (`signals.py`) : brancher + commit + déployer.
2. **Réconcilier raffinerie** (carte `919DA1C1`, 3 €, 11/07) — mêmes scripts que polymorphe.
3. **Déployer les fixes Lespass** : makemessages/compilemessages + `pytest tests/pytest/` + brancher + commit.
4. **Appliquer la conf nginx** anti-crawl en prod (§4).
5. **Traefik actuel → WARN** (§5.1) + logrotate.
6. **Finaliser TraefikV3** : collections HTTP, scénario custom, whitelist caisses,
   `cscli console enroll` (blocklists), vérifier le filtre 3xx (§6.1), (option) AppSec.
   Puis **déployer** (migration reverse proxy, à froid).
7. **Décider** whitelist dynamique (auth) **vs** VPN/IP fixe pour les caisses.
8. (fond) Cache pages publiques + rate limit, en prévision d'un flood sur routes légitimes.

---

## 10. Artefacts produits (contenus intégrés ci-dessus)

- Fix Fedow → §1 (dans `Fedow/fedow_core/signals.py`, non committé).
- Fixes Lespass → §3 (dans `Lespass`, non committés).
- Conf nginx anti-crawl → §4.
- Scénario CrowdSec `tibillet-http-spider-trap.yaml` → §6.1.
- Whitelist caisses `tibillet-whitelist-caisses.yaml` → §6.3.
- Scripts de diagnostic/réconciliation (dérive adhésion) : étaient dans le scratchpad
  (éphémère). Logique documentée dans la mémoire projet
  `[[fedow-webhook-membership-timeout]]` (méthode : carte→wallet, GET brut Fedow `_get`,
  check `ArticleVendu`, recréation via bloc `methode_AD`).

## 11. Références

- Sentry : issue `LABOUTIK_DJANGO-45` (2 occurrences, statut `regressed`).
- Commit régression Fedow : `18d73ed` (7 jan 2026, retrait `timeout=1`).
- IPs botnet (échantillon) : `189.158.61.233`, `86.26.144.38`, `45.4.31.164`,
  `188.163.8.234`, `179.189.64.15`, `179.189.64.15`, `170.80.55.195`.
- Doc CrowdSec : parser hub `crowdsecurity/traefik-logs`, `cscli explain/scenarios/decisions/allowlists`.
