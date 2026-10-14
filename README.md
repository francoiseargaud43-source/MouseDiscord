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
12. [Design et illustrations](docs/REPORTE_DESIGN.md)
13. [Faire enrichir le catalogue par une IA](docs/PROMPT_RECHERCHE_SOURIS_ATK.md) — [Analyse vidéo Oblivity et améliorations proposées](docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md)
14. [Audit et données](docs/audit/AUDIT.md)

---

## Fonctionnement

| Étape | Ce que voit l'utilisateur | Action |
|---|---|---|
| Accueil | Message persistant : bannière AzeMouse (`T08`) | Bouton **Start Mouse Shape Finder** |
| 1/… Prise | Message éphémère + illustration des 3 prises (`T09`) | Menu : Palm / Claw / Fingertip Grip |
| 2/5. Variante de Claw | Le même message + les trois variantes (`T04`) | Menu : Claw relâchée / agressive / pincée — **prise Claw uniquement**, aucun effet sur le score (précise le conseil de bosse) |
| 2/4 – 3/5. Thénar | Le même message est mis à jour + tailles de thénar (`T10`) | Menu : Petite / Moyenne / Grande — **informatif** (aucun effet sur le score). **Étape sautée avec la prise Fingertip** (parcours en 3 étapes : 1 → 2/3 → 3/3) |
| 3/4 – 4/5. Mesures | Le même message + main mesurée à la règle (`T11`) | Bouton **Saisir mes mesures** → modal (longueur, largeur sans pouce) |
| 4/4 – 5/5. Budget | Le même message est mis à jour + récapitulatif | Menu : Économique, Rapport Qualité/Prix, Haut de Gamme, **Peu importe le prix**, Budget personnalisé (→ modal prix max) |
| Résultat | **Un message privé, plusieurs blocs illustrés** : la recommandation (match idéal, alternative, troisième place — « 💸 L'économie », « ➕ L'autre option » ou « 🔎 Autre piste » — pourcentages **ordonnés du haut vers le bas** et prix non attestés **signalés** depuis le 2026-10-13), les deux dernières lignes étant remplies **dès que le budget le permet** depuis le 2026-10-12 — nom, **poids**, prix, pourcentage, puis **symétrique / ergonomique** tout à droite), puis 📐 vos repères de taille, 🖐️ l'arrière étroit (thénar « Petite »), ⛰️ la bosse, 🦾 les variantes de Claw et 🖱️ la hauteur des boutons conseillée | Boutons 🛒 d'achat (liens réels), ou « 🔗 Liens à venir » |

**Thénar (étape 2/4)** : collecté et affiché à titre **informatif** — aucune source ne définit de règle thénar → dimensions,
il n'entre donc dans **aucun** calcul (ni points, ni classement, ni exclusion) : voir `docs/audit/AUDIT.md`.
En **Fingertip**, l'étape n'est **pas posée** : cette prise ne s'appuie sur l'arrière de la souris (la bosse est déjà
ignorée par le barème), donc ni thénar ni note « arrière étroit » ne sont demandés ni affichés (`_steps_total`).

**Identité visuelle** : bordeaux `#8A2342` en couleur latérale de tous les embeds (« session expirée » exceptée, en orange),
illustrations sur fond Nuit `#0B1220` avec liseré bordeaux et une touche de jaune Étincelle `#F0C43C`.
Aucune image n'est inventée : voir `docs/REPORTE_DESIGN.md`.

Les étapes utilisent `interaction.response.edit_message()` : le salon ne se remplit pas de messages.
Les saisies invalides (texte, nombre hors bornes, etc.) déclenchent un message d'erreur explicite
et ne font pas avancer le flux. Les réponses sont visibles uniquement par l'utilisateur.

**Un parcours ne reste jamais en impasse** (corrigé le 2026-10-12, voir `docs/audit/ROBUSTESSE_2026-10-12.md`) :

- les composants des étapes ont des identifiants fixes, sans délai, et sont **enregistrés au démarrage** : un clic est
  reconnu même après un redémarrage du bot ;
- chaque action se rattache au **parcours vivant du membre qui clique** (aucun identifiant de parcours ne circule dans les
  messages : rien à falsifier, rien à expirer) ;
- les parcours **en cours** sont enregistrés dans `state/sessions.json` : une mise à jour du bot ne fait plus perdre un
  questionnaire commencé (`SESSION_PERSIST=false` pour revenir au tout-mémoire) ;
- un parcours interrompu affiche la **raison** et un **bouton de reprise** dans le message lui-même : un clic suffit pour
  repartir, sans retourner au panneau du salon ;
- toute erreur inattendue est tracée et expliquée en privé au membre — jamais un silence.

