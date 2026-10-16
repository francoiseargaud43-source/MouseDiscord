# AzeMouse — comment le système fonctionne (vérité courante)

À lire **avant** de coder. Dix minutes, et tout le reste du dépôt devient lisible. Ce document décrit ce
que le système **est** aujourd'hui ; l'histoire de chaque décision vit dans les registres (§8). Ses
chiffres sont relus par `tests/test_architecture.py` contre le code : s'ils divergent, la suite échoue.

## 1. En une phrase

Un bot Discord pose trois à cinq questions selon la prise (prise, variante, thénar, mesures de la main,
budget), note
chacune des 36 souris du catalogue sur 40 points selon sa géométrie, et montre **trois souris** dans un
seul message privé, avec l'explication du choix.

## 2. Le parcours

```
Panneau public « Start Mouse Shape Finder »   (cogs/mouse_finder.py, commande !setup_finder)
   └─ message privé (éphémère) :
      1. Prise ............ Palm / Claw / Fingertip
      2. Variante ......... Claw seulement : relâchée / agressive / pincée   (aucun effet sur le score)
      3. Thénar ........... sauf Fingertip : petite / moyenne / grande        (aucun effet sur le score)
      4. Mesures .......... longueur et largeur de la main (mm), formulaire
      5. Budget ........... Économique · Qualité/Prix · Haut de gamme · Peu importe · budget libre (€)
   └─ résultat : un message, trois places + blocs d'explication
```

Une seule fonction décide de l'étape affichée, d'après les réponses déjà données (`step_kind` dans
`cogs/finder_flow.py`) : un clic rejoué ou un redémarrage du bot reprend le parcours là où il était. Les
parcours en cours sont gardés dans `state/sessions.json` ; une fois le résultat donné, plus rien n'est
écrit sur disque, et un parcours abandonné expire (30 minutes par défaut, `SESSION_TTL_SECONDS`).

## 3. Le calcul, en trois temps

### 3.1 La note géométrique — `utils/matcher.py`

Les **plages cibles** de la main viennent de l'outil d'origine (Oblivity), retrouvées à l'identique sur ses
10 sorties datées (`Reverse/`) :

- longueur de souris : de `71,4 + 0,2633 × L` à cette valeur + 5 mm (Palm, Claw) ; en Fingertip, seul le
  maximum compte ;
- largeur de prise : de `48,4 + 0,08 × W` à + 4 mm (Palm, Claw), de `47,3 + 0,08 × W` à + 3,9 mm
  (Fingertip) ; la largeur de prise d'une souris est estimée à sa largeur de coque − 3 mm, faute de mesure.

| Critère | Points | Règle |
| --- | --- | --- |
| Longueur | 10 | dans la plage : 10 · à moins de 3 mm : 5 · à plus de 8 mm : souris **écartée** |
| Largeur de prise | 10 | dans la plage : 10 · à moins de 2 mm : 5 · à plus de 5 mm : souris **écartée** |
| Prise (fabricant, propriétaire ou source autorisée) | 10 | « Élevé » 10 · « Moyen » 5 · « Faible » : souris **écartée** |
| Bosse | 5 | Palm : avant ou milieu · Claw : milieu ou arrière · Fingertip : ignorée |
| Hauteur des boutons | 5 (10 en Fingertip) | Palm → {High} · Claw → {Low} · Fingertip → {Low, Mid} |

Le total est sur **40** dans les trois prises ; le pourcentage affiché est ce total rapporté à 40 — jamais
une probabilité. Une donnée **inconnue** ne rapporte aucun point et n'est jamais devinée. Quand la seule
donnée manquante est la hauteur des boutons, la souris est quand même classée (« score partiel », signalé
à l'écran) ; toute autre donnée manquante la met « en attente », hors classement.

> **Le point faible du calcul** : 18 souris sur 36 n'ont pas de hauteur de boutons. Selon ce qu'elles
> vaudront, le match idéal peut changer pour 27 % des profils (`tools/campagne_boutons.py sensibilite`).
> La campagne EloShapes du 2026-10-15 propose une classe pour 7 d'entre elles et laisse 10 non tranchées ;
> rien n'est publié avant la décision du propriétaire (`docs/audit/MESURE_BOUTONS_2026-10-12.md` §18.1).

### 3.2 Le classement selon le budget — `utils/selection.py`

Le mode ne change **jamais** la note : il choisit parmi les souris proches de la meilleure note.

| Mode | Zone | Ordre dans la zone |
| --- | --- | --- |
| Économique | 5 points sous la meilleure note | la moins chère |
| Qualité/Prix | 2 points | le plus de points par euro |
| Haut de gamme | 2 points | composants documentés (fréquence ≥ 8 000 Hz, capteur haut de gamme) |
| Peu importe le prix | 2 points | la meilleure note, puis capteur > MCU > switchs > fréquence, puis le prix |
| Budget libre | 2 points | la meilleure note, puis la moins chère ; au-dessus du budget : écartée |

### 3.3 Les trois places — `utils/slots.py`

Calcul pur, sans Discord. Dans le classement du mode, sans recalculer aucune note :

1. **Le match idéal** : la tête du classement.
2. **L'alternative** : une autre coque, de préférence moins chère, dans la zone du mode (élargie une fois à
   5 points si la zone ne contient que la même coque).
