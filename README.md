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

---

## Fonctionnement

| Étape | Ce que voit l'utilisateur | Action |
|---|---|---|
| Accueil | Message persistant (bannière) dans le salon | Bouton bleu **Start Mouse Shape Finder** |
| 1. Grip | Message éphémère + image des 3 grips | Menu : Palm / Claw / Fingertip Grip |
| 2. Mesures | Le même message est mis à jour + image « règle » | Bouton **Saisir mes mesures** → modal (longueur, largeur sans pouce) |
| 3. Thénar | Le même message est mis à jour + image des zones | Menu : Small / Medium / Large (collecté, sans impact sur le calcul) |
| 4. Budget | Le même message est mis à jour | Menu : Économique, Rapport Qualité/Prix, Haut de Gamme, Budget Personnalisé (→ modal prix max) |
| Résultat | Le même message affiche le Top 1 et le Top 2 | Boutons 🛒 d'achat (liens URL) et 🔄 Refaire le test |

Les étapes utilisent `interaction.response.edit_message()` : le salon ne se remplit pas de messages.
Les saisies invalides (texte, nombre hors bornes, etc.) déclenchent un message d'erreur explicite
et ne font pas avancer le flux. Les réponses sont visibles uniquement par l'utilisateur.

Les sessions sont stockées **en mémoire**, une par utilisateur (`session_id = user_id`), avec une expiration
après 30 min d'inactivité (`SESSION_TTL_SECONDS`). Un redémarrage du bot efface les sessions en cours :
le message persistant, lui, continue de fonctionner.

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
   - Permissions minimales : *View Channels*, *Send Messages*, *Embed Links*, *Read Message History*,
     *Manage Roles* et *Manage Channels* (uniquement si vous voulez que le bot verrouille le salon, voir `LOCK_FINDER_CHANNEL`).
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

Le bot enregistre la vue persistante au démarrage : le bouton fonctionne donc après chaque redémarrage,
sans republier le message. Les logs apparaissent dans le terminal.

---

## Initialiser le salon : `!setup_finder`

Commande réservée aux membres ayant la permission **Gérer le serveur**.

```
!setup_finder            → publie le message d'accueil dans FINDER_CHANNEL_ID (ou le salon courant si vide)
!setup_finder #salon     → publie dans le salon indiqué
```

Ce que fait la commande :
1. Met le salon cible en lecture seule pour `@everyone` (`Envoyer des messages` et `Ajouter des réactions` désactivés),
   sauf si `LOCK_FINDER_CHANNEL=false`. Les boutons restent cliquables.
2. Publie l'embed « Mouse Shape Finder » avec le bouton **Start Mouse Shape Finder**.
3. Confirme dans le salon de la commande.

> Relancer `!setup_finder` publie un **nouveau** message : supprimez l'ancien à la main pour éviter les doublons
> (les deux restent fonctionnels).

---

## Personnaliser les images

Toutes les URL d'images sont dans **`assets/images.json`**. Modifiez le fichier et enregistrez :
le bot le relit à chaque interaction, aucun redémarrage n'est nécessaire.

```json
{
  "banner": "https://.../banniere.png",
  "step1_grip": "https://.../3-grips.png",
  "step2_measure": "https://.../mesure-regle.png",
  "step3_thenar": "https://.../zones-thenar.png",
  "step4_budget": ""
}
```

| Clé | Affichée à |
|---|---|
| `banner` | Message persistant d'accueil |
| `step1_grip` | Étape 1 — illustration des 3 grips |
| `step2_measure` | Étape 2 — main mesurée à la règle |
| `step3_thenar` | Étape 3 — zones rouges Small / Medium / Large |
| `step4_budget` | Étape 4 — facultatif (vide = aucune image) |