**Premier écran** : la ligne du parcours, puis les souris utiles — nom, prix et **pourcentage du maximum
théorique** pour le match idéal, l'alternative et la troisième place (remplies dès que le budget le permet : « 💸 économie » si elle en est une, « ➕ autre option » sinon, « 🔎 autre piste » quand la souris vient du dernier palier ; les pourcentages **ne remontent jamais** d'une ligne à l'autre, une souris dont le prix n'est pas attesté l'annonce : « 74,90 € (prix non vérifié) », et une souris dont la hauteur des boutons n'est pas documentée — donc notée sans ce critère — porte « · boutons non documentés » quand elle occupe une 2e ou 3e place). Ni score /40, ni souris
écartées à ce niveau : le détail vient **plus bas dans le même message privé**, en petits blocs illustrés,
dans l'ordre de l'outil de référence (Oblivity) :

| Bloc | Contenu | Image |
|---|---|---|
| 📐 Vos repères de taille | longueur cible, largeur de prise, score `/40 — %`, la souris retenue « en clair », le pourquoi du choix | T12 |
| 🖐️ Un arrière étroit pour votre thénar | seulement si le thénar est « Petite » (jamais en Fingertip) | T13 |
| ⛰️ La bosse et la forme | où placer la bosse (**selon la variante de Claw déclarée**), quelle forme de coque convient (symétrique / ergonomique) et la forme de la souris retenue ; absent en Fingertip | T14 ou T07 |
| 🦾 Votre variante de Claw | la variante déclarée (ou les trois à titre indicatif si le parcours a été ouvert sans cette étape) | T04, T05 ou T06 |
| 🖱️ La hauteur des boutons | niveau conseillé (Palm : hauts ; Claw : bas ; Fingertip : médians à bas) | T01, T02 ou T03 |

Les détails du barème (`Longueur … : 10 pts`) ne sont jamais affichés : ils restent dans `MouseScore.details` et
dans `docs/audit/matrice_profils.md`. Ce n'est **ni une probabilité d'achat, ni une validation biomécanique** :
c'est une estimation géométrique provisoire.

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
| `SESSION_TTL_SECONDS` | non | `1800` | Durée d'inactivité avant expiration d'un parcours |
| `SESSION_PERSIST` | non | `true` | Conserve les parcours en cours dans `state/sessions.json` (`false` = mémoire seulement) |

Les deux variables booléennes acceptent `true`/`false` (aussi `1`/`0`, `yes`/`no`, `on`/`off`,
`oui`/`non`, `vrai`/`faux`) : **toute autre valeur empêche le démarrage**, avec la liste des
orthographes acceptées dans le message. Une faute de frappe dans le `.env` ne passe donc jamais
inaperçue — avant, elle désactivait la fonction en silence (corrigé le 2026-10-13).

---

## Lancer le bot

```bash
python bot.py
```

Pour un fonctionnement permanent sur un hébergement (Alwaysdata, services, mise à jour, diagnostic) :
voir **[docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md](docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md)**.
Contrôle avant mise en ligne : `python tools/check_deployment.py`.

Le bot enregistre **tous** les composants du parcours au démarrage (six menus, deux formulaires) : les boutons
fonctionnent donc après chaque redémarrage, sans republier le message. Les logs apparaissent dans le terminal.

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

Deux façons de renseigner une image (elles peuvent cohabiter) :

1. **Nom de fichier** repris de `assets/illustrations/` — recommandé, c'est ce qui est livré :

   ```json
   { "banner": "T08_azemouse_banniere.png" }
   ```

   La résolution se fait avec `IMAGES_BASE_URL` (fichier `.env`), qui désigne le dossier public où vous avez
   publié les illustrations. **Une seule variable à changer au déploiement** (voir la section
   « Publier les illustrations » de `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`) :

   ```
   IMAGES_BASE_URL=https://[compte].alwaysdata.net/illustrations/
   ```

   Un nom de fichier **sans** `IMAGES_BASE_URL` n'affiche aucune image (aucune erreur, aucun plantage).

2. **URL complète** `https://…` (hébergement externe) : utilisée telle quelle, prioritaire sur la base.

```json
{
  "banner": "T08_azemouse_banniere.png",
  "step1_grip": "T09_griffe_paume_doigts.png",
  "step2_thenar": "T10_tailles_de_main.png",
  "step2_measure": "T11_mesurer_la_main.png",
  "step3_budget": "",
  "illustration_mouse_dimensions": "T12_souris_longueur_largeur.png"
}
```