3. **La troisième place** : « 💸 l'économie » (strictement moins chère que les deux autres, fenêtre de
   5 points), sinon « ➕ l'autre option », sinon « 🔎 autre piste » (la meilleure souris restante).

Trois règles pour toutes les places : jamais deux fois la même coque tant qu'une autre existe ; jamais de
trou ; jamais une place mieux notée que celle du dessus. Quand une règle doit céder faute de candidat, le
banc d'essai compte le cas.

## 4. Le message de résultat — `cogs/finder_flow.py`

Un seul message privé : « 🎯 Votre recommandation » (récapitulatif + trois lignes : nom · poids · prix ·
pourcentage · forme), puis les blocs d'explication — « 📐 Vos repères de taille » (avec « 🧭 Pourquoi ce
choix ? »), l'arrière étroit (thénar petit ou moyen), la bosse et la forme, la variante de Claw, la hauteur
des boutons. Chaque bloc porte une illustration (`assets/images.json`) ; une illustration n'apparaît
qu'**une fois** par message. Sous le message, un lien d'achat par souris affichée.

## 5. Les données

| Fichier | Contenu | Règle |
| --- | --- | --- |
| `data/mouse_db.json` | les 36 souris : cotes, forme, prises, prix, composants, **sources** | chaque valeur renseignée cite une source datée qui la déclare ; inconnu = vide, jamais estimé ; relu à chaque recherche |
| `data/commercial_links.json` | un lien d'achat affilié par souris | boutique officielle, variante figée quand le prix en dépend |
| `assets/images.json` | les illustrations T01–T15 | hébergées par le propriétaire (`IMAGES_BASE_URL`) |

Validation stricte au chargement : `utils/catalog.py`. Prix en euros, relevés sur la boutique officielle,
jamais convertis.

## 6. Les fichiers du bot

| Fichier | Rôle |
| --- | --- |
| `bot.py` | démarrage : intents, cogs, vues durables |
| `config.py` | réglages (`.env`) et chemins |
| `cogs/mouse_finder.py` | la commande `!setup_finder` et le panneau public |
| `cogs/finder_flow.py` | le parcours Discord : étapes, formulaires, message de résultat |
| `utils/matcher.py` | la note sur 40 |
| `utils/selection.py` | le classement selon le budget |
| `utils/slots.py` | les trois places et leurs titres |
| `utils/models.py` | les types (souris, prise, budget…) |
| `utils/catalog.py` | chargement et validation du catalogue |
| `utils/session.py` | les parcours en cours (mémoire + fichier, expiration) |
| `utils/validation.py` | les bornes des saisies |
| `utils/assets.py` | les adresses des illustrations |

## 7. Vérifier que tout est sain

```bash
.venv/bin/python -m pytest -q                 # la suite complète
.venv/bin/python tools/qa_flow_matrix.py      # 21 736 profils, toutes les règles et limites Discord
.venv/bin/python tools/check_deployment.py    # fichiers, jeton, catalogue (sur le serveur)
.venv/bin/python tools/check_links.py         # liens et prix contre les boutiques (réseau requis)
```

Avant de mesurer quoi que ce soit : `tools/check_bytecode.py` (le banc refuse de tourner sur du code
compilé périmé). Après une modification du code des trois places : `tools/flow_effect.py` ; des données :
`tools/db_effect.py`.

## 8. Où est l'histoire

- `docs/audit/AUDIT.md` : chaque défaut trouvé (C1 → C107), sa preuve, sa correction.
- `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` : mise en ligne, et §12 : ce qui a changé, fichier par fichier.
- `docs/audit/ROBUSTESSE_2026-10-12.md` : le journal détaillé des passes.
- `docs/MASTER_PROMPT_AZEMOUSE.md` et `docs/REPORTE_DESIGN.md` : le cahier des charges et la charte.