Les URL doivent être publiques et commencer par `https://`. Une valeur vide ou invalide n'affiche simplement pas d'image.
Les fichiers Discord (pièces jointes) ne sont pas utilisés : hébergez les images ailleurs (ou sur un salon Discord
et copiez le lien direct de l'image).

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
- Les entrées dont l'URL ne commence pas par `http(s)://` sont ignorées (un avertissement est écrit dans les logs).
- Modification à chaud : rechargé à chaque résultat, sans redémarrage.

---

## Modifier le catalogue

`data/mouse_db.json` contient une liste d'objets avec les champs suivants :

| Champ | Valeurs | Usage |
|---|---|---|
| `id` | identifiant unique | Clé de jointure avec `commercial_links.json` |
| `brand`, `model` | texte | Nom affiché |
| `price_eur` | nombre | Prix (filtre « Budget Personnalisé ») |
| `budget_tier` | `Économique`, `Qualité-Prix`, `Haut de Gamme` | Départage des ex æquo |
| `length_mm`, `width_max_mm` | nombre | Dimensions (largeur ajustée de −3 mm) |
| `hump_position` | `Front`, `Mid`, `Rear`, `Mid-Front`, `Any`… | Bosse |
| `button_height` | `Low`, `Mid`, `High` | Hauteur des boutons |
| `palm_grip_fit`, `claw_grip_fit`, `fingertip_grip_fit` | `Élevé`, `Moyen`, `Faible` | Compatibilité par grip |
| `fit_rationale` | texte | Raison affichée dans le résultat |

Le catalogue est validé au chargement (champs manquants, valeurs hors liste, identifiants dupliqués).
Une erreur est signalée dans les logs et l'utilisateur voit un message d'erreur générique.

---

## Moteur de scoring

Code : `utils/matcher.py`. Constantes nommées en tête de fichier.

**Plages cibles** pour une main de longueur `L` et de largeur `W` (mm) :

| | Palm / Claw | Fingertip |
|---|---|---|
| Longueur min | `71.4 + L × 0.2633` | 0 (pas de minimum) |
| Longueur max | min + 5.0 | `71.4 + L × 0.2633 + 5.0` |
| Largeur min | `48.4 + W × 0.08` | `47.3 + W × 0.08` |
| Largeur max | min + 4.0 | min + 3.9 |

**Largeur évaluée** = `width_max_mm − 3.0` (constante `WIDTH_MEASUREMENT_OFFSET_MM`).

**Filtre budget** (mode « Budget Personnalisé » uniquement) : exclusion si `price_eur > budget`.

**Points** (total maximum **40**) :

| Critère | Règle | Points |
|---|---|---|
| Longueur | dans la plage / écart < 3 mm / écart > 8 mm | 10 / 5 / exclusion |
| Largeur | dans la plage / écart < 2 mm / écart > 4 mm | 10 / 5 / exclusion |
| Grip | Élevé / Moyen / Faible | 10 / 5 / exclusion |
| Bosse | Palm : Front ou Mid · Claw : Mid ou Rear · Fingertip : ignorée | 5 · 5 · 0 |
| Boutons | Palm : High · Claw : Low ou Mid · Fingertip : Low | 5 · 5 · 10 |

Tri : score décroissant, puis souris dont `budget_tier` correspond au choix d'Étape 4
(Économique → « Économique », Rapport Qualité/Prix → « Qualité-Prix », Haut de Gamme → « Haut de Gamme »).
Le muscle thénar n'entre jamais dans le calcul.

**Exemple : main 180 × 90 mm, Palm**, plages cibles 118.8–123.8 mm et 55.6–59.6 mm :

| Souris | Résultat | Détail |
|---|---|---|
| Scyrox V6 | **30** | longueur 10 · largeur 10 · grip Moyen 5 · bosse Mid 5 · boutons Mid 0 |
| ATK A9 Plus 2.0 | **25** | longueur 5 · largeur 5 · grip Élevé 10 · bosse Mid 5 · boutons 0 |
| ATK X1 V2 Ultra Max | **20** | longueur 0 (écart 3.2 mm) · largeur 5 · grip 10 · bosse 5 · boutons 0 |
| ATK Z1 V2 Ultra | exclue | largeur évaluée 63.8 mm, écart 4.2 mm > 4 mm |
| Scyrox V8 / V8S, ATK F1 V3 | exclues | grip Palm « Faible » |

---

## Architecture

```
MouseDiscord/
├── bot.py                    # Point d'entrée, vue persistante, chargement du cog
├── config.py                 # Variables d'environnement et chemins
├── cogs/
│   ├── mouse_finder.py       # Commande !setup_finder (+ verrouillage du salon)
│   └── finder_flow.py        # Vues, menus, modals, embeds, flux des étapes 1 à 4 et résultat
├── utils/
│   ├── matcher.py            # Moteur de scoring (pur Python, sans Discord)
│   ├── models.py             # Grip, BudgetMode, Thenar, Mouse, HandMeasure
│   ├── catalog.py            # Chargement / validation de mouse_db.json et des liens
│   ├── assets.py             # Lecture de assets/images.json
│   ├── session.py            # Sessions utilisateur en mémoire (session_id = user_id)
│   └── validation.py         # Validation des saisies des modals
├── data/
│   ├── mouse_db.json         # Catalogue (géométrie, prix, compatibilité)
│   └── commercial_links.json # Liens d'affiliation (modifiable à tout moment)
├── assets/
│   └── images.json           # URL des images des étapes
├── tests/                    # pytest
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Tests

```bash
pytest
```

- `tests/test_matcher.py` : plages cibles, pondérations pour une main **180 × 90 mm en Palm**
  (V6 = 30, A9 Plus = 25, X1 = 20, Z1 et V8 exclues), bornes des seuils, tri et départage.
- `tests/test_validation.py` : saisies valides, invalides et hors bornes des modals.
- `tests/test_session.py` : durée de vie des sessions.
- `tests/test_flow.py` : parcours complet du flux avec des interactions simulées (édition de message, erreurs de saisie, budget personnalisé).
- `tests/test_setup_command.py` : publication et verrouillage du salon par `!setup_finder`.
- `tests/test_data.py` : intégrité des fichiers de `data/` et `assets/`.
