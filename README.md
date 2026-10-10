# Mouse Discord — Mouse Shape Finder

Bot Discord (discord.py 2.x) qui recommande une souris gaming selon la géométrie de la main :
longueur et largeur, style de prise (grip), bosse et hauteur des boutons.

L'interface est entièrement dans Discord : un message persistant dans un salon en lecture seule,
puis un flux de messages éphémères (une seule fenêtre qui se met à jour) avec des illustrations.

---

## Sommaire

1. [Fonctionnement](#fonctionnement)
2. [Installation](#installation)
3. [Configuration Discord](#configuration-discord)
4. [Lancer le bot](#lancer-le-bot)
5. [Initialiser le salon : `!setup_finder`](#initialiser-le-salon--setup_finder)
6. [Personnaliser les images](#personnaliser-les-images)
7. [Modifier les liens commerciaux](#modifier-les-liens-commerciaux)
8. [Modifier le catalogue](#modifier-le-catalogue)
9. [Moteur de scoring](#moteur-de-scoring)
10. [Architecture](#architecture)
11. [Tests](#tests)
12. [Audit et données](docs/audit/AUDIT.md)

---

## Fonctionnement

| Étape | Ce que voit l'utilisateur | Action |
|---|---|---|
| Accueil | Message persistant (bannière) dans le salon | Bouton bleu **Start Mouse Shape Finder** |
| 1/3. Grip | Message éphémère + image des 3 grips | Menu : Palm / Claw / Fingertip Grip |
| 2/3. Mesures | Le même message est mis à jour + image « règle » | Bouton **Saisir mes mesures** → modal (longueur, largeur sans pouce) |
| 3/3. Budget | Le même message est mis à jour | Menu : Économique, Rapport Qualité/Prix, Haut de Gamme, Budget Personnalisé (→ modal prix max) |
| Résultat | Le même message affiche le Match Idéal, l'Alternative, l'explication du choix et les souris « à vérifier » | Boutons 🛒 d'achat (liens URL) et 🔄 Refaire le test |

Le muscle thénar a été retiré du parcours : il était collecté mais n'entrait dans aucun calcul (voir `docs/audit/AUDIT.md`).

Les étapes utilisent `interaction.response.edit_message()` : le salon ne se remplit pas de messages.
Les saisies invalides (texte, nombre hors bornes, etc.) déclenchent un message d'erreur explicite
et ne font pas avancer le flux. Les réponses sont visibles uniquement par l'utilisateur.

Les sessions sont stockées **en mémoire**, identifiées par un `session_id` aléatoire propre à chaque parcours
(et non par l'identifiant Discord seul), avec une expiration après 30 min d'inactivité (`SESSION_TTL_SECONDS`).
Relancer un test remplace le précédent : les anciens menus deviennent inactifs. Un redémarrage du bot efface les sessions
en cours : le message persistant continue de fonctionner, mais un ancien menu éphémère affichera « session expirée ».

**Score affiché** : `Score de correspondance : X/40 — Y % du maximum théorique du barème`.
Ce n'est **ni une probabilité d'achat, ni une validation biomécanique** : c'est une estimation géométrique provisoire.

---

## Installation

Prérequis : Python 3.10+ (testé avec 3.11).

```bash
git clone https://github.com/francoiseargaud43-source/MouseDiscord.git
cd MouseDiscord
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # puis renseignez les valeurs
```

Pour lancer les tests : `pip install -r requirements-dev.txt`.

---

## Configuration Discord

1. Créez une application sur le [Discord Developer Portal](https://discord.com/developers/applications),
   puis onglet **Bot** → **Reset Token** : copiez le token dans `DISCORD_TOKEN` (`.env`). Ne le partagez jamais.
2. Dans **Bot → Privileged Gateway Intents**, activez **Message Content Intent**
   (nécessaire pour la commande préfixée `!setup_finder`).
3. Invitez le bot sur votre serveur (**OAuth2 → URL Generator**) :
   - Scopes : `bot`
   - Permissions minimales : *View Channels*, *Send Messages*, *Embed Links*, *Read Message History*.
     Ajoutez *Manage Roles* (« Gérer les permissions » au niveau du salon) uniquement si vous voulez que le bot
     verrouille le salon (`LOCK_FINDER_CHANNEL=true`). Aucune permission *Administrateur* n'est nécessaire.
   - Intent privilégié requis : **Message Content Intent** (étape 2). Sans lui, le bot ne démarre pas.
4. Créez un salon dédié (ex. `#mouse-shape-finder`), copiez son identifiant (mode développeur Discord activé :
   clic droit sur le salon → *Copier l'identifiant*) et renseignez `FINDER_CHANNEL_ID`.

### Variables d'environnement (`.env`)

| Variable | Obligatoire | Défaut | Rôle |
|---|---|---|---|
| `DISCORD_TOKEN` | oui | — | Token du bot |
| `FINDER_CHANNEL_ID` | non | salon où la commande est tapée | Salon cible de `!setup_finder` |
| `COMMAND_PREFIX` | non | `!` | Préfixe des commandes |
| `LOCK_FINDER_CHANNEL` | non | `true` | Met `@everyone` en lecture seule dans le salon au setup |
| `SESSION_TTL_SECONDS` | non | `1800` | Durée d'inactivité avant expiration d'une session |

---

## Lancer le bot

```bash
python bot.py
```

Pour un fonctionnement permanent sur un hébergement (Alwaysdata, services, mise à jour, diagnostic) :
voir **[docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md](docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md)**.
Contrôle avant mise en ligne : `python tools/check_deployment.py`.

Le bot enregistre la vue persistante au démarrage : le bouton fonctionne donc après chaque redémarrage,
sans republier le message. Les logs apparaissent dans le terminal.

---

## Initialiser le salon : `!setup_finder`

Commande réservée aux membres ayant la permission **Gérer le serveur**.

```
!setup_finder            → publie (ou met à jour) le message d'accueil dans FINDER_CHANNEL_ID (ou le salon courant si vide)
!setup_finder #salon     → même chose dans le salon indiqué
```

Ce que fait la commande :
1. Met le salon cible en lecture seule pour `@everyone` (`Envoyer des messages` et `Ajouter des réactions` désactivés),
   **au niveau du salon uniquement** (aucune permission serveur n'est modifiée), sauf si `LOCK_FINDER_CHANNEL=false`.
   Les boutons restent cliquables.
2. Si un message d'accueil a déjà été publié dans ce salon, **il est édité** : aucun doublon n'est créé.
   Sinon, le message « Mouse Shape Finder » est publié avec le bouton **Start Mouse Shape Finder**.
3. Mémorise l'identifiant du message dans `state/finder_message.json` (dossier ignoré par Git).
   Si ce message a été supprimé, ou s'il appartient à un autre salon, un nouveau message est publié.
4. Confirme dans le salon de la commande.

Le bouton est une vue persistante (`custom_id` fixe, enregistrée au démarrage) : il répond encore après un redémarrage du bot.

---

## Personnaliser les images

Toutes les URL d'images sont dans **`assets/images.json`**. Modifiez le fichier et enregistrez :
le bot le relit à chaque interaction, aucun redémarrage n'est nécessaire.

```json
{
  "banner": "https://.../banniere.png",
  "step1_grip": "https://.../3-grips.png",
  "step2_measure": "https://.../mesure-regle.png",
  "step3_budget": ""
}
```

| Clé | Affichée à |
|---|---|
| `banner` | Message persistant d'accueil |
| `step1_grip` | Étape 1/3 — illustration des 3 grips |
| `step2_measure` | Étape 2/3 — main mesurée à la règle |
| `step3_budget` | Étape 3/3 — facultatif (vide = aucune image). Remplace l'ancienne clé `step4_budget`, encore lue en repli. |

Les URL doivent être publiques et commencer par `https://`. Une valeur vide ou invalide n'affiche simplement pas d'image.
**Aucune URL d'image n'est fournie par défaut** : elles seront renseignées par le propriétaire.
Les fichiers Discord (pièces jointes) ne sont pas utilisés : hébergez les images ailleurs.

---

## Modifier les liens commerciaux

Les liens d'affiliation sont dans **`data/commercial_links.json`**, séparés du code :

```json
{
  "scyrox_v8": "https://mon-affiliation.example/scyrox-v8",
  "atk_a9_plus": "https://mon-affiliation.example/atk-a9"
}
```

- La clé est l'`id` de la souris dans `data/mouse_db.json`.
- Une souris sans lien affiche un bouton grisé « Lien bientôt disponible » ; ajoutez simplement son `id` pour l'activer.
- Aucun lien n'est inventé dans le dépôt : le fichier est volontairement vide tant que le propriétaire ne fournit pas les liens.
- Les entrées dont l'URL ne commence pas par `http(s)://` sont ignorées (un avertissement est écrit dans les logs).
- Modification à chaud : rechargé à chaque résultat, sans redémarrage.

---

## Modifier le catalogue

`data/mouse_db.json` contient une liste d'objets (schéma v2). Chaque valeur géométrique porte ses sources.

**Géométrie**

| Champ | Usage |
|---|---|
| `length_mm` | Longueur. `null` = non vérifiée ou en conflit (la souris reste « à vérifier »). |
| `width_max_mm` | Largeur maximale **de la coque** (catalogue). |
| `grip_width_mm` | Largeur de prise **mesurée** — `null` tant qu'aucune mesure n'existe. |
| `height_mm` | Hauteur (informative). |
| `dimension_status` | `verified` (≥ 2 sources concordantes), `single_source`, `conflicting`, `owner_spec`, `owner_spec_unverified`. |
| `conflicts` | Valeurs divergentes et leurs sources (ex. longueur 118.0 vs 117 mm). |
| `shell_id` | Même coque = dimensions partagées (ex. A9 Ultimate / A9 Air / A9 Plus). |

**Compatibilité** (valeurs : `Élevé`, `Moyen`, `Faible`, `Inconnu`)

| Champ | Usage |
|---|---|
| `palm_grip_fit`, `claw_grip_fit`, `fingertip_grip_fit` | Compatibilité par grip. `Inconnu` = non vérifié : la souris est mise **à vérifier** (aucun point n'est attribué). |
| `hump_position` | `Front`, `Mid`, `Rear`, `Mid-Front`, `Mid-Rear`, `Any` ou `Inconnu`. |
| `button_height` | `Low`, `Mid`, `High` ou `Inconnu`. |
| `fit_status` | `owner_spec` (cahier des charges) ou `unverified`. |
| `fit_rationale` | Texte affiché dans le résultat. |

**Commercial** (ne modifie jamais le score géométrique)

| Champ | Usage |
|---|---|
| `price_eur` | Prix en euros. `null` = inconnu : exclu des modes à prix, autorisé en Haut de Gamme. |
| `price_status` | `verified`, `owner_spec_unverified` ou `unknown`. Un prix `verified` exige un prix. |
| `price_note` | Précision (date, devise d'origine…). |
| `budget_tier` | `Économique`, `Qualité-Prix`, `Haut de Gamme` (étiquette, départage visuel uniquement). |
| `weight_g`, `sensor`, `polling_hz` | Caractéristiques documentées. `polling_hz` ≥ 8000 et capteur `PAW3950`/`PAW3955` (variantes) comptent pour le mode Haut de Gamme. |
| `sources` | `[{label, url, fields, date_checked}]`. Obligatoire pour toute donnée `verified` ou `single_source`. |
| `notes` | Commentaires de vérification. |

Le catalogue est validé au chargement (champs manquants, valeurs hors liste, identifiants dupliqués,
conflits sans deux valeurs, dimensions « vérifiées » sans source). Une erreur est signalée dans les logs.

**Régénérer les matrices** après modification : `python tools/compare_profiles.py`.

---

## Moteur de scoring

Code : `utils/matcher.py` (compatibilité géométrique, sans Discord) et `utils/selection.py` (modes).
Toutes les constantes sont nommées en tête de fichier.

**Trois couches distinctes**

1. **Compatibilité morphologique** : points sur 40, identiques quel que soit le mode.
2. **Éligibilité** : `scored` (score final), `pending` (donnée manquante ou en conflit : score partiel, non classable), `excluded` (règle éliminatoire).
3. **Stratégie de sélection** : le mode choisit parmi les candidats `scored`, dans une zone de tolérance. Il ne modifie jamais un score.

**Plages cibles** pour une main de longueur `L` et de largeur `W` (mm) :

| | Palm / Claw | Fingertip |
|---|---|---|
| Longueur min | `71.4 + L × 0.2633` | 0 (pas de minimum) |
| Longueur max | min + 5.0 | `71.4 + L × 0.2633 + 5.0` |
| Largeur min | `48.4 + W × 0.08` | `47.3 + W × 0.08` |
| Largeur max | min + 4.0 | min + 3.9 |

**Largeur de prise utilisée** :
- si `grip_width_mm` est renseignée (mesure) : elle est utilisée (`width_source = measured`) ;
- sinon : `width_max_mm − 3.0` (`GRIP_WIDTH_ESTIMATE_OFFSET_MM`, `width_source = estimated`). **Correctif provisoire**, à remplacer par des mesures.

**Règles strictes** : les seuils d'écart sont stricts (`< 3 mm`, `< 2 mm`, `> 8 mm`, `> 5 mm`). Un écart exactement égal à 3, 2, 8 ou 5 mm
n'est donc pas dans la zone supérieure. Les écarts sont arrondis à 6 décimales avant comparaison (`DELTA_DECIMALS`).

**Points** (total maximum **40**) :

| Critère | Règle | Points |
|---|---|---|
| Longueur | dans la plage / écart < 3 mm / écart > 8 mm | 10 / 5 / exclusion |
| Largeur de prise | dans la plage / écart < 2 mm / écart > 5 mm (`WIDTH_EXCLUDE_DELTA_MM`) | 10 / 5 / exclusion |
| Grip | Élevé / Moyen / Faible | 10 / 5 / exclusion |
| Bosse | Palm : Front ou Mid · Claw : Mid ou Rear · Fingertip : ignorée | 5 · 5 · 0 |
| Boutons | Palm : High · Claw : Low ou Mid · Fingertip : Low | 5 · 5 · 10 |

Les règles de bosse et de boutons sont centralisées dans `HUMP_IDEAL` et `BUTTON_IDEAL` (`utils/matcher.py`).

**Affichage** : `Score de correspondance : X/40 — Y % du maximum théorique du barème`, où `Y = X / 40 × 100` arrondi à l'entier (demi vers le haut).
Le pourcentage n'est jamais présenté comme une probabilité.

**Statuts**

- `excluded` : longueur > 8 mm hors plage, largeur de prise > 5 mm hors plage, grip « Faible », prix > budget (mode budget personnalisé).
- `pending` : aucune exclusion, mais grip, bosse, boutons ou longueur `Inconnu` / en conflit. Le score partiel est affiché, jamais classé.
- `scored` : toutes les données présentes.

**Niveau de confiance** : `élevée` si dimensions vérifiées et largeur de prise mesurée ; `moyenne` si dimensions vérifiées
mais largeur estimée ; `faible` sinon (dimensions d'une seule source, non vérifiées, ou compatibilité non confirmée).

**Modes de sélection** (`utils/selection.py`) — tolérances **provisoires**, à valider :

| Mode | Zone (écart au meilleur score) | Critère dans la zone |
|---|---|---|
| Économique | ≤ 5 pts | prix le plus bas |
| Rapport Qualité/Prix | ≤ 2 pts | points par euro le plus élevé (indicateur provisoire) |
| Haut de Gamme | ≤ 2 pts | performance **documentée** (polling ≥ 8000 Hz, capteur PAW3950/PAW3955 : 0 à 2) ; le prix n'entre pas |
| Budget Personnalisé | ≤ 2 pts, parmi les souris ≤ budget | meilleur score, puis le moins cher |

Les souris sans prix connu ne sont jamais recommandées dans les modes à prix : elles passent dans « À vérifier ».
Une donnée de performance absente compte pour zéro ; cela ne signifie pas une performance inférieure.

**Exemple : main 180 × 90 mm, Palm** (plages 118.8–123.8 mm et 55.6–59.6 mm, valeurs de non-régression) :

| Souris | Résultat | Détail |
|---|---|---|
| Scyrox V6 | **30** | longueur 10 · largeur 10 · grip Moyen 5 · bosse Mid 5 · boutons Mid 0 |
| ATK Z1 V2 Ultra | **30** | longueur 10 · largeur 0 (écart 4.2 mm, zone 2–5 mm) · grip 10 · bosse Mid-Front 5 · boutons High 5 |
| ATK A9 Plus 2.0 | **25** | longueur 5 · largeur 5 · grip Élevé 10 · bosse Mid 5 · boutons 0 |
| ATK X1 V2 Ultra Max | **20** | longueur 0 (écart 3.2 mm) · largeur 5 · grip 10 · bosse 5 · boutons 0 |
| Scyrox V8 / V8S, ATK F1 V3 | exclues | grip Palm « Faible » |

Ces souris donnent, selon le mode : Économique → A9 Plus ; Qualité/Prix → V6 ; Haut de Gamme → Z1 (polling 8000 Hz documenté).

**Matrices complètes** (profils Palm, Claw, Fingertip, toutes les souris du catalogue) : `docs/audit/matrice_profils.md`,
générées par `python tools/compare_profiles.py`.

---

## Architecture

```
MouseDiscord/
├── bot.py                    # Point d'entrée, vue persistante, chargement du cog
├── config.py                 # Variables d'environnement et chemins
├── cogs/
│   ├── mouse_finder.py       # !setup_finder (idempotent, verrouillage du salon)
│   └── finder_flow.py        # Vues, menus, modals, embeds, flux 1/3 à 3/3 et résultat
├── utils/
│   ├── matcher.py            # Compatibilité morphologique (points, statuts, largeur de prise)
│   ├── selection.py          # Modes de sélection (tolérances, classement, explications)
│   ├── models.py             # Grip, BudgetMode, Mouse, Source, HandMeasure
│   ├── catalog.py            # Chargement / validation de mouse_db.json et des liens
│   ├── assets.py             # Lecture de assets/images.json
│   ├── session.py            # Sessions de parcours en mémoire (session_id aléatoire, propriétaire vérifié)
│   └── validation.py         # Validation des saisies des modals
├── data/
│   ├── mouse_db.json         # Catalogue v2 (géométrie + sources, compatibilité, prix)
│   └── commercial_links.json # Liens d'affiliation (vide tant que non fournis)
├── assets/
│   └── images.json           # URL des images des étapes (vides tant que non fournies)
├── tools/
│   ├── check_deployment.py   # Contrôle de déploiement (fichiers, token, JSON, state/) — sans afficher le token
│   ├── build_mouse_db.py     # Génère le catalogue v2 à partir des données sourcées
│   └── compare_profiles.py   # Génère docs/audit/matrice_profils.md
├── docs/
│   ├── DEPLOYMENT_ALWAYSDATA_FILEZILLA.md  # Guide de mise en ligne (Alwaysdata, FileZilla, mise à jour)
│   └── audit/                # Audit, catalogue ATK, matrices, rapports
├── state/                    # Message publié par !setup_finder (ignoré par Git)
├── tests/                    # pytest
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Tests

Reproduire les résultats (depuis la racine du dépôt, environnement virtuel activé) :

```bash
pip install -r requirements-dev.txt
pytest -q
python -m pyflakes bot.py config.py cogs utils tests tools
python tools/privacy_scan.py          # contrôle statique de confidentialité (0 violation attendue)
python tools/compare_profiles.py     # régénère docs/audit/matrice_profils.md
```

- `tests/test_matcher.py` : plages cibles, points pour 180 × 90 mm en Palm (non-régression), bornes strictes, largeur mesurée vs estimée, statuts `scored` / `pending` / `excluded`, budget personnalisé.
- `tests/test_selection.py` : effet réel de chaque mode, tolérances, prix inconnus, candidats à vérifier jamais classés.
- `tests/test_catalog_lookup.py` et `tests/test_data.py` : schéma v2, validation des erreurs, absence de valeur inventée, liens et images vides par défaut, repli de clé d'image.
- `tests/test_validation.py` : saisies valides, invalides et hors bornes des modals.
- `tests/test_session.py` : isolation des sessions par `session_id`, propriétaire, remplacement d'un parcours, expiration.
- `tests/test_privacy.py` : scénarios de confidentialité P02–P12 (parcours complet, deux utilisateurs simultanés, intrus, expiration, redémarrage) — voir `docs/audit/AUDIT_CONFIDENTIALITE.md`.
- `tests/test_privacy_scan.py` : contrôle statique `tools/privacy_scan.py` (envois non éphémères, éditions hors fonctions autorisées, alias, appels dynamiques) : cas valides, violations injectées, dépôt réel.
- `tests/test_doc_references.py` : chemins cités dans la documentation existants, titres de section exacts.
- `tests/test_config.py` : chemins indépendants du répertoire courant, entiers invalides signalés clairement.
- `tests/test_deployment_check.py` : diagnostics de `tools/check_deployment.py` sur un projet factice.
- `tests/test_flow.py` : parcours complet 1/3 à 3/3 avec interactions simulées (édition de message, erreurs de saisie, affichage du score, section « à vérifier »), confidentialité (aucun envoi public, analyse statique), lien manquant → « Lien bientôt disponible ».
- `tests/test_setup_command.py` : publication, édition sans doublon, message supprimé, autre salon, fichier d'état corrompu.

**Ce que les tests ne couvrent pas** : une vraie connexion Discord. Les vérifications suivantes doivent être faites à la main
(voir `docs/audit/RAPPORT_FINAL.md`, §8 « Vérifications Discord manuelles (non exécutées) » et le protocole `docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md`, non exécuté) : isolation des sessions entre deux utilisateurs,
interactions expirées, vue persistante après redémarrage, absence d'accumulation de messages, permissions limitées au salon.

---