| Clé | Affichée à | Illustration livrée |
|---|---|---|
| `banner` | Message persistant d'accueil | `T08_azemouse_banniere.png` |
| `step1_grip` | Étape 1/4 — les 3 prises | `T09_griffe_paume_doigts.png` |
| `step2_thenar` | Étape 2/4 — thénar (informatif) | `T10_tailles_de_main.png` |
| `step2_measure` | Étape 3/4 — main mesurée à la règle | `T11_mesurer_la_main.png` |
| `step3_budget` | Étape 4/4 — facultatif (vide = aucune image). Ancien nom `step4_budget`, encore lu en repli. | *(vide)* |
| `illustration_mouse_dimensions` | Repères de taille du résultat | `T12_souris_longueur_largeur.png` |
| `illustration_rear_narrow` | Résultat, si thénar « Petite » (indicatif) | `T13_arriere_etroit.png` |
| `illustration_grip_relaxed` | Étape « variante de Claw » (illustration générique de l'étape) et résultat quand la variante choisie est « Claw relâchée » | `T04_griffe_relachee.png` |
| `illustration_hump_mid` | Résultat — bosse centrale de la souris retenue, et conseil « bosse au milieu ou à l'avant » (Palm) | `T14_bosse_centrale.png` |
| `illustration_hump_front` | Résultat — bosse avant / Mid-Front de la souris retenue | `T15_bosse_avant.png` |
| `illustration_hump_rear` | Résultat — bosse arrière de la souris retenue, et conseil « bosse au milieu ou à l'arrière » (Claw) | `T07_bosse_arriere.png` |
| `illustration_buttons_high` | Résultat — boutons hauts (souris retenue ou conseil Palm) | `T01_boutons_hauts.png` |
| `illustration_buttons_low` | Résultat — boutons bas (souris retenue ou conseil Claw) | `T02_boutons_bas.png` |
| `illustration_buttons_mid` | Résultat — boutons moyens (souris retenue ou conseil Fingertip) | `T03_boutons_moyens.png` |
| `illustration_grip_aggressive` | Résultat, prise Claw — variante « Claw agressive » | `T05_griffe_agressive.png` |
| `illustration_grip_pincer` | Résultat, prise Claw — variante « Claw pincée » | `T06_griffe_pince.png` |

Les URL doivent être publiques et commencer par `https://`. Une valeur vide ou invalide n'affiche simplement pas d'image.
Les 15 fichiers sont livrés dans `assets/illustrations/` (copie de `ImageUse/`) : il suffit de les publier et de
renseigner `IMAGES_BASE_URL`. Les fichiers Discord (pièces jointes) ne sont pas utilisés : hébergez les images ailleurs.

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
- Sans lien, le résultat affiche **un seul** bouton informatif désactivé `🔗 Liens à venir` (jamais un bouton grisé par souris) ;
  ajoutez simplement l'`id` de la souris pour afficher son bouton 🛒 `Acheter …`.
- Aucun lien n'est inventé dans le dépôt : le fichier est volontairement vide tant que le propriétaire ne fournit pas les liens.
- Les entrées dont l'URL ne commence pas par `http(s)://`, ou qui contient une espace, une tabulation ou un
  caractère de contrôle, sont ignorées **souris par souris** (un avertissement est écrit dans les logs) :
  une telle adresse n'est pas une URL utilisable, et Discord la refuse au moment de l'envoi — ce qui ferait
  échouer **tout** le résultat, pas seulement ce bouton.
- Modification à chaud : rechargé à chaque résultat, sans redémarrage.

---

## Faire enrichir le catalogue par une IA

Le pack de recherche se prépare et s'envoie en trois étapes (détail : `docs/PROMPT_RECHERCHE_SOURIS_ATK.md`) :

```bash
python tools/build_ai_bundle.py     # crée pack_ia_mousediscord.zip (prompt + règles + catalogue + identifiants)
```

1. Joignez `pack_ia_mousediscord.zip`, les **liens YouTube** et vos **captures Discord** à votre message.
2. Copiez le **prompt** du §3 de `docs/PROMPT_RECHERCHE_SOURIS_ATK.md`.
3. À la réponse : collez les fiches dans `data/mouse_db.json`, puis
   `python tools/check_deployment.py` → `pytest -q` → `python tools/compare_profiles.py`.

Le pack ne contient **aucun secret** (ni `.env`, ni `state/`, ni liens d'affiliation) et rappelle les règles du projet :
aucune valeur inventée, prix en euros uniquement s'ils sont documentés en euros, compatibilités « Inconnu » sans source
explicite, deux sources concordantes à ≤ 0.5 mm — ou la boutique officielle du fabricant elle-même —
pour un statut `verified`.

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
| `dimension_status` | `verified` (**deux sources de cotes concordantes à ≤ 0,5 mm, ou une seule quand c'est le fabricant lui-même** — sa boutique officielle, ex. `atk.store`, `eu.pulsar.gg`), `single_source` (une seule source, tierce), `conflicting`, `owner_spec`, `owner_spec_unverified`. |
| `conflicts` | Valeurs divergentes et leurs sources (ex. longueur 118.0 vs 117 mm). |
| `shell_id` | Même coque = dimensions partagées (ex. A9 Ultimate / A9 Air / A9 Plus). Une coque **partagée par plusieurs entrées** cite, sur chacune, la source qui l'atteste (fabricant ou document du projet) ; une coque unique n'a rien à citer. |

**Compatibilité** (valeurs : `Élevé`, `Moyen`, `Faible`, `Inconnu`)

| Champ | Usage |
|---|---|
| `palm_grip_fit`, `claw_grip_fit`, `fingertip_grip_fit` | Compatibilité par grip. `Inconnu` = non vérifié : la souris est mise **à vérifier** (aucun point n'est attribué). |
| `hump_position` | `Front`, `Mid`, `Rear`, `Mid-Front`, `Mid-Rear`, `Any` ou `Inconnu`. |
| `button_height` | `Low`, `Mid`, `High` ou `Inconnu`. |
| `fit_status` | `owner_spec` (cahier des charges, ou coque jumelle de la même forme), `manufacturer_guide` (recommandation écrite du fabricant), `third_party_guide` (recommandation écrite d'une source tierce autorisée — mouseshape.com — pour une prise que le fabricant ne publie pas : jamais « Faible », jamais à la place d'une valeur fabricant) ou `unverified` (tout `Inconnu`). |
| `fit_rationale` | Texte affiché dans le résultat. |

**Commercial** (ne modifie jamais le score géométrique)

| Champ | Usage |
|---|---|
| `price_eur` | Prix en euros. `null` = inconnu : exclu des modes à prix, autorisé en Haut de Gamme et en « Peu importe le prix ». |
| `price_status` | `verified`, `owner_spec_unverified` ou `unknown`. Un prix `verified` exige un prix. |
| `price_note` | Précision (date, devise d'origine…). |
| `budget_tier` | `Économique`, `Qualité-Prix`, `Haut de Gamme` (étiquette, départage visuel uniquement). |
| `weight_g`, `sensor`, `polling_hz` | Caractéristiques documentées. `polling_hz` ≥ 8000 et capteur `PAW3950`/`PAW3955` (variantes) comptent pour le mode Haut de Gamme. |
| `shape` | `Symmetrical` / `Ergonomic` : affichée tout à droite de la ligne du match idéal et de l'alternative (« Symétrique » / « Ergonomique »). |
| `switches`, `mcu` | Switchs et microcontrôleur documentés (`Nordic 54H20`, `54L15`, `54LM20`, `nRF52840`…). Servent au départage du mode « Peu importe le prix » : capteur > MCU > switchs > fréquence. Un champ vide n'est jamais deviné. |
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
| Boutons | Palm : High · Claw : Low · Fingertip : Low ou Mid | 5 · 5 · 10 |

Les règles de bosse et de boutons sont centralisées dans `HUMP_IDEAL` et `BUTTON_IDEAL` (`utils/matcher.py`).
Règle des boutons, mot pour mot identique dans les quatre documents normatifs (vérifiée par
`tests/test_doc_references.py`) : `Palm → {High} · Claw → {Low} · Fingertip → {Low, Mid}` — `High` en Palm, `Low` en Claw, `Low` ou `Mid` en Fingertip.

**Affichage** : `Score de correspondance : X/40 — Y % du maximum théorique du barème`, où `Y = X / 40 × 100` arrondi à l'entier (demi vers le haut).
Le pourcentage n'est jamais présenté comme une probabilité.

**Statuts**

- `excluded` : longueur > 8 mm hors plage, largeur de prise > 5 mm hors plage, grip « Faible », prix > budget (mode budget personnalisé).
- `pending` : aucune exclusion, mais grip, bosse, boutons ou longueur `Inconnu` / en conflit. Le score partiel est affiché, jamais classé.
- `scored` : toutes les données présentes.

**Forme de coque** : `shape` (`Symmetrical` / `Ergonomic`) est renseignée pour les **36 souris** (26 le 2026-10-11,
plus 10 Pulsar le 2026-10-12), chacune sourcée (fiche ATK/VXE/Pulsar, EloShapes, test indépendant) — jamais devinée. Elle sert au bloc « ⛰️ La bosse et la forme » :
une forme symétrique convient aux trois prises, une ergonomique épouse un peu mieux l'arche de la main en Palm.
En Claw, la **variante déclarée** précise la bosse attendue (relâchée → arrière marquée, agressive → médiane,
pincée → arrière à flancs plats) : conseil d'affichage uniquement, aucun point ni classement ne change.

**Niveau de confiance** (calculé, **non affiché**) : `élevée` si dimensions vérifiées et largeur de prise mesurée ;
`moyenne` si dimensions vérifiées mais largeur estimée ; `faible` sinon (dimensions d'une seule source, non
vérifiées, ou compatibilité non confirmée). Il mesure la solidité des **données**, pas la qualité de la souris :
il reste dans `MouseScore.confidence` et n'apparaît plus dans le résultat (décision du propriétaire, 2026-10-11).

**Modes de sélection** (`utils/selection.py`) — tolérances **provisoires**, à valider :

| Mode | Zone (écart au meilleur score) | Critère dans la zone |
|---|---|---|
| Économique | ≤ 5 pts | prix le plus bas |
| Rapport Qualité/Prix | ≤ 2 pts | points par euro le plus élevé (indicateur provisoire) |
| Haut de Gamme | ≤ 2 pts | performance **documentée** (polling ≥ 8000 Hz, capteur PAW3950/PAW3955 : 0 à 2) ; le prix n'entre pas |
| Peu importe le prix | ≤ 2 pts | **forme d'abord** : meilleur score, puis composants documentés (capteur > MCU > switchs > fréquence), puis le moins cher ; le prix ne compte jamais |
| Budget Personnalisé | ≤ 2 pts, parmi les souris ≤ budget | meilleur score, puis le moins cher |

Les souris sans prix connu ne sont jamais recommandées dans les modes à prix : elles passent dans « À vérifier ».
Une donnée de performance absente compte pour zéro ; cela ne signifie pas une performance inférieure.

**Valeurs de non-régression du moteur** (main 180 × 90 mm, Palm ; plages 118.8–123.8 mm et 55.6–59.6 mm) :
elles sont figées par `tests/test_matcher.py` et ne doivent jamais bouger sans décision explicite.

| Souris | Résultat | Détail |
|---|---|---|
| Scyrox V6 | **30** | longueur 10 · largeur 10 · grip Moyen 5 · bosse Mid 5 · boutons Mid 0 |
| ATK Z1 V2 Ultimate | **30** | longueur 10 · largeur 0 (écart 4.2 mm, zone 2–5 mm) · grip 10 · bosse Mid-Front 5 · boutons High 5 |
| ATK A9 Plus | **25** | longueur 5 · largeur 5 · grip Élevé 10 · bosse Mid 5 · boutons 0 |
| ATK X1 V2 Ultra Max 2.0 | **20** | longueur 0 (écart 3.2 mm) · largeur 5 · grip 10 · bosse 5 · boutons 0 |
| Scyrox V8 / V8S, ATK F1 V3 | exclues | grip Palm « Faible » |

**Réponse réelle du bot pour ce profil** : en *Rapport Qualité/Prix*, match idéal **ATK Phantom Ultimate**
(35/40 — 88 %, 91,95 €), alternative **ATK Z1 V2 Ultimate** (30/40 — 75 %, 59,95 €) et, en troisième ligne,
**ATK A9 Mini** (30/40 — 75 %, 59,95 €) sous le titre « ➕ L'autre option » — au même prix que l'alternative,
elle n'est pas une économie et ne s'annonce donc pas comme telle ; le gagnant dépend du mode
(en *Économique*, la Z1 V2 Ultimate passe devant, parce qu'elle est la moins chère de la fenêtre). Ce résultat est
vérifié par `tests/test_flow.py` ; le classement des cinq modes, pour les trois profils de référence, est dans
la matrice ci-dessous — c'est elle qui fait foi, pas ce paragraphe.

**Matrices complètes** (profils Palm, Claw, Fingertip, toutes les souris du catalogue, les deux places
affichées par mode) : `docs/audit/matrice_profils.md`, générées par `python tools/compare_profiles.py`.
Chaque mode y est calculé **comme dans le bot** (le plafond du mode budget ne s'applique qu'à sa propre
ligne) ; `tests/test_compare_profiles.py` le vérifie.

---

## Architecture

```
MouseDiscord/
├── bot.py                    # Point d'entrée : composants durables enregistrés, sessions, purge périodique
├── config.py                 # Variables d'environnement et chemins
├── cogs/
│   ├── mouse_finder.py       # !setup_finder (idempotent, verrouillage du salon)
│   └── finder_flow.py        # Vues, menus, modals, embeds, flux 1/4 à 4/4 et résultat en 2 embeds
├── utils/
│   ├── matcher.py            # Compatibilité morphologique (points, statuts, largeur de prise)
│   ├── selection.py          # Modes de sélection (tolérances, classement, explications)
│   ├── models.py             # Grip, BudgetMode, Mouse, Source, HandMeasure
│   ├── catalog.py            # Chargement / validation de mouse_db.json et des liens
│   ├── assets.py             # Lecture de assets/images.json
│   ├── session.py            # Parcours : rattachement au membre, TTL, reprise après redémarrage (state/sessions.json)
│   └── validation.py         # Validation des saisies des modals
├── data/
│   ├── mouse_db.json         # Catalogue v2 (géométrie + sources, compatibilité, prix)
│   └── commercial_links.json # Liens d'achat (36/36 fournis et vérifiés ; les clés _ sont de la documentation)
├── assets/
│   ├── images.json           # Clé -> nom de fichier (résolu par IMAGES_BASE_URL) ou URL https complète
│   └── illustrations/        # Les 15 assets ImageUse (T01–T15), à publier en https (voir REPORTE_DESIGN.md)
├── tools/
│   ├── check_deployment.py   # Contrôle de déploiement (fichiers, token, JSON, state/) — sans afficher le token
│   ├── check_links.py        # Chaque lien d'achat ouvre-t-il le modèle ET le prix publiés ? (réseau requis)
│   │                         #   code 0 cohérent · 1 écart · 2 rien n'a pu être vérifié (réseau bloqué)
│   ├── build_mouse_db.py     # Génère le catalogue v2 à partir des données sourcées
│   ├── build_ai_bundle.py    # Prépare le pack (prompt + règles + catalogue) pour une IA de recherche
│   ├── measure_grip_width.py # Largeur de prise en mm depuis une capture vue de dessus (méthode Oblivity)
│   ├── measure_button_height.py # Classe de hauteur des boutons depuis une vue de côté (vue en perspective refusée)
│   ├── image_corpus_check.py # Doublons d'un corpus d'images : une photo = une identité (sinon mesure refusée)
│   ├── image_identity_check.py # Rattache une image SANS nom à une image nommée (comparaison de silhouette)
│   ├── qa_flow_matrix.py     # Banc d'essai du parcours : toute la grille de profils passe par le moteur
│   ├── flow_effect.py        # Effet d'une modification du CODE des trois places : avant/après mesuré
│   ├── db_effect.py          # Effet d'une modification des DONNÉES : deux catalogues, mêmes profils
│   │                         #   (--retrait : mesure aussi le retrait de souris, catalogue réduit)
│   ├── recommendation_stats.py # Combien de fois chaque souris est recommandée (rapport dans docs/audit/)
│   ├── render_preview.py     # Aperçu PNG du parcours, du résultat et du prix libre (+ empreinte des sources)
│   ├── privacy_scan.py       # Contrôle statique de confidentialité (0 violation attendue)
│   └── compare_profiles.py   # Génère docs/audit/matrice_profils.md
├── docs/
│   ├── DEPLOYMENT_ALWAYSDATA_FILEZILLA.md  # Guide de mise en ligne (Alwaysdata, FileZilla, illustrations)
│   ├── REPORTE_DESIGN.md     # Charte AzeMouse : assets, mapping image -> écran, hébergement
│   ├── LISTE_LIENS_SPONSORISES_2026-10-11.md  # Les liens d'affiliation, un par un (relevé initial)
│   ├── VERIFICATION_LIENS_SPONSORISES_2026-10-11.md  # Relecture page par page des liens et des prix
│   └── audit/                # Audit, catalogue ATK, matrices, statistiques, campagne EloShapes
│                             #   (dont ELOSHAPES_2026-10-12.md)
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
python tools/qa_flow_matrix.py       # banc d'essai du parcours (27 170 profils, 0 problème attendu)
python tools/qa_flow_matrix.py --rapide   # même banc, grille réduite (720 profils)
python tools/flow_effect.py          # effet d'une modification du CODE des trois places (avant/après)
python tools/db_effect.py --avant ancien_mouse_db.json   # effet d'une modification des DONNÉES
python tools/db_effect.py --avant data/mouse_db.json --apres catalogue_reduit.json --retrait  # retrait de souris
python tools/image_corpus_check.py  # doublons d'un corpus d'images (identité vérifiable avant mesure)
python tools/image_identity_check.py --reference IMG --candidate IMG  # même coque ? (silhouettes)
python tools/recommendation_stats.py # régénère docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md
python tools/render_preview.py       # régénère les trois aperçus livrés (docs/apercu_*.png)
python tools/render_preview.py --sortie-dossier /tmp/apercus   # les rend sans toucher aux fichiers livrés
python tools/measure_button_height.py IMG --length-mm 122.5 --height-mm 42.4   # classe de hauteur des boutons
python tools/measure_grip_width.py IMG --length 118.2   # largeur au capteur (méthode Oblivity)
python tools/build_mouse_db.py       # traçabilité du premier relevé — refuse d'écraser le catalogue réel
```

- `tests/test_matcher.py` : plages cibles, points pour 180 × 90 mm en Palm (non-régression), bornes strictes, largeur mesurée vs estimée, statuts `scored` / `pending` / `excluded`, budget personnalisé.
- `tests/test_selection.py` : effet réel de chaque mode, tolérances, prix inconnus, candidats à vérifier jamais classés.
- `tests/test_catalog_lookup.py` et `tests/test_data.py` : schéma v2, validation des erreurs (**dont 14 valeurs numériques hostiles** — `NaN`, infini, booléen, poids en texte — et un lien à espace, refusés au chargement), absence de valeur inventée, liens et images, résolution `IMAGES_BASE_URL` (nom de fichier), existence réelle des 15 illustrations, repli de clé d'image.
- `tests/test_validation.py` : saisies valides, invalides et hors bornes des modals.
- `tests/test_session.py` : rattachement au membre, remplacement d'un parcours, expiration, enregistrement/relecture du fichier d'état, et **14 contenus de fichier d'état hostiles** (tronqué, version inconnue, dossier à la place du fichier, âge négatif…) qui ne doivent jamais empêcher le bot de démarrer.
- `tests/test_privacy.py` : scénarios de confidentialité et de robustesse **P02–P18** (parcours complet, deux utilisateurs simultanés, intrus, expiration, redémarrage, clic rejoué, erreur inattendue, fichier d'état) — voir `docs/audit/AUDIT_CONFIDENTIALITE.md` et `docs/audit/ROBUSTESSE_2026-10-12.md`.
- `tests/test_bot_runtime.py` : comportements de `bot.py` mesurés le 2026-10-13 (couverture de `bot.py` : 67 % → **100 %**, lignes de script comprises, démarrage rejoué deux fois) — purge périodique des parcours expirés (et son silence quand rien n'a expiré), erreur d'événement journalisée sans arrêter le bot, commande inconnue totalement muette, erreur de commande tracée sans rien publier, message de connexion, démarrage refusé sans jeton.
- `tests/test_privacy_scan.py` : contrôle statique `tools/privacy_scan.py` (envois non éphémères, éditions hors fonctions autorisées, alias, appels dynamiques) : cas valides, violations injectées, dépôt réel.
- `tests/test_apercus.py` : **les trois aperçus PNG doivent être de la même date que les données qu'ils montrent** — chaque image porte dans ses métadonnées une empreinte du catalogue, des liens, des images et des modules qui composent le message ; un aperçu périmé (celui du mode « Peu importe le prix » montrait encore un ancien nom de modèle) est refusé avec la commande à relancer.
- `tests/test_doc_references.py` : chemins cités dans la documentation existants, titres de section exacts, et **renvois « fichier + §numéro » valides** (aucune citation ne doit pointer vers une section qui n'existe pas) — y compris dans les **données** (`data/*.json`), où une note de prix renvoyait à une section qui n'a jamais existé. Depuis le 2026-10-14, les numéros cités **sans nom de fichier** sont vérifiés eux aussi, sur les trois plages sans ambiguïté du dépôt : `§19.x` à `§26.x` → ROBUSTESSE, `§12.x` → guide de déploiement, `C##` → AUDIT — quatre renvois vers la section « 21.6 », qui n'existe pas depuis la renumérotation de la 33e passe, dormaient dans le document de robustesse.
- `tests/test_config.py` : chemins indépendants du répertoire courant, entiers invalides signalés clairement, et **`.env.example`** qui doit documenter toutes les variables lues par `config.py` (chacune expliquée sur la ligne juste au-dessus, dont le `FINDER_CHANNEL_ID=0` = « le salon où la commande est tapée »).
- `tests/test_deployment_check.py` : diagnostics de `tools/check_deployment.py` sur un projet factice (dont `IMAGES_BASE_URL` et illustrations manquantes).
- `tests/test_ai_bundle.py` : contenu du pack IA (`tools/build_ai_bundle.py`) — fichiers attendus, **aucun secret** (`.env`, `state/`, liens d'affiliation), liste des identifiants existants.
- `tests/test_flow.py` : parcours complet 1/4 à 4/4 avec interactions simulées (édition de message, erreurs de saisie, affichage du score, section « à vérifier »), charte d'embeds, limites Discord des embeds, refus des détails internes (`pts`), thénar stocké mais sans effet sur le score, illustrations branchées, lien manquant → « Liens à venir ».
- `tests/test_code_hygiene.py` : hygiène du code livré — aucun résidu de guillemets (le défaut trouvé le
  2026-10-12, invisible à la compilation), aucun `print` dans le bot (il ne laisserait aucune trace dans
  `~/admin/logs/jobs/`), et le contrôle porte bien sur tout le code livré. Depuis le 2026-10-13, il refuse
  aussi **tout test du dépôt qui ne vérifie rien** (relevé par analyse syntaxique : `assert`, `raises`, méthode
  d'assertion, `fail(`) — un test creux trouvé dans `tests/test_flow.py` a été renforcé, et la contre-épreuve
  du contrôle s'écrit sur un fichier temporaire.
- `tests/test_textes_des_cartes.py` : **les textes variables des cartes sont mesurés, bornés et jamais coupés** — la justification du choix comme le sommaire morphologique, la ligne « en clair » et le résumé du parcours, sur la
  grille resserrée (420 profils) comme sur un pire cas construit (libellé le plus long du catalogue, meilleur
  score, zone la plus large) ; la phrase connue la plus longue fait 320 caractères sur les 18 522 profils de la
  grille complète, la coupe de 1 024 n'a donc jamais mordu, et le message réel doit porter la phrase **entière**.
- `tests/test_reverse_engineering.py` : **le moteur est-il encore celui de la preuve primaire ?** Les **10
  sorties datées de `Reverse/`** (l'outil d'origine, trois prises × trois tailles de main) sont relues par les
  tests : plages cibles au dixième de millimètre, règles de bosse et de hauteur des boutons, conseil de bosse
  des trois variantes de Claw, arrière étroit et méthode de mesure de la largeur. La règle du thénar garde son
  **écart assumé et daté** (l'outil d'origine conseille l'arrière étroit au thénar petit *et* moyen ; le bot le
  réserve à « Petite », comme le prescrit `docs/MASTER_PROMPT_AZEMOUSE.md` §7.6 — le test refuse que l'un des
  deux bouge sans l'autre).
- `tests/test_data.py` (suite) : **invariants de coque** — deux souris dont les trois cotes publiées sont
  identiques (au dixième : longueur, largeur maximale, hauteur) ne peuvent pas être deux coques : neuf
  groupes de jumelles au catalogue, dont un (ATK Blazing Sky U2 / U2 V2 Ultimate) est resté sans `shell_id`
  jusqu'au 2026-10-14 : **235 profils sur 27 170 (0,86 %)** montraient alors les deux dans le même résultat
  (207 sur les 18 522 du rapport) et **175 (0,64 %)** changent de résultat après l'enregistrement de la
  coque — contre la règle « deux places ne montrent jamais la même coque ». Deux profils réels tiennent les
  deux sens de la règle : la préférence de coque quand une autre coque passe sous le plafond, le repli quand
  il n'y en a aucune. Cotes identiques et coques distinctes ne passent que si l'écart est **consigné** dans
  `conflicts` — un silence n'est jamais une preuve.
- `tests/test_db_effect.py` : le comparateur de données (`tools/db_effect.py`) prouve dans les deux sens —
  deux catalogues identiques ne produisent aucun écart, un prix modifié en produit, et deux catalogues qui
  ne contiennent pas les mêmes souris sont refusés au lieu d'être comparés. Une **simulation de retrait**
  (`--retrait`, catalogue après = sous-ensemble) est mesurée — quelles places les souris sorties
  occupaient, et laquelle des souris restantes reprend la place — tandis qu'un catalogue **enrichi** reste
  refusé dans tous les cas.
- `tests/test_flow_effect.py` : le mesureur d'effet du parcours recharge la version antérieure du code (`git show`) et refuse une référence inconnue avec un message lisible, sans trace Python.
- `tests/test_donnees_a_chaud.py` : **les fichiers de données sont relus à chaque appel** — le catalogue, les liens commerciaux et le calcul lui-même (une souris ajoutée ou renommée dans `data/mouse_db.json` apparaît au parcours suivant, sans redémarrer le bot). C'est la promesse du guide de déploiement, tenue par trois tests : un cache ajouté dans un chargeur, ou une lecture sortie de `compute_selection`, les fait rougir.
- `tests/test_catalog_hardening.py` : catalogue hostile (valeurs numériques, booléens, listes, dictionnaires, chaînes) refusé au chargement avec un message clair, jamais au milieu d'une réponse d'interaction.
- `tests/test_build_mouse_db_guard.py` : garde-fou du générateur (`tools/build_mouse_db.py`) — il refuse d'écraser le catalogue réel et n'écrit qu'avec `--force`, en une seule fois.
- `tests/test_doc_coherence.py` : chaque pourcentage des documents doit correspondre à l'ensemble cité (« N sur M ») — le contrôle qui a rattrapé C48, limites comprises.
- `tests/test_tools_usage_errors.py` : **le contrat d'erreur des quinze outils** (phrase sur la sortie d'erreur, code 2, jamais de trace Python), leur aide, et l'invariant `main(argv=None)` qui rend ce contrôle possible — c'est lui qui a rattrapé C50 ; il garde aussi les **deux artefacts générés** (le rapport statistique doit être celui de la grille complète, la matrice des profils doit correspondre au script relancé).
- `tests/test_image_corpus_check.py` : les groupes de doublons d'un corpus d'images (une même photo circulait sous huit noms de modèles) sont signalés, les fichiers non-image ignorés.
- `tests/test_image_identity_check.py` : rattachement d'une image sans nom imprimé à une image nommée par sa silhouette (mise dans le même sens, deux verdicts bornés, refus de trancher).
- `tests/test_measure_button_height.py` : mesure exacte sur une vue orthographique synthétique, classe estimée par les références étalonnées, et vue en perspective **refusée** (aucune valeur produite).
- `tests/test_measure_grip_width.py` : largeur au capteur depuis une vue de dessus, précision et cas limites.
- `tests/test_qa_flow_matrix.py` : garde-fous du banc d'essai lui-même (lecture des places **par rôle**, libellés des trois lignes, comptage des places au prix non attesté) — un banc qui se trompe de rôle produit des milliers d'alertes fantômes.
- `tests/test_setup_command.py` : publication, édition sans doublon, message supprimé, autre salon, fichier d'état corrompu.
- `tests/test_liens_achat.py` : **les 36 liens d'achat ouverts un par un** — le tableau §8.1 de
  `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` est relu contre `data/commercial_links.json` (handle
  et variante figée) et `data/mouse_db.json` (prix publié), dans les deux sens ; une note qui annonce
  « la variante que le bouton ouvre » exige un lien qui la fige ; la **liste de travail**
  (`docs/LISTE_LIENS_SPONSORISES_2026-10-11.md`) doit envoyer sur la page que le bouton ouvre, pas sur
  l'ancienne (deux lignes y renvoyaient encore le 2026-10-13) ; et `tools/check_links.py` est essayé hors
  réseau sur une fausse boutique (cohérent, variante disparue, prix changé, fiche en dollars, réseau
  bloqué) — c'est ce test qui a rattrapé le statut composé mal reconnu.

**Ce que les tests ne couvrent pas** : une vraie connexion Discord. Les vérifications suivantes doivent être faites à la main
(voir `docs/audit/RAPPORT_FINAL.md`, §8 « Vérifications Discord manuelles (non exécutées) », le protocole `docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md` et la liste de contrôle `docs/audit/ROBUSTESSE_2026-10-12.md` §4) : isolation des sessions entre deux utilisateurs,
interactions expirées, **reprise d'un parcours après un redémarrage réel du bot**, double appui sur le dernier menu,
absence d'accumulation de messages, permissions limitées au salon.

---

