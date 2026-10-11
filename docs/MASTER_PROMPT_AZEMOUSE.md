# MASTER PROMPT — AZEMOUSE DISCORD BOT
## Refonte esthétique fidèle à l'identité AzeMouse, amélioration UX et préservation intégrale du moteur

**Version :** 1.0 — 2026-10-11 (Europe/Paris)  
**Branche de travail :** `arena/9ddacf48-mousediscord` (fork de `arena/33e33710-mousediscord`, commit de base `2191feec`)  
**Dépôt :** `francoiseargaud43-source/MouseDiscord`  
**Rôle de l'agent destinataire :** IA codeur Python `discord.py` — tu travailles sur un **logiciel existant, fonctionnel, à améliorer visuellement**, pas à reconstruire.  
**Contrainte absolue :** Ne pas créer d'application Web indépendante. Le livrable reste un bot Discord natif.

---

## 1. CONTEXTE ET OBJECTIF PREMIER

### 1.1 Ce qu'est AzeMouse
Bot Discord qui recommande une souris gaming (catalogue ATK/Scyrox) selon :
- **Mesures de la main** : longueur (pli du poignet → bout du majeur) et largeur sans pouce (au niveau des articulations), en mm.
- **Grip** : Palm, Claw, Fingertip.
- **Géométrie de la souris** : longueur, largeur de prise (coque ou mesurée), position de la bosse, hauteur des boutons, compatibilité de grip.
- **Budget / gamme** : Économique, Qualité-Prix, Haut de Gamme, **Peu importe le prix** (forme d'abord, ajouté le 2026-10-11), Budget Personnalisé Maximal (prix max en €).

Parcours 100% Discord natif : panneau d'accueil public → parcours éphémère (un seul message qui se met à jour) → résultat privé → boutons d'achat / Fermer / Refaire le test.

### 1.2 Objectif de la mission actuelle
**Améliorer la présentation visuelle et l'UX, tout en conservant les calculs, données, protections et fonctionnalités validées.**

Priorités, dans l'ordre :
1. **Identité visuelle AzeMouse** reconnaissable, sombre, élégante, premium.
2. **Intégration correcte des 15 assets** fournis dans `ImageUse/`.
3. **Allègement et hiérarchisation de l'embed de résultat** (actuellement surchargé).
4. **Cohérence de tout le parcours** (bannière → 3/4 étapes → résultat).
5. **Zéro régression fonctionnelle** : formules, seuils, scores, statuts, prix, confidentialité.
6. Documentation et tests mis à jour.

> Toute modification fonctionnelle non indispensable au design doit être listée séparément, justifiée et validée.

### 1.3 Ce qui est déjà fonctionnel et à PRESERVER tel quel
- `utils/matcher.py` : plages cibles, barème 40 pts, statuts `scored`/`pending`/`excluded`, largeur mesurée vs estimée.
- `utils/selection.py` : tolérances par mode, classement, `pending` jamais classé.
- `utils/catalog.py` : validation stricte du catalogue v2, `commercial_links.json` séparé.
- `utils/session.py` : isolation par `session_id` aléatoire + `user_id`, TTL 30 min, discard à l'affichage du résultat.
- `utils/validation.py` : bornes 100–260 mm (longueur), 50–130 mm (largeur), 10–5000 € (budget), parsing tolérant (virgule/point, `mm`/`€`).
- `utils/assets.py` : lecture à chaud de `assets/images.json`, repli `step4_budget`→`step3_budget`.
- `cogs/finder_flow.py` & `cogs/mouse_finder.py` : vues persistantes, modals, ephemerals, `!setup_finder` idempotent.
- Tests : 200+ tests couvrent matcher, selection, sessions, confidentialité, flow simulé, etc. (cf. §13).

**Interdiction :** ne réécris pas le moteur pour « faire plus joli ». **Sépare calcul et présentation.**

---

## 2. INVENTAIRE TECHNIQUE — CE QUE TU DOIS LIRE EN PREMIER

Avant d'écrire une ligne, inspecte (dans cet ordre) :

1. `README.md` (§ Fonctionnement, Personnaliser les images, Modifier les liens, Modifier le catalogue, Moteur de scoring, Architecture, Tests).
2. `config.py` (chemins `MOUSE_DB_PATH`, `COMMERCIAL_LINKS_PATH`, `IMAGES_CONFIG_PATH`, `FINDER_STATE_PATH`, variables d'env).
3. `utils/models.py` (`Grip`, `BudgetMode`, `Mouse`, `Source`, `HandMeasure`).
4. `utils/matcher.py` (constantes d'équations, barème, `evaluate_mouse`, `compute_target_ranges`).
5. `utils/selection.py` (tolérances, `performance_index`, `select`).
6. `utils/catalog.py` + `data/mouse_db.json` + `data/commercial_links.json`.
7. `utils/assets.py` + `assets/images.json`.
8. `utils/session.py` + `utils/validation.py`.
9. `cogs/finder_flow.py` (TOUT le flux) + `cogs/mouse_finder.py` + `bot.py`.
10. `docs/audit/AUDIT.md`, `RAPPORT_FINAL.md`, `CATALOGUE_ATK.md`, `matrice_profils.md` (matrices générées par `tools/compare_profiles.py`).
11. `tools/compare_profiles.py`, `tools/build_mouse_db.py`, `tools/check_deployment.py`, `tools/privacy_scan.py`.
12. `tests/` (surtout `test_matcher.py`, `test_selection.py`, `test_flow.py`, `test_privacy.py`).

Exécute sans toucher au code :
```bash
pip install -r requirements-dev.txt
pytest -q
python -m pyflakes bot.py config.py cogs utils tests tools
python tools/compare_profiles.py  # régénère docs/audit/matrice_profils.md — ne pas commit si inchangé
python tools/privacy_scan.py
```

---

## 3. LES TROIS DOSSIERS D'IMAGES — RÈGLE DE CORRESPONDANCE OBLIGATOIRE

### 3.1 Inventaire réel (à vérifier sur disque, ne présume rien)

**`ImageAct/` — 7 captures de l'interface ACTUELLE (état à corriger)**
| Fichier | Contenu observé | Problème mis en évidence |
|---|---|---|
| `Capture d'écran 2026-10-11 111832.png` | Étape 3/3 Budget (menu fermé, récap Grip + Main) | Absence d'image `step3_budget`, fond bleu Discord générique, texte sec |
| `Capture d'écran 2026-10-11 111848.png` | Même étape, menu Budget ouvert (Économique, Qualité/Prix, Haut de Gamme, Budget Perso) | Libellés longs, hiérarchie faible |
| `Capture d'écran 2026-10-11 111859.png` | Étape 1/3 Grip (texte Palm/Claw/Fingertip) — clé `step1_grip` vide | Aucune illustration des grips → incompréhensible pour un novice |
| `Capture d'écran 2026-10-11 111906.png` | Modal « Mesure de votre main » (2 TextInput) | Correct fonctionnellement, mais pas d'aide visuelle dans l'embed parent |
| `Capture d'écran 2026-10-11 111924.png` | Étape 2/3 Mesure (texte + bouton « Saisir mes mesures ») | `step2_measure` vide → pas de schéma main/règle |
| `Capture d'écran 2026-10-11 111932.png` | Variante 2/3 (même) | Idem |
| `Capture d'écran 2026-10-11 111947.png` | **Résultat complet** (Claw 200×110, Haut de Gamme) — Le Match Idéal ATK X1 V2 Ultra Max 40/40, Alternative A9 Plus 40/40, Puis « Pourquoi ce choix ? », puis liste « À vérifier (non classées) » de 10+ lignes, puis footer disclaimer, puis 3 boutons | **Embed monolithique** : 5 niveaux de détails mélangés, `Longueur 127.0 mm vs cible … : 10 pts` visible pour l'utilisateur, liste pendings interminable, 2 scores 100% identiques peu différenciés, pas de hiérarchie visuelle |

> Utilise `ImageAct` uniquement pour comprendre l'existant et lister les défauts. Ne reproduis pas ces captures à l'identique en changeant juste la couleur latérale.

**`ImageEx/` — 9 références de design (INSPIRATION, pas assets à copier tels quels)**

| Fichier | Référence | Ce qu'elle enseigne (à transposer en composants Discord) |
|---|---|---|
| `…111122.png` | **Oblivity** — bannière « mouse finder by oblivty » sur fond sombre avec 5 souris | Direction artistique sombre premium, bannière large, titre + pill bordeaux, typo Syne |
| `…111138.png` | Choose Your Grip Style — 3 mains blanches sur fond sombre, pills « Claw / Palm / Fingertip » | Présentation triptyque, fond Crème vs Nuit, pill bordeaux |
| `…111151.png` | Select Your Thenar Muscle Size — 3 mains avec thénar pointillé jaune | Idée du **thénar informatif** (Small/Medium/Large) — à reprendre avec `T10` si l'étape est conservée |
| `…111213.png` | Breakdown Fingertip 180×90 — « Your Profile », « Mouse Size » (Longueur max 123.8, Largeur 54.5–58.4) + schéma souris + « Button Height : Mid Buttons / Low Buttons » | **Structure du résultat en cartes séparées** : Profil → Taille cible → Hump → Boutons → Design. Chaque carte a un titre, un texte court, une illustration. À reproduire avec 2–3 embeds/fields, pas un seul bloc |
| `…111455.png` | Mouse Size Recommendation Palm 180×100 — Optimal Length 118.8–123.8, Width 56.4–60.4 + Rear Design Narrow Rear + Hump Placement Mid-to-Front + Button Height Elevated + Mouse Design | Même principe : **une section = une idée**. Schémas line art jaune/bordeaux sur fond sombre |
| `…111510.png` | Profil Claw 180×90 — Mouse Size 118.8–123.8 / 55.6–59.6 + Rear Design + Hump Mid-to-Back | Variante Claw : bosse Mid-to-Back (adaptée à l'arche transverse palmaire) |
| `…111526.png` | How to Measure Your Hand — mains avec règle, pills Length/Width | Inspiration pour **T11** : longueur = pli poignet→majeur, largeur = articulations sans pouce |
| `…111545.png` | Claw Grip Variants — Relaxed / Aggressive / Pincer (photos) + Rear Hump, Button Low | **Déclinaison Claw** à expliquer visuellement — correspond exactement à `T04/T05/T06` |
| `…111609.png` | Complement Claw — même variantes + explications | Idem |

**Leçons communes `ImageEx` :**
- Fond global très sombre (`#070B14` / `#0B1220`), cartes avec fin liseré rouge/bordeaux à gauche.
- Peu de couleurs : noir + blanc cassé + bordeaux + jaune pointillé. Jamais d'arc-en-ciel.
- Titres courts, textes en 2–3 lignes max, schémas explicatifs.
- **Ne tente pas de recréer ces cartes en HTML/CSS dans Discord.** Transpose le **principe** : 1 embed = 1 intention, fields courts, images d'illustration hébergées.

**`ImageUse/` — 15 assets À INTÉGRER (ressources finales, à héberger en https)**

| # | Fichier réel | Visuel | Rôle prévu (à confirmer visuellement avant codage) | Proposition de clé `assets/images.json` |
|---|---|---|---|---|
| T08 | `T08_azemouse_banniere.png` | Photo 5 souris fond nuit, « AzeMouse » Syne ExtraBold crème, pill bordeaux « by aze129 » Fraunces | **Bannière d'accueil** (message persistant) | `banner` (existe) |
| T09 | `T09_griffe_paume_doigts.png` | 3 mains line art : Griffe / Paume / Bout des doigts, pills bordeaux, typo Syne | **Étape 1/3 — Grip** : les 3 grips | `step1_grip` (existe, remplacer URL vide) |
| T11 | `T11_mesurer_la_main.png` | 2 mains + règles : Longueur (poignet→majeur) / Largeur (articulations sans pouce) | **Étape 2/3 — Mesures** | `step2_measure` (existe) |
| T10 | `T10_tailles_de_main.png` | 3 mains avec zones thénar pointillées jaune : Petite / Moyenne / Grande | **Étape thénar informative** (si conservée) | **Nouvelle** `step2_thenar` |
| T12 | `T12_souris_longueur_largeur.png` | Vue de dessus souris, croix jaune Longueur/Largeur | **Aide « Mouse Size »** dans résultat (rappel cible Largeur/Longueur) | **Nouvelle** `illustration_mouse_dimensions` |
| T01 | `T01_boutons_hauts.png` | Profil souris, bouton incliné haut en jaune, pointillé gris | **Boutons hauts** | **Nouvelle** `illustration_buttons_high` |
| T02 | `T02_boutons_bas.png` | Profil souris, bouton bas jaune | **Boutons bas** | **Nouvelle** `illustration_buttons_low` |
| T03 | `T03_boutons_moyens.png` | Profil souris, bouton moyen jaune | **Boutons moyens** | **Nouvelle** `illustration_buttons_mid` |
| T07 | `T07_bosse_arriere.png` | Profil souris, bosse arrière jaune désaxée | **Bosse arrière (Rear)** | **Nouvelle** `illustration_hump_rear` |
| T14 | `T14_bosse_centrale.png` | Profil souris, bosse centrale jaune | **Bosse centrale (Mid)** | **Nouvelle** `illustration_hump_mid` |
| T15 | `T15_bosse_avant.png` | Profil souris, bosse avant jaune | **Bosse avant (Front / Mid-Front)** | **Nouvelle** `illustration_hump_front` |
| T13 | `T13_arriere_etroit.png` | Vue de dessous souris, arrière étroit jaune | **Arrière étroit (Narrow Rear)** — lien avec thénar Small | **Nouvelle** `illustration_rear_narrow` |
| T04 | `T04_griffe_relachee.png` | Photo main « Relaxed Claw Grip » + contour jaune | **Claw variante : relâchée** | **Nouvelle** `illustration_grip_relaxed` |
| T05 | `T05_griffe_agressive.png` | Photo main « Aggressive Claw Grip » | **Claw variante : agressive** | **Nouvelle** `illustration_grip_aggressive` |
| T06 | `T06_griffe_pince.png` | Photo main « Pincer Claw Grip » | **Claw variante : pince** | **Nouvelle** `illustration_grip_pincer` |

> **Règle d'or :** Aucune image ne doit être associée arbitrairement. Tu dois ouvrir chaque fichier, confirmer son contenu, puis l'assigner à l'étape/composant où son **sujet** est cité. La table ci-dessus est la correspondance attendue après vérification visuelle (toutes les images ont été auditées le 2026-10-11). Si une clé n'a pas d'URL, l'embed n'affiche simplement pas d'image (comportement actuel de `_image()`).

### 3.2 Ce que tu dois faire des trois dossiers

| Dossier | Rôle | Ce que tu fais |
|---|---|---|
| `ImageAct/` | Vérité terrain actuelle | Tu listes les défauts (embed surchargé, manque d'images, hiérarchie faible, blurple générique, détails internes exposés, pending list interminable) |
| `ImageEx/` | Horizon qualitatif | Tu extrais les **principes** (sombre premium, pills bordeaux, jaune avec parcimonie, cartes courtes, schémas line art) et tu les **transposes** en embeds Discord (pas en site web) |
| `ImageUse/` | Assets de production | Tu héberges chaque `T0*.png` en `https://` (hébergeur public au choix du propriétaire, ex. `cdn.aze.mouse` ou Imgur, mais **une seule source stable**), tu renseignes `assets/images.json`, tu étends `IMAGE_KEYS` et `LEGACY_KEYS` si besoin, et tu branches chaque URL au bon embed via `_image()` ou `embed.set_image()` |

---

## 4. CHARTE GRAPHIQUE OFFICIELLE AZEMOUSE

### 4.1 Philosophie
> « Un système, pas un arc-en-ciel. On n'utilise jamais les cinq couleurs à parts égales. On choisit une association, on garde le jaune précieux. »

- **Sombre, maîtrisé, premium, reconnaissable.**
- Le **jaune est un highlight** (1–2 touches par image max, jamais en aplat).
- Le **bordeaux est l'accent identitaire** (pills, liseré, CTA), pas un fond généralisé.
- **Nuit / Encre** portent la structure, **Crème** apporte de la respiration **uniquement dans les illustrations** (pas dans les embeds Discord qui restent en dark).

### 4.2 Palette — codes exacts à transmettre tels quels

| Nom | Hex | Usage |
|---|---|---|
| **Nuit** | `#0B1220` | Fond principal des compositions personnalisées (images `T*`) |
| **Encre** | `#070B14` | Fond profond (variante plus noire, pour profondeur) |
| **Lume** | `#2C3D56` | Structure, galets, éléments secondaires (bordures subtiles) |
| **Bordeaux** | `#8A2342` | Pills, accents identitaires, liseré gauche des embeds, CTA « cérémonie » |
| **Joue** | `#A83B55` | Accent doux (hover, variante claire de Bordeaux, à utiliser avec parcimonie) |
| **Étincelle** | `#F0C43C` | Highlights précieux : pointillés, contours jaunes, labels « Longueur/Largeur » |
| **Crème** | `#F6F1EA` | Cartes / zones claires **dans les images uniquement** (pas de fond d'embed clair) |

**Règles d'application (à coder et à documenter) :**

- **Embed side color :** `discord.Color.from_rgb(138, 35, 66)` (`#8A2342` Bordeaux) **partout** (banner, steps, résultat). Remplace l'actuel `discord.Color.from_rgb(88, 101, 242)` (blurple). Exception : `expired_embed()` reste `discord.Color.orange()`.
- **Ne jamais mettre 7 couleurs dans un même écran.** Choix type :
  - Bannière + Steps : Nuit/Encre + Crème (texte) + Bordeaux (pill) + Étincelle (1 touche).
  - Schémas explicatifs : line art Crème sur Nuit, highlight Étincelle, pill Bordeaux.
- **Fonds neutres Discord :** tu ne contrôles pas le fond du client. Assure-toi que tous les textes restent lisibles en thème sombre ET clair (contraste ≥ 4.5:1, tester sur fond `#313338` discord dark et `#FFFFFF` light).
- **Erreurs à éviter :**
  - Jaune en aplat de fond d'embed.
  - Bordeaux sur tout le message (perte de hiérarchie).
  - Cartes Crème à répétition (fatigue visuelle).
  - Emojis décoratifs en surnombre (2–3 max par embed).
  - Titres en caps démesurés dans l'embed.

### 4.3 Typographie (contrainte Discord)

| Famille | Poids/style | Usage (dans les **images personnalisées uniquement**) |
|---|---|---|
| **Syne ExtraBold** | 800 | Titres majeurs, « AZE », « AzeMouse », labels de pills (« Griffe », « Paume », « Longueur ») |
| **Fraunces** | Italic / Regular | Sous-titres précieux : « by aze129 », « On allume. », annotations narratives |
| **JetBrains Mono** | Regular | Cotes mm, codes hex, commandes slash, watermarks « ATK / Scyrox » |

**Limite technique Discord :** les embeds/messages natifs utilisent la police du client (gg sans). Tu ne peux pas imposer Syne/Fraunces/JetBrains dans le texte d'un embed. Donc :
- Dans les **images `T*`** : typographies respectées (déjà rendues).
- Dans les **embeds** : tu utilises la hiérarchie Markdown native : `**gras**`, `*italique*`, `` `code` ``, listes `•`, fields.
- N'essaie pas de simuler une police custom avec des caractères unicode fantaisistes.

---

## 5. CONTRAINTES VISUELLES PROPRES À DISCORD — CE QUE TU PEUX / NE PEUX PAS

### 5.1 Ce que tu PEUX
- Embeds (title, description, fields, footer, timestamp, `color`, `image`, `thumbnail`).
- Boutons : 5 styles (`primary=blurple`, `secondary=grey`, `success=green`, `danger=red`, `link=lien URL`) + `emoji` + `disabled` + max 25 caractères label (tronquer à 80 déjà fait).
- Select menus (StringSelect, 25 options max, placeholder).
- Modals (TextInput, 5 max).
- Messages éphémères (`ephemeral=True`), `edit_message` sur le message de parcours.
- Images hébergées (`https://`) via `embed.set_image(url=...)` ou `thumbnail`.

### 5.2 Ce que tu NE PEUX PAS
- Choisir la couleur de fond du client Discord.
- Définir une couleur hex arbitraire pour un bouton (seulement les 4 styles + link).
- Imposer une police custom au texte natif.
- Faire une mise en page libre à l'intérieur d'un embed (pas de grid, 3 fields inline max, largeur fixe).
- Garantir le rendu pixel-perfect sur mobile vs desktop (tester les deux).

### 5.3 Stratégie premium native
Combine :
- `color = #8A2342` + titres concis (`Étape 1/3 — Votre prise` plutôt que `Étape 1/3 — Votre style de prise` trop long).
- Descriptions de **2–3 lignes max** + liste à puces courte.
- **1 image par étape max** (les embeds n'acceptent qu'une image, pas de carrousel).
- Boutons limités : 1 select OU 1 bouton d'action par étape, puis 2–4 boutons au résultat (max 5 par row, 5 rows max).
- Supprime tout séparateur ASCII verbeux (`---`).

> Référence d'inspiration : `ImageEx` montre des **cartes multiples** → en Discord, traduis par **plusieurs embeds** (le message de résultat peut porter un embed principal + 1–2 embeds d'explication). Discord autorise jusqu'à 10 embeds par message. Utilise-le pour aérer sans surcharger un seul embed.

---

## 6. L'INTERFACE ACTUELLE : PROBLÈMES PRÉCIS À RÉSOUDRE

### 6.1 Diagnostic sur la capture `111947.png` (résultat type)

Structure actuelle d'un résultat (ex. Claw 200×110, Haut de Gamme) :

```
🎯 Résultat Mouse Shape Finder
🖐 Grip : Claw Grip
📏 Main : 200×110 mm
🎚️ Gamme : Haut de Gamme
🥇 Le Match Idéal — ATK X1 V2 Ultra Max — 75.00 € (prix non vérifié)
   Score : 40/40 — 100% du max théorique
   Confiance : moyenne
   • Longueur 127.0 mm vs cible 124.1–129.1 mm (dans la plage) : 10 pts
   • Largeur de prise estimée (coque −3 mm) 61.0 mm vs cible 57.2–61.2 : 10 pts
   • Compatibilité Claw Grip Élevé : 10 pts
   • Bosse Mid : adaptée : 5 pts
   • Boutons Mid : adaptés : 5 pts
   • Idéale pour soutenir … (fit_rationale)
🥈 L'Alternative — ATK A9 Plus 2.0 — 45.00 € …
   (même détail 6 lignes)
🧭 Pourquoi ce choix ?
   Haut de gamme : performances … parmi les 2 souris à 2 pts …
⏳ À vérifier (non classées)
   • ATK Phantom Ultimate : compatibilité … — score partiel 15/25 pts (non classable)
   • … (10 lignes, avec "et 7 autre(s)")
Footer : Score géométrique provisoire …
Boutons : Lien bientôt disponible : X1 V2 Ultra Max | Acheter A9 Plus 2.0 | Fermer | Refaire le test
```

### 6.2 Problèmes classés par gravité (à corriger)

| # | Problème | Impact UX | Correction attendue (sans toucher au moteur) |
|---|---|---|---|
| P1 | **Details internes exposés** (`Longueur … : 10 pts` etc.) | Surcharge cognitive, donne l'impression d'un debug | **Retirer toutes les lignes `… : X pts` de l'UI.** Le calcul reste dans `MouseScore.details` et dans `matrice_profils.md`, pas dans l'embed. Remplacer par 1–2 phrases humaines (« Longueur et largeur dans la cible, bosse et boutons adaptés à votre grip. ») |
| P2 | **Liste `À vérifier` interminable** (10+ noms, scores partiels) | Noyade du message principal, donne un poids visuel trompeur aux souris non évaluables | **Limiter à 3–5 noms max** (déjà `MAX_PENDING_SHOWN=5`), **sans scores partiels** (`15/25 pts`) dans l'embed public. Mettre seulement « Compatibilité non vérifiée » + note « Détails techniques : voir `docs/audit/matrice_profils.md` ». Truncate intelligible. |
| P3 | **Hiérarchie inexistante** : Match Idéal et Alternative ont le même poids visuel que les pendings | L'utilisateur ne voit pas le winner en 2 sec | **Structure en 3 blocs visuels** : (1) 🏆 Le Match Idéal — gros, avec prix + score + confiance + 1 phrase de justification ; (2) 🥈 L'Alternative — compacte, seulement si elle apporte une vraie différence (prix −30%, ou géométrie différente) — sinon afficher « Aucune alternative pertinente dans la gamme choisie. » ; (3) ℹ️ Note de confiance et lien doc — footer. |
| P4 | **Score répété** dans chaque field (100% deux fois) + Wording honnête mais dilué | Redondance, perte de crédibilité | **Un seul affichage du score** (sur le Match Idéal) + footer honnête conservé : « `Score de correspondance : 30/40 — 75% du maximum théorique du barème.` » Ne jamais afficher `100%` sans contexte, ne jamais dire « Compatibilité 100% ». |
| P5 | **Confiance noyée** (moyenne/faible au milieu du bloc) | L'utilisateur ne sait pas s'il peut faire confiance | **Badge `Confiance : moyenne — Dimensions vérifiées, largeur estimée (coque −3 mm, provisoire)`** en une ligne sous le score, avec emoji `🟡` / `🟢` / `🔴` stable (vert=élevée, jaune=moyenne, rouge=faible). |
| P6 | **Boutons décevants** : 2 boutons gris « Lien bientôt disponible » prennent 2 slots | Frustration | **Ne plus afficher un bouton disabled par souris sans lien.** Remplacer par **un seul bouton secondaire** `🔗 Liens à venir` disabled + note « Les liens commerciaux seront activés dès que fournis dans `data/commercial_links.json` ». Garder uniquement les vrais liens `🛒 Acheter <label>`. |
| P7 | **Couleur latérale générique blurple** | Aucune identité AzeMouse | **Passer à `#8A2342`** |
| P8 | **Aucune image dans le parcours** (URLs vides) | Parcours textuel triste | **Brancher `T08`, `T09`, `T11`** immédiatement, et prévoir les **nouvelles clés** pour les illustrations de résultat (hump, buttons, rear). |
| P9 | **Textes trop longs** sur mobile (fields > 600 car.) | Scroll infini, lisibilité | **Limiter chaque field à 400–600 car. max**, phrases courtes, tests sur mobile (largeur 360px). |
| P10 | **Alternative systématique** même si identique (ex. 40/40 vs 40/40) | Valeur ajoutée nulle | **N'afficher l'alternative que si `ranked[1].total >= ranked[0].total - tolerance` ET qu'elle diffère par mode** (prix significativement inférieur OU performance documentée différente OU géométrie différente). Sinon message informatif. |

---

## 7. MOTEUR MÉTIER — CE QUE TU NE TOUCHES PAS

### 7.1 Formules de plages cibles (à préserver strictement)

Pour une main `L` (longueur) et `W` (largeur sans pouce), en mm :

| | Palm / Claw | Fingertip |
|---|---|---|
| **Longueur min** | `71.4 + L×0.2633` | `0` (pas de minimum) |
| **Longueur max** | `min + 5.0` | `71.4 + L×0.2633 + 5.0` |
| **Largeur min** | `48.4 + W×0.08` | `47.3 + W×0.08` |
| **Largeur max** | `min + 4.0` | `min + 3.9` |

Constantes dans `utils/matcher.py` : `LENGTH_BASE_MM`, `LENGTH_SLOPE`, `LENGTH_SPAN_MM`, `WIDTH_BASE_*`, `WIDTH_SLOPE`, `WIDTH_SPAN_*`. **Ne pas renommer sans grep complet.**

**Largeur de prise utilisée** (`grip_width_for_scoring`) :
- Si `mouse.grip_width_mm` non null → `measured`
- Sinon → `mouse.width_max_mm − 3.0` (`GRIP_WIDTH_ESTIMATE_OFFSET_MM`) → `estimated`
- **Correctif provisoire**, à afficher tel quel : `« Largeur de prise estimée (coque −3 mm, provisoire) »`

### 7.2 Barème (40 pts) — strict, avec seuils `<` et `>` (pas `≤`/`≥`), arrondi `DELTA_DECIMALS=6`

| Critère | Points | Règle |
|---|---|---|
| Longueur | 10 / 5 / 0 + exclusion | `dans la plage →10` ; `écart <3.0 →5` ; `écart >8.0 →exclusion` |
| Largeur prise | 10 / 5 / 0 + exclusion | `dans la plage →10` ; `écart <2.0 →5` ; `écart >5.0 →exclusion` |
| Grip | 10 / 5 / excl. / pending | `Élevé→10, Moyen→5, Faible→exclusion, Inconnu→pending` |
| Bosse | 5 / 0 / pending | `Palm→{Front,Mid}`, `Claw→{Mid,Rear}`, `Fingertip→ignorée (0)` ; `Inconnu→pending` |
| Boutons | 5 ou 10 / 0 / pending | `Palm→{High}:5`, `Claw→{Low,Mid}:5`, `Fingertip→{Low}:10` ; `Inconnu→pending` |

Tables centralisées : `HUMP_IDEAL`, `BUTTON_IDEAL`, `BUTTON_POINTS`, `GRIP_POINTS`.

Affichage : `Score de correspondance : X/40 — Y% du maximum théorique du barème` où `Y = round(X*100/40)` (demi vers le haut, via `int(X*100/40+0.5)`). **Ne jamais présenter comme probabilité d'achat.**

### 7.3 Statuts

- `excluded` : longueur >8 ou largeur >5 ou grip Faible ou prix > budget custom.
- `pending` : aucune exclusion mais au moins une donnée `Inconnu` / `conflicting` / `length null`. `computable_max` = somme des maxima des critères évaluables. **Score partiel non classable.**
- `scored` : tout renseigné, score final /40.

**Confiance** (`_confidence`) :
- `élevée` si `dimension_status==verified` ET `fit_status==owner_spec` ET `width_source==measured`
- `moyenne` si `verified`+`owner_spec` mais `width_source==estimated`
- `faible` sinon

Aujourd'hui : toutes les souris sont `estimated` → confiance max `moyenne` (sauf Scyrox qui sont `owner_spec_unverified` → `faible`). Ne pas inventer de `measured`.

### 7.4 Modes de sélection (`utils/selection.py`) — tolérances PROVISOIRES à conserver

| Mode | Tolérance | Critère dans la zone |
|---|---|---|
| Économique | 5 pts | prix le plus bas |
| Qualité/Prix | 2 pts | `points/€` le plus élevé (indicateur provisoire, le dire) |
| Haut de Gamme | 2 pts | `performance_index` (0–2 : +1 si `polling≥8000`, +1 si `sensor∈{PAW3950, PAW3950 Ultra, PAW3955, PAW3955 Master}`) puis score |
| Peu importe le prix (2026-10-11) | 2 pts | **score d'abord**, puis `components_index` (capteur > MCU > switchs > fréquence, chacun 0–5), puis prix le plus bas ; aucun prix exigé. Poids affiché sur la ligne du match idéal et de l'alternative |
| Budget Perso | 2 pts | meilleur score ≤ budget, à score égal le moins cher |

`ranked` = 2 premiers de la zone ordonnée, `pending` = `pending` + (modes à prix : `eligible` sans prix). `explanation` = phrase type fournie par `_explanation()`.

### 7.5 Cas de non-régression (à garder en tests)

Main `180×90 mm`, **Palm** → cibles `118.8–123.8` (L) et `55.6–59.6` (W prise) :

| Souris | Score attendu | Détail verrouillé |
|---|---|---|
| Scyrox V6 | **30/40** | L 10, W 10, grip Moyen 5, bosse Mid 5, boutons Mid 0 |
| ATK Z1 V2 Ultra | **30/40** | L 10, W 0 (écart 4.2, entre 2 et 5), grip 10, bosse 5, boutons 5 — **doit rester 30, pas 35** |
| ATK A9 Plus 2.0 | **25/40** | L 5, W 5, grip 10, bosse 5, boutons 0 |
| ATK X1 V2 Ultra Max | **20/40** | L 0 (écart 3.2), W 5, grip 10, bosse 5, boutons 0 |
| Scyrox V8 / ATK F1 V3 | **exclues** | grip Palm Faible |

**Si un de ces scores change après ta refonte visuelle, tu as cassé le moteur.** Revert.

### 7.6 Muscle thénar — règle absolue

Si tu réintroduis l'étape thénar (pour utiliser `T10` et coller au parcours cible §9) :

- **Stockage uniquement** : `session.thenar = Small|Medium|Large` (ajoute le champ à `FinderSession`).
- **Affichage** : récap `Thénar : Moyenne` dans `recap` et dans le résultat, section « Profil ».
- **Zéro effet** sur : équations, seuils, points, score, classement, exclusion. Ne pas inventer de bonus « arrière étroit » automatique.
- Illustrations : `T10` pour la sélection, `T13_arriere_etroit` pour l'explication « Si thénar Small → arrière étroit conseillé » **à titre informatif uniquement**, avec disclaimer « Recommandation morphologique indicative, non prise en compte dans le score ».
- Tests antérieurs ont prouvé qu'aucune source ne définit de règle thénar→dimensions. **Ne pas en inventer.**

---

## 8. CATALOGUE ATK/SCYROX — DONNÉES SÉPARÉES DU RENDU

### 8.1 Où sont les données

- `data/mouse_db.json` : 18 entrées (6 Scyrox/ATK d'origine + 12 ATK vérifiées le 2026-10-10). Schéma v2 : chaque dimension porte `dimension_status`, `conflicts`, `sources[]`. Ne pas modifier les valeurs géométriques pour « faire joli ».
- `data/commercial_links.json` : liens séparés. **Ne pas inventer** de liens. Clé = `id` de la souris. URL invalide (pas `https://`) → ignorée avec warn log.
- `CATALOGUE_ATK.md` : documente 23 produits ATK listés, choix de non-ajout (Z1 originale suspecte, Duckbill longueur en conflit, etc.). Lire avant d'ajouter une souris.

### 8.2 Statuts de données à respecter à l'affichage

- `verified` (≥2 sources concordantes ≤0.5 mm) → confiance moyenne/élevée possible.
- `single_source` → confiance faible, afficher « Prix / dimensions d'une seule source ».
- `conflicting` (ex. Duckbill `118.0 vs 117`) → `length_mm = null`, souris `pending`, ne jamais afficher une valeur tranchée.
- `owner_spec` / `owner_spec_unverified` (Scyrox) → faible.
- `fit_status` / `price_status` : même logique.

### 8.3 Familles listées (sans garantie d'exhaustivité)

A9 (Plus, Ultimate, Air, Mini), F1 (V3 Ultimate), X1 (V2 Ultra Max), Z1 (V2 Ultra), Ghost (Ultimate, Extreme), Phantom (Ultimate), Y9 (Ultimate), Fierce X, U2 (V2 Ultimate, V2 Mini), ZERO, Duckbill, Scyrox V6/V8. **Tu ne dois pas ajouter/supprimer une famille pour des raisons esthétiques.** Toute évolution du catalogue se fait via `tools/build_mouse_db.py` (attention : écrase le fichier) ou édition manuelle tracée + `python tools/compare_profiles.py`.

---

## 9. PARCOURS UTILISATEUR CIBLE — ADAPTATION VISUELLE

### 9.1 Parcours actuellement codé (à vérifier)

| Ordre codé | Embed | Image actuelle | Action |
|---|---|---|---|
| Persistance | `banner_embed()` | `banner` (vide) | `StartView` → `GripView` |
| 1/3 | `grip_step_embed()` | `step1_grip` (vide) | `GripSelect` → `MeasureView` |
| 2/3 | `measure_step_embed(session)` | `step2_measure` (vide) | `MeasureView.open_measures` → `MeasureModal` → `BudgetView` |
| 3/3 | `budget_step_embed(session)` | `step3_budget` (vide, repli `step4_budget`) | `BudgetSelect` → soit `BudgetModal` si CUSTOM, soit `results_embed` |

**Parcours cible demandé** (avec thénar informatif) :

```
Accueil (bannière AzeMouse)
  → 1/4 Grip            (T09)
  → 2/4 Thénar          (T10) — Small/Medium/Large, disclaimer "n'influence pas le score"
  → 3/4 Mesures         (T11) — + rappel T12 en aide
  → 4/4 Budget          (sans image ou T08 mini)
  → Résultat            (1 embed principal + 1–2 embeds d'explication avec T01/T02/T03/T07/T13/T14/T15 selon le match)
```

**Consigne :**
- Vérifie `finder_flow.py` : si tu trouves `GripView`, `MeasureView`, `BudgetView` (3 étapes), **ne casse pas les `custom_id`** pour ajouter le thénar. Soit tu insères `ThenarView` entre `Grip` et `Measure` en décalant `MeasureView`→`ThenarView` puis `ThenarView`→`MeasureView`, soit tu gardes 3 étapes et tu ajoutes la sélection thénar comme **field informatif** dans l'étape Mesures (moins intrusif, recommandé si le propriétaire veut rester à 3 étapes).
- Quelle que soit la voie, la session doit rester compatible : `session_id` inchangé, ancien parcours invalidé au `start`.
- **Confidentialité :** tout le parcours reste `ephemeral=True` sauf le banner.

### 9.2 Détail visuel par écran (à implémenter)

**A. Banner persistant**
- `embed = banner_embed()` : `title = "🖱️ Mouse Shape Finder"` (ou mieux : `"AzeMouse — Mouse Shape Finder"`), `description` 3 lignes max, `color = #8A2342`, `image = T08` (bannière).
- Texte : « Trouvez la souris dont la géométrie épouse **votre** main. 3 questions rapides (prise, mesures, budget) → recommandation personnalisée. *Réponses privées : seul vous voyez le résultat.* »
- Bouton : `Start Mouse Shape Finder` `primary` `🖱️` `START_CUSTOM_ID`.
- Ne pas toucher à `manager.py` (`!setup_finder`) sauf pour la couleur de l'embed.

**B. Étape 1 — Grip**
- `title = "Étape 1/3 — Votre prise"` (ou `1/4` si thénar).
- `description = "Quelle prise utilisez-vous le plus ?"` + 3 lignes courtes (pas de pavé).
- `image = T09` (les 3 line arts Griffe/Paume/Bout des doigts).
- `Select` : garde `GRIP_OPTIONS` (Palm/Claw/Fingertip) avec `description` courte. Placeholder : « Choisissez votre prise… ».

**C. Étape 2 — Thénar (optionnelle, informative)**
- `title = "Étape 2/4 — Votre éminence thénar"` (ou `2/3` si intégrée à Mesures).
- `description = "À titre informatif : cette donnée **n'influence pas** le score. Elle aide à comprendre l'arrière de la souris conseillé."`
- `image = T10` (Petite/Moyenne/Grande).
- `Select` : `Small / Medium / Large` (ou `Petite / Moyenne / Grande` selon wording final, mais utiliser la même langue que le reste).
- Au `callback`, stocker `session.thenar` et passer à `MeasureView`.

**D. Étape Mesures**
- `title = "Étape 2/3 (ou 3/4) — Vos mesures"`
- `description` :
  ```
  ✋ Prise : **Claw Grip**
  📏 Avec une règle, mesurez :
  • **Longueur** : pli du poignet → bout du majeur
  • **Largeur** : articulations, **sans le pouce**
  ```
- `image = T11` (mains + règle).
- `View` : bouton `Saisir mes mesures` `primary` `📏`.
- `Modal MeasureModal` : inchangé fonctionnellement (`parse_hand_measures`). Placeholders `Ex : 180` / `Ex : 90`. Messages d'erreur privatifs déjà corrects.

**E. Étape Budget**
- `title = "Étape 3/3 — Budget et gamme"`
- `description = "Choisissez votre gamme."` + récap `Grip + Main` + (si thénar) `Thénar`.
- `image` : facultative (`step3_budget` vide → pas d'image). Ne pas forcer `T08` ici (déjà en banner). Laisse vide ou utilise une illustration minimaliste si le propriétaire fournit une image `step3_budget` dédiée.
- `Select BUDGET_OPTIONS` inchangé.

**F. Résultat — refonte majeure**

*Structure cible (2 embeds max par message de résultat) :*

**Embed 1 — Principal (couleur Bordeaux, image selon le match)**

```
Title: 🎯 Votre recommandation
Description: ✋ Palm Grip  •  📏 180×90 mm  •  🎚️ Qualité/Prix
Fields:
  🥇 Le Match Idéal
    **Scyrox V6** · 74.90 € (prix non vérifié)
    Score : **30/40 — 75% du maximum théorique**  ·  🟡 Confiance moyenne
    Bosse **Mid** et boutons **Mid** adaptés à votre Palm. Longueur et largeur dans la cible.
  🥈 L'Alternative (ou « Pas d'alternative pertinente »)
    **ATK Z1 V2 Ultra** · 75.00 €
    Même score, polling 8000 Hz documenté. Choix Haut de Gamme si vous cherchez la perf pure.
  🧭 Pourquoi ce choix ?
    Qualité/Prix : meilleur rapport points/€ parmi 2 souris ≤2 pts du meilleur score (30/40). Indicateur provisoire.
Footer: Score géométrique provisoire, ni probabilité d'achat ni validation biomécanique. Largeur de prise estimée (coque −3 mm) tant que non mesurée.
Image: selon le Match Idéal — si Palm → Bosse Mid (T14) + Boutons Mid (T03) ; si Claw → Hump Rear/Mid selon la souris + Low/Mid etc. Choisir 1 image max qui illustre le point discriminant (bosse OU boutons), pas 3.
```

**Embed 2 — Détails géométriques (optionnel, si besoin d'expliquer la cible)**

```
Title: 📐 Repères de taille
Description: Pour votre main (180×90, Palm) — cible longueur 118.8–123.8 mm, largeur de prise 55.6–59.6 mm.
Image: T12 (souris longueur/largeur)
Fields:
  • Votre cible expliquée (1 phrase)
  • Ce que fait le score (1 phrase)
```

**Règles de choix d'image de résultat :**

| Condition | Image à afficher |
|---|---|
| Grip Palm + bosse Mid/Front du winner | `T14` (Bosse centrale) ou `T15` (Bosse avant) si `Mid-Front` |
| Grip Claw + bosse Rear | `T07` (Bosse arrière) |
| Grip quelconque + winner a `Arrière étroit` (ex. F1) | `T13` (Arrière étroit) en alternative |
| Boutons High du winner (ex. Z1 Palm) | `T01` (Boutons hauts) |
| Boutons Low du winner (ex. F1 Claw/Fingertip) | `T02` (Boutons bas) |
| Boutons Mid | `T03` (Boutons moyens) |
| Besoin d'expliquer les variantes Claw | En annexe doc, pas dans le résultat (T04/T05/T06 sont pour la doc, pas pour l'embed) |

> **Une seule image par embed.** Si deux points sont aussi importants (bosse + boutons), privilégie la bosse (plus déterminante pour le ressenti) et mentionne les boutons en texte.

**G. Boutons du résultat**

- Pour chaque `score` dans `selection.ranked` :
  - Si `links.get(mouse.id)` existe et valide (`https://`) → `Button Link` `🛒 Acheter <label>` (max 2).
  - Sinon → **pas de bouton disabled par souris**. Un seul bouton disabled global si aucun lien : `🔗 Liens à venir` `secondary` `disabled`.
- Ensuite row 2 : `✖️ Fermer` (`secondary`) et `🔄 Refaire le test` (`secondary`). Le `Fermer` doit `edit_message(content="✅ Résultat fermé …", embed=None, view=None)` (déjà codé).

---

## 10. PRINCIPES UX SUPPLÉMENTAIRES (checklist qualité)

- **Hiérarchie :** 1) Action → 2) Info demandée → 3) Avancement (Étape X/Y) → 4) Explication → 5) Détails secondaires (jamais avant).
- **Sobriété :** pas de titres en 24pt simulés par `##`, pas de doubles listes, pas de `Score : 40/40 — 100%` répété deux fois, pas de `⏳ À vérifier` avec 12 lignes.
- **Cohérence :** même `color`, même ton (« vous », concis), même style de pills dans toutes les images `T*`.
- **Mobile first :** tester sur iPhone SE (375px) et iPad ; embeds < 600 car./field, pas de mot > 25 car., images 16:9 recadrées.
- **Accessibilité :** contraste texte/fond ≥ 4.5, info jamais portée uniquement par la couleur (toujours un label), emojis avec texte.
- **Efficacité :** 3 clics + 2 saisies = résultat. N'ajoute pas d'étape « Confirmation » ou « Tutoriel » inutile.

---

## 11. CONTRAINTES TECHNIQUES — NE PAS MIGRER

- **Stack imposée :** Python 3.10+ (testé 3.11), `discord.py 2.4+`, `python-dotenv 1.0+`.
- **Ne pas migrer vers** Node, Discord.js, Next.js, ou autre framework Web.
- **Lancer :** `python bot.py` (lecture `.env` à côté de `config.py`, pas du CWD). `intents.message_content = True` obligatoire (commande préfixée).
- **Fichiers à conserver tels quels sauf besoin visuel :** `bot.py`, `config.py`, `utils/*`, `cogs/*`, `data/*`, `assets/*`, `tools/*`, `tests/*`, `requirements.txt`, `pytest.ini`, `docs/*`, `state/` (gitignored).
- **Aucun secret en dur.** Token dans `.env` (jamais commité). `tools/check_deployment.py` ne l'affiche pas.
- **Compatibilité :** le bot relit `assets/images.json` et `commercial_links.json` **à chaque interaction** (pas de cache nécessitant restart).

---

## 12. MÉTHODE DE TRAVAIL IMPOSÉE (12 étapes)

1. **Examiner le dépôt** (branche `arena/9ddacf48-mousediscord`, `git status` propre, `git log` `2191fee Image`).
2. **Ouvrir les 31 images** (`ImageAct` 7, `ImageEx` 9, `ImageUse` 15) — **lister leurs noms, tailles, sujets** avant toute proposition.
3. **Produire l'inventaire & matrice de correspondance** (table §3.1) dans `docs/INVENTAIRE_IMAGES.md` ou dans ce Master Prompt (ci-dessus).
4. **Identifier les problèmes de présentation** (table §6.2 P1–P10) et les hiérarchiser.
5. **Définir les changements visuels** à partir de la charte §4 (couleur embed Bordeaux, choix des images par étape, allègement du résultat).
6. **Lister ce que tu ne toucheras PAS** (§7, §8) et le faire valider dans le code (grep `GRIP_WIDTH_ESTIMATE_OFFSET_MM`, `HUMP_IDEAL`, etc.).
7. **Implémenter progressivement :**
   a. D'abord couleur + textes courts (embeds) — test `pytest`.
   b. Puis branchement des 3 images principales (`banner`, `step1_grip`, `step2_measure`) — test.
   c. Puis refonte du résultat (suppression details pts, pending résumé, alternative conditionnelle) — test.
   d. Enfin illustrations de résultat (hump/buttons/rear) — test.
   e. Enfin (optionnel) thénar informatif — test.
8. **Intégrer les ressources** : héberger `T*.png` en `https://`, remplir `assets/images.json` (garder `step3_budget` repli, ajouter les nouvelles clés), étendre `utils/assets.py::IMAGE_KEYS` et `LEGACY_KEYS` si tu ajoutes des clés (avec tests `test_data.test_images_config_has_all_keys` à mettre à jour).
9. **Tester les interactions simulées** : adapter `tests/test_flow.py` si tu ajoutes une vue (nouveaux `session_id`, `View`, `lookup`), mais ne pas supprimer les tests de non-régression numérique.
10. **Vérifier l'absence de régressions** (§13) — `pytest -q` doit rester vert, `privacy_scan` à 0, `pyflakes` propre.
11. **Mettre à jour la documentation** : `README.md` (captures, parcours 3/3→3/4 si thénar), `assets/images.json` comment, `docs/audit/matrice_profils.md` si catalogue changé (ne pas changer si non nécessaire), nouveau `docs/REPORTE_DESIGN.md` listant les URLs et mappings.
12. **Fournir un rapport final** : changements réalisés, captures avant/après (ou descriptions), résultats de tests, limites connues, points ouverts (prix, thénar).

> Ne code pas l'UI avant d'avoir validé la matrice d'images. Ne fais pas de « refonte aveugle » à partir d'une seule capture `111947.png`.

---

## 13. TESTS DE NON-RÉGRESSION OBLIGATOIRES

### 13.1 Calculs (à garder verts)

```bash
pytest tests/test_matcher.py -k palm_180x90
# Attendu : V6 30, Z1 30 (écart 4.2 → 0 pt, pas 35), A9 25, X1 20, V8/F1 exclues
pytest tests/test_matcher.py tests/test_selection.py
# Plages Palm/Claw/Fingertip, bornes strictes <3/<2/>8/>5, arrondi 6 décimales,
# largeur mesurée vs estimée, confidence, budget custom
pytest tests/test_selection.py
# Modes : Économique ≤5 pts prix le plus bas, Qualité/Prix points/€, Haut de Gamme perf 0–2,
# Peu importe le prix = forme puis composants documentés, Custom budget ≤
# pending jamais classé, prix inconnu → pending (sauf Haut de Gamme et Peu importe le prix)
```

### 13.2 Confidentialité

```bash
pytest tests/test_privacy.py tests/test_privacy_scan.py tests/test_session.py
# P02–P12 : 1 utilisateur, 2 utilisateurs simultanés, intrus, expiration, restart, lookup forbidden, discard
python tools/privacy_scan.py  # 0 violation : aucun send_message sans ephemeral=True hors StartView, aucun edit hors fonctions autorisées, pas de channel.send
```

Critères :
- Un utilisateur ne voit que son parcours (`lookup(session_id, user_id)` vérifie les deux).
- Résultats 100% éphémères (`send_message(ephemeral=True)` ou `edit_message` sur message éphémère).
- Anciennes vues ne modifient pas une session récente (`_active_by_user`).
- `Fermer` d'un user ne ferme pas celui d'un autre (`owner_id` check).

### 13.3 Interface Discord (simulée)

```bash
pytest tests/test_flow.py tests/test_setup_command.py
# Parcours 1/3→3/3, erreurs de saisie restent sur la même étape, score wording « Score de correspondance : X/40 — Y% », pending séparé, lien manquant → « Lien bientôt disponible » (ou nouveau single disabled), Refaire le test → GripView
```

À adapter si tu ajoutes ThenarView : ajouter `test_thenar_is_stored_and_not_scored`.

### 13.4 Intégration graphique

- Chaque asset utilisé a une URL `https://` valide (pas `http://`, pas `ftp://`) dans `assets/images.json`.
- `_image(embed, key)` ne casse pas si URL vide/invalide (pas d'image, pas d'exception).
- Aucune image ne fait échouer l'envoi d'un embed (tester `load_image_urls` avec fichier manquant/corrompu).
- Embeds lisibles sur mobile (fields ≤1024 car., description ≤4096, total ≤6000).

```bash
pytest tests/test_data.py tests/test_catalog_lookup.py
# Schéma v2, dimensions null justifiées, conflicts ≥2 values, sources obligatoires si verified/single_source, images.json repli
pytest tests/test_doc_references.py  # chemins cités existent, titres exacts
```

### 13.5 Documentation & déploiement

```bash
pytest tests/test_config.py tests/test_deployment_check.py
python tools/check_deployment.py  # depuis la racine, sans afficher le token
```

Vérifier : chemins indépendants du CWD, `FINDER_STATE_PATH` dans `state/` (gitignored), variables d'env invalides → `ConfigError` clair.

**Ce que les tests ne couvrent pas (à faire manuellement, voir `PROTOCOLE_DISCORD_CONFIDENTIALITE.md`) :**
- 2 comptes réels en parallèle sur un serveur de test.
- Expiration TTL 1800s (ou réduire à 60s pour tester).
- Redémarrage bot + clic sur ancien `Start` → nouveau parcours.
- `!setup_finder` 3× → un seul message, édité, aucun doublon, salon seul verrouillé.
- Permissions `@everyone` limitées au salon cible.

---

## 14. PLAN D'IMPLÉMENTATION DÉTAILLÉ (code)

### 14.1 `assets/images.json` — étendre sans casser

Actuel :
```json
{
  "_aide": "Renseignez une URL https:// ... La clé step3_budget remplace step4_budget ...",
  "banner": "",
  "step1_grip": "",
  "step2_measure": "",
  "step3_budget": ""
}
```

Proposé (rétro-compatible) :
```json
{
  "_aide": "...",
  "banner": "https://.../T08_azemouse_banniere.png",
  "step1_grip": "https://.../T09_griffe_paume_doigts.png",
  "step2_measure": "https://.../T11_mesurer_la_main.png",
  "step3_budget": "",
  "step2_thenar": "https://.../T10_tailles_de_main.png",
  "illustration_mouse_dimensions": "https://.../T12_souris_longueur_largeur.png",
  "illustration_rear_narrow": "https://.../T13_arriere_etroit.png",
  "illustration_hump_mid": "https://.../T14_bosse_centrale.png",
  "illustration_hump_front": "https://.../T15_bosse_avant.png",
  "illustration_hump_rear": "https://.../T07_bosse_arriere.png",
  "illustration_buttons_high": "https://.../T01_boutons_hauts.png",
  "illustration_buttons_low": "https://.../T02_boutons_bas.png",
  "illustration_buttons_mid": "https://.../T03_boutons_moyens.png",
  "illustration_grip_relaxed": "https://.../T04_griffe_relachee.png",
  "illustration_grip_aggressive": "https://.../T05_griffe_agressive.png",
  "illustration_grip_pincer": "https://.../T06_griffe_pince.png"
}
```

Ne renseigne que les URLs dont l'hébergeur est **stable et public**. Laisse `""` si tu ne peux pas héberger immédiatement : l'embed n'affichera pas d'image, mais ne plantera pas.

### 14.2 `utils/assets.py` — ajouter les clés

```python
IMAGE_KEYS = (
  "banner", "step1_grip", "step2_measure", "step3_budget",
  "step2_thenar",
  "illustration_mouse_dimensions", "illustration_rear_narrow",
  "illustration_hump_mid", "illustration_hump_front", "illustration_hump_rear",
  "illustration_buttons_high", "illustration_buttons_low", "illustration_buttons_mid",
  "illustration_grip_relaxed", "illustration_grip_aggressive", "illustration_grip_pincer",
)
LEGACY_KEYS = {"step3_budget": "step4_budget"}
```

Mettre à jour `tests/test_data.test_images_config_has_all_keys` si tu ajoutes des clés (ou fais-en des clés optionnelles — au choix, mais documente).

### 14.3 `cogs/finder_flow.py` — changements visuels

**Couleur**
```python
COLOR = discord.Color.from_rgb(138, 35, 66)  # Bordeaux #8A2342, remplace 88,101,242
```

**Helpers**
- Garder `_send_ephemeral`, `require_session`, `_show_private`, `_image`.
- Ajouter `_choose_result_image(mouse, grip)` qui retourne la clé d'illustration la plus pertinente (bosse prioritaire, sinon boutons).

**Embeds étapes :**
- `banner_embed()` : garde `title`/`description` courte, `color`, `_image(..., "banner")`.
- `grip_step_embed()` : `title = "Étape 1/3 — Votre prise"` (ou `1/4`), `description` 2 lignes, `_image(..., "step1_grip")`.
- `measure_step_embed(session)` : `_recap` inclut thénar si présent, `title = "Étape 2/3 — Vos mesures"`, `_image(..., "step2_measure")`.
- **Si thénar ajouté :** `thenar_step_embed(session)` avec `T10`, disclaimer.
- `budget_step_embed(session)` : inchangé mais `_image(..., "step3_budget")` (peut rester vide).

**Nouveau `_recap(session)` :**
```python
def _recap(session):
  parts = []
  if session.grip: parts.append(f"✋ Prise : **{GRIP_LABELS[session.grip]}**")
  if session.thenar: parts.append(f"🖐️ Thénar : **{session.thenar}** _(informatif)_")
  if session.hand_length_mm: parts.append(f"📏 Main : **{length:g} × {width:g} mm**")
  return "\n".join(parts)
```

**Résultat : réécrire `results_embed` et `_candidate_text` / `_pending_text`**

- Supprimer `details` (`Longueur … : 10 pts`) de `_candidate_text`. Nouveau format (≤400 car.) :
  ```python
  def _candidate_text(score):
    mouse = score.mouse
    price = f"{mouse.price_eur:.2f} €" if mouse.price_eur else "prix non renseigné"
    if mouse.price_status != "verified" and mouse.price_eur: price += " (non vérifié)"
    conf_emoji = {"élevée":"🟢","moyenne":"🟡","faible":"🔴"}.get(score.confidence, "🔴")
    return (
      f"**{mouse.label}** · {price}\n"
      f"Score : **{score.total}/{MAX_SCORE} — {compatibility_percent(score)}%** du max théorique  {conf_emoji} Confiance {score.confidence}\n"
      f"{mouse.fit_rationale[:120]}"  # 1 phrase, pas 3
    )
  ```
- `_pending_text` : ne plus afficher `15/25 pts`. Exemple :
  ```python
  def _pending_text(pending):
    lines = [f"• **{s.mouse.label}** — compatibilité {s.grip.label} non vérifiée" for s in pending[:5]]
    if len(pending) > 5: lines.append(f"… et {len(pending)-5} autre(s) — voir docs/audit/matrice_profils.md")
    return "\n".join(lines)
  ```
- `results_embed` :
  - `color = COLOR` (bordeaux)
  - `description = _recap(session) + "\n🎚️ Gamme : **...**"`
  - `add_field("🥇 Le Match Idéal", _candidate_text(top), inline=False)`
  - Alternative conditionnelle (voir §6.2 P10)
  - `add_field("🧭 Pourquoi ce choix ?", selection.explanation, inline=False)`
  - Si `pending` : `add_field("⏳ À vérifier (non classées)", _pending_text(pending), inline=False)` **ou** si `len(pending)>8`, n'afficher que le compte : `f"{len(pending)} souris non évaluables (données incomplètes) — détails dans la matrice."`
  - `set_footer(text=SCORE_DISCLAIMER)` — garder tel quel
  - `set_image` avec la clé choisie par `_choose_result_image` (ex. `illustration_hump_mid`)
  - **Ne pas mettre plus de 4 fields** (limite cognitive et mobile).

**Views :**
- `ResultsView` : ne plus créer un bouton disabled par souris sans lien. Si `ranked` a 0 vrai lien, un seul bouton `link` est absent → rien. Ajouter un seul disabled global si besoin. Garder `Fermer` et `Refaire le test` en 2e row.
- Si tu ajoutes `ThenarView`/`ThenarSelect` : copier le pattern `GripSelect` (placeholder, options Small/Medium/Large, callback stocke puis `edit_message` vers `MeasureView`).

**Modals :** inchangés (`MeasureModal`, `BudgetModal`), juste vérifier `parse_*` labels.

### 14.4 `utils/session.py` — si thénar ajouté

```python
@dataclass
class FinderSession:
  ...
  thenar: str | None = None  # "Small"|"Medium"|"Large" (ou "Petite"/"Moyenne"/"Grande")
```

Aucun autre fichier ne lit `thenar` pour calculer.

### 14.5 Tests à mettre à jour (minimaux)

- `tests/test_data.py` : si tu ajoutes des clés, mettre à jour `test_images_config_has_all_keys`.
- `tests/test_flow.py` : ajouter un test `test_thenar_step` si thénar ajouté, et adapter `test_valid_measures_move_to_budget_step` si le flux passe par thenar.
- Ne **supprime pas** les tests de scores 30/30/25/20.

---

## 15. CRITÈRES D'ACCEPTATION (checklist livrable)

- [ ] `pytest -q` : 219+ tests verts (ou plus si ajout thénar), 1 warning `audioop` toléré, `pyflakes` propre.
- [ ] `python tools/privacy_scan.py` → `0 violation(s)`.
- [ ] Couleur d'embed = `#8A2342` partout (sauf `expired` orange), vérifiée visuellement sur capture.
- [ ] `assets/images.json` contient au moins `banner`, `step1_grip`, `step2_measure` en `https://` stables, et les nouvelles clés renseignées ou vides sans plantage.
- [ ] Parcours testé manuellement sur serveur de test : 3 clics + 2 saisies → résultat en <60s, éphémère, pas d'accumulation.
- [ ] Résultat : Match Idéal lisible en 2 sec, pas de lignes `… : 10 pts`, pending ≤5 noms sans scores partiels, footer honnête conservé, boutons d'achat fonctionnels, `Fermer`/`Refaire` OK.
- [ ] Grip 180×90 Palm → V6 30, Z1 30, A9 25, X1 20 (non-régression).
- [ ] Thénar (si ajouté) stocké et affiché, mais n'influence aucun score (vérifié par `test_thenar_not_affecting_score` ou équivalent).
- [ ] Aucun lien commercial inventé, aucun prix inventé.
- [ ] Documentation à jour : `README.md` (§ Personnaliser les images), `docs/REPORTE_DESIGN.md` (URLs + mappings), `matrice_profils.md` régénérée si catalogue changé.
- [ ] Captures `ImageAct` après refonte fournies (ou description) montrant l'amélioration sur mobile et desktop thème sombre.

---

## 16. DOCUMENTATION À PRODUIRE / METTRE À JOUR

1. **`README.md`** : mettre à jour le tableau « Fonctionnement » (1/3→1/4 si thénar), la section « Personnaliser les images » (lister toutes les clés et leur illustration), et la section « Moteur de scoring » si wording du score change (mais garder `X/40 — Y%`).
2. **`assets/images.json`** : commenter les nouvelles clés (dans `_aide`).
3. **`docs/REPORTE_DESIGN.md` (nouveau)** : pour chaque `T0*.png` → URL https, clé, écran, capture actuelle vs nouvelle (facultatif).
4. **`docs/audit/matrice_profils.md`** : régénérer via `tools/compare_profiles.py` uniquement si `mouse_db.json` changé.
5. **`docs/audit/AUDIT.md` §8 / `RAPPORT_FINAL.md` §7** : noter la décision thénar et la non-modification du barème Z1 30/40.
6. **Commentaires de code** : en tête de `finder_flow.py` et `assets.py`, expliquer la charte (Nuit/Bordeaux/Étincelle) et les limites Discord.

---

## 17. LIMITES ET POINTS OUVERTS À NE PAS MASQUER

- **Aucune largeur de prise mesurée** : toutes les souris restent en `estimated` → confiance plafonnée à `moyenne`. Documenter.
- **Prix EUR non vérifiés** pour les 12 nouvelles variantes (ATK en USD) → modes à prix partiels. Ne pas convertir.
- **Bosse F1/X1** : conflit `Mid` (cahier) vs `Back - minimal` (EloShapes) — valeur propriétaire conservée, à confirmer.
- **A9 Plus largeur** 63.5 vs 64.0 → conservé 63.5 (écart 0.5 mm toléré).
- **Duckbill longueur** 118.0 vs 117 → `conflicting`, souris pending.
- **Y9 polling** 8000 vs 1000 → `polling_hz = null`, conflit listé.
- **Capteur X1** PAW3395 vs PAW3950/3955 → `sensor = null`, conflit listé.
- **Hébergement d'images** : le bot ne sert pas d'images ; il ne fait qu'afficher des URLs `https://` publiques. Prévoir un hébergement durable (pas d'URL éphémère Discord CDN).
- **Thème Discord clair** : tester la lisibilité (embed bordeaux sur fond clair reste OK, mais vérifier).

---

## 18. RAPPEL FINAL POUR L'AGENT CODEUR

Tu n'es pas un designer Web. Tu es un **artisan d'embeds Discord premium**.

- **Une couleur forte (Bordeaux), une touche précieuse (Étincelle), un fond sombre (Nuit).** C'est tout.
- **Un message = une intention.** Pas de pavé.
- **Une image = une explication.** Pas de décoration.
- **Un score = une estimation géométrique.** Pas une vérité biomécanique.
- **Un pending = un silence visuel.** Pas une seconde liste aussi grosse que le winner.
- **Une confidentialité = sacrée.** Tout le parcours est éphémère, isolé par `session_id` + `user_id`.

Si tu hésites entre deux designs, choisis le plus **lisible sur mobile en 3 secondes**.

Commence par lire le dépôt. Ensuite choisis les images. Ensuite seulement, code.

---

### Annexe A — Commandes utiles

```bash
# Vérifier l'état
git status
git diff
git log --oneline -10

# Installer et tester
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest -q
python -m pyflakes bot.py config.py cogs utils tests tools
python tools/privacy_scan.py
python tools/check_deployment.py
python tools/compare_profiles.py

# Lancer le bot (après avoir rempli .env)
python bot.py

# Déployer (Alwaysdata / FileZilla) — voir docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md
```

### Annexe B — Fichiers critiques (ne jamais supprimer)

```
bot.py
config.py
cogs/finder_flow.py
cogs/mouse_finder.py
utils/matcher.py
utils/selection.py
utils/models.py
utils/catalog.py
utils/assets.py
utils/session.py
utils/validation.py
data/mouse_db.json
data/commercial_links.json
assets/images.json
state/finder_message.json  (généré, gitignored)
```

### Annexe C — Palette en RGB pour discord.py

```python
Nuit         = discord.Color.from_rgb(11, 18, 32)   # #0B1220
Encre        = discord.Color.from_rgb(7, 11, 20)    # #070B14
Lume         = discord.Color.from_rgb(44, 61, 86)   # #2C3D56
Bordeaux     = discord.Color.from_rgb(138, 35, 66)  # #8A2342 ← embed side color
Joue         = discord.Color.from_rgb(168, 59, 85)  # #A83B55
Étincelle    = discord.Color.from_rgb(240, 196, 60) # #F0C43C — jamais en aplat
Crème        = discord.Color.from_rgb(246, 241, 234) # #F6F1EA — dans images seulement
COLOR = Bordeaux
```

*Fin du Master Prompt. Ce document est autonome : un agent sans historique, avec accès au dépôt `francoiseargaud43-source/MouseDiscord` branche `arena/9ddacf48-mousediscord`, doit pouvoir l'exécuter sans autre source.*

