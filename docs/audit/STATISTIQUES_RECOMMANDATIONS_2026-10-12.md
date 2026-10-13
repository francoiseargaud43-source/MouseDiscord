# Statistiques de recommandation — 2026-10-12

Rapport **régénéré le 2026-10-13** sur le catalogue `data/mouse_db.json` du même jour : chaque régénération remplace les chiffres ci-dessous, la date du titre reste celle de la définition de la grille.

Grille : **420 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, troisième place — intitulée « 💸 L'économie » quand elle est moins chère que les deux autres, « ➕ L'autre option » sinon). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 0** sur 420 (0.0 %).
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **0**
- **Profils où DEUX places montrent la même coque : 8** (1.9 %).
  C'est le repli documenté de `result_slots()` : quand la zone ne contient rien d'autre, une place reprend la même coque plutôt que de disparaître — mesuré, jamais supposé. Depuis la décision du 2026-10-12, la préférence « jamais deux fois la même coque » vaut pour les TROIS places : la troisième ne prend une variante déjà affichée que si aucune autre coque n'existe dans sa fenêtre. Les paires concernées, par fréquence :
  - `atk_f1_ultimate` + `atk_f1_v2` : 8 profils
  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas d'autre coque à prix égal ou inférieur.

## Nombre de fois où chaque souris est recommandée

- **Places remplies** : 0 place(s) : 0 · 1 place(s) : 0 · 2 place(s) : 0 · 3 place(s) : 420 — dont **420 profils à trois places** (100.00 % de la grille). Troisième place : « ➕ L'autre option » 234 fois · « 💸 L'économie » 159 fois · « 🔎 Autre piste » 27 fois. Le libellé suit le prix réel (décision du propriétaire du 2026-10-12) : la place reste remplie même quand plus rien n'est moins cher, et elle ne ment pas sur son rôle. Deuxième place : « 🥈 L'alternative » 378 fois, « 🔎 Autre piste » 42 fois (dernier palier : la zone du mode ne contenait rien de comparable, la ligne le dit).

| Souris | Idéal | Alternative | 3e place | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 43 | 53 | 66 | 162 | 38.6 % |
| ATK A9 Mini | 84 | 45 | 24 | 153 | 36.4 % |
| ATK Blazing Sky F1 V2 | 51 | 76 | 15 | 142 | 33.8 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 36 | 21 | 81 | 138 | 32.9 % |
| ATK A9 Plus 2.0 | 18 | 54 | 23 | 95 | 22.6 % |
| ATK X1 V2 Ultra Max | 48 | 27 | 15 | 90 | 21.4 % |
| VXE MAD R / MAD R Major | 3 | 24 | 48 | 75 | 17.9 % |
| ATK F1 V3 Ultimate | 41 | 6 | 2 | 49 | 11.7 % |
| ATK ZERO | 6 | 21 | 22 | 49 | 11.7 % |
| ATK GHOST Ultimate | 0 | 15 | 27 | 42 | 10.0 % |
| ATK Phantom Ultimate | 9 | 21 | 12 | 42 | 10.0 % |
| ATK Z1 V2 Ultra | 3 | 12 | 27 | 42 | 10.0 % |
| Pulsar X2 v3 Mini | 15 | 27 | 0 | 42 | 10.0 % |
| Scyrox V6 | 30 | 0 | 12 | 42 | 10.0 % |
| Scyrox V8 / V8S | 15 | 6 | 12 | 33 | 7.9 % |
| ATK A9 Ultimate | 15 | 0 | 13 | 28 | 6.7 % |
| Pulsar Xlite v4 Mini | 0 | 9 | 3 | 12 | 2.9 % |
| ATK Y9 Ultimate | 0 | 0 | 9 | 9 | 2.1 % |
| VXE Dragonfly R1 / R1 Pro | 0 | 3 | 6 | 9 | 2.1 % |
| ATK GHOST Extreme | 3 | 0 | 0 | 3 | 0.7 % |
| ATK U2 V2 Mini | 0 | 0 | 3 | 3 | 0.7 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Fierce X | 0 | 0 | 0 | 0 | 0.0 % |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2A v3 | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H v3 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**15 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **ATK Dragonfly A9 NB Ultra** (`atk_a9_nb`)
- **ATK Duckbill** (`atk_duckbill`)
- **ATK Fierce X** (`atk_fierce_x`)
- **ATK U2 V2 Ultimate** (`atk_u2_v2_ultimate`)
- **Pulsar X2 CrazyLight Medium** (`pulsar_x2_crazylight_medium`)
- **Pulsar X2 CrazyLight Mini** (`pulsar_x2_crazylight_mini`)
- **Pulsar X2A v3** (`pulsar_x2a_v3_medium`)
- **Pulsar X2H CrazyLight Mini** (`pulsar_x2h_crazylight_mini`)
- **Pulsar X2H v3 Mini** (`pulsar_x2h_v3_mini`)
- **Pulsar Xlite CrazyLight Medium** (`pulsar_xlite_crazylight_medium`)
- **Pulsar Xlite v4 Large** (`pulsar_xlite_v4_large`)
- **Pulsar Xlite v4 Medium** (`pulsar_xlite_v4_medium`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 420 | 0 | 0 | notée, jamais affichée : la 1re place revient à **ATK A9 Mini** sur 84 des 420 profils où elle reste éligible · **une variante de sa coque (ATK A9 Plus 2.0) est classée devant elle sur 420 des 420 profils où elle est notée**, dont 318 avec ATK A9 Plus 2.0 — coque identique, prix différent |
| ATK Blazing Sky U2 Mini | 192 | 144 | 84 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **ATK F1 V3 Ultimate** sur 41 des 192 profils où elle reste éligible · **une variante de sa coque (ATK U2 V2 Mini) est classée devant elle sur 192 des 192 profils où elle est notée** — coque identique, prix différent |
| ATK Dragonfly A9 NB Ultra | 336 | 0 | 84 | notée, jamais affichée : la 1re place revient à **ATK A9 Mini** sur 66 des 336 profils où elle reste éligible · **une variante de sa coque (ATK A9 Plus 2.0) est classée devant elle sur 336 des 336 profils où elle est notée**, dont 246 avec ATK A9 Plus 2.0 — coque identique, prix différent |
| ATK Duckbill | 336 | 0 | 84 | donnée absente : hauteur des boutons · notée, jamais affichée : la 1re place revient à **ATK A9 Mini** sur 66 des 336 profils où elle reste éligible |
| ATK Fierce X | 192 | 144 | 84 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **ATK F1 V3 Ultimate** sur 41 des 192 profils où elle reste éligible |
| ATK U2 V2 Ultimate | 360 | 60 | 0 | donnée absente : prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK A9 Mini** sur 84 des 360 profils où elle reste éligible |
| Pulsar X2 CrazyLight Medium | 192 | 144 | 84 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **ATK F1 V3 Ultimate** sur 41 des 192 profils où elle reste éligible · **une variante de sa coque (Pulsar X2A v3) est classée devant elle sur 192 des 192 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2 CrazyLight Mini | 156 | 108 | 156 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **ATK Blazing Sky F1 V2** sur 30 des 156 profils où elle reste éligible · **une variante de sa coque (Pulsar X2 v3 Mini) est classée devant elle sur 156 des 156 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2A v3 | 192 | 144 | 84 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **ATK F1 V3 Ultimate** sur 41 des 192 profils où elle reste éligible |
| Pulsar X2H CrazyLight Mini | 156 | 108 | 156 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **ATK Blazing Sky F1 V2** sur 30 des 156 profils où elle reste éligible · **une variante de sa coque (Pulsar X2H v3 Mini) est classée devant elle sur 156 des 156 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2H v3 Mini | 156 | 108 | 156 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **ATK Blazing Sky F1 V2** sur 30 des 156 profils où elle reste éligible |
| Pulsar Xlite CrazyLight Medium | 288 | 32 | 100 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK A9 Mini** sur 66 des 288 profils où elle reste éligible |
| Pulsar Xlite v4 Large | 0 | 0 | 420 | donnée absente : hauteur des boutons, prise Fingertip · jamais notée : écartée par une règle éliminatoire, un budget ou un prix |
| Pulsar Xlite v4 Medium | 288 | 32 | 100 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK A9 Mini** sur 66 des 288 profils où elle reste éligible |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 45 | 270 | 105 | donnée absente : position de la bosse, hauteur des boutons · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 21 des 45 profils où elle reste éligible |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 30 | 30 | 30 | 30 | 42 |
| ATK A9 Mini | 24 | 30 | 27 | 33 | 39 |
| ATK Blazing Sky F1 V2 | 33 | 36 | 26 | 5 | 42 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 30 | 27 | 27 | 27 | 27 |
| ATK A9 Plus 2.0 | 18 | 24 | 12 | 12 | 29 |
| ATK X1 V2 Ultra Max | 12 | 21 | 15 | 21 | 21 |
| VXE MAD R / MAD R Major | 24 | 9 | 9 | 9 | 24 |
| ATK F1 V3 Ultimate | 0 | 3 | 10 | 31 | 5 |
| ATK ZERO | 17 | 10 | 9 | 13 | 0 |
| ATK GHOST Ultimate | 12 | 12 | 9 | 9 | 0 |
| ATK Phantom Ultimate | 12 | 9 | 9 | 12 | 0 |
| ATK Z1 V2 Ultra | 9 | 9 | 9 | 6 | 9 |
| Pulsar X2 v3 Mini | 0 | 14 | 14 | 14 | 0 |
| Scyrox V6 | 3 | 9 | 21 | 9 | 0 |
| Scyrox V8 / V8S | 9 | 4 | 16 | 4 | 0 |
| ATK A9 Ultimate | 4 | 2 | 6 | 11 | 5 |
| Pulsar Xlite v4 Mini | 3 | 3 | 3 | 3 | 0 |
| ATK Y9 Ultimate | 9 | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 3 | 0 | 0 | 0 | 6 |
| ATK GHOST Extreme | 0 | 0 | 0 | 3 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 3 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2A v3 | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H v3 Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 51 | 51 | 60 |
| ATK A9 Mini | 96 | 54 | 3 |
| ATK Blazing Sky F1 V2 | 0 | 105 | 37 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 75 | 63 | 0 |
| ATK A9 Plus 2.0 | 57 | 36 | 2 |
| ATK X1 V2 Ultra Max | 57 | 33 | 0 |
| VXE MAD R / MAD R Major | 27 | 48 | 0 |
| ATK F1 V3 Ultimate | 0 | 42 | 7 |
| ATK ZERO | 3 | 39 | 7 |
| ATK GHOST Ultimate | 39 | 3 | 0 |
| ATK Phantom Ultimate | 42 | 0 | 0 |
| ATK Z1 V2 Ultra | 42 | 0 | 0 |
| Pulsar X2 v3 Mini | 0 | 18 | 24 |
| Scyrox V6 | 15 | 6 | 21 |
| Scyrox V8 / V8S | 0 | 27 | 6 |
| ATK A9 Ultimate | 12 | 3 | 13 |
| Pulsar Xlite v4 Mini | 12 | 0 | 0 |
| ATK Y9 Ultimate | 6 | 3 | 0 |
| VXE Dragonfly R1 / R1 Pro | 6 | 3 | 0 |
| ATK GHOST Extreme | 0 | 3 | 0 |
| ATK U2 V2 Mini | 0 | 3 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 0 | 0 |
| Pulsar X2A v3 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 |
| Pulsar X2H v3 Mini | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 34 | 34 | 34 | 60 |
| ATK A9 Mini | 50 | 50 | 50 | 3 |
| ATK Blazing Sky F1 V2 | 35 | 35 | 35 | 37 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 46 | 46 | 46 | 0 |
| ATK A9 Plus 2.0 | 31 | 31 | 31 | 2 |
| ATK X1 V2 Ultra Max | 30 | 30 | 30 | 0 |
| VXE MAD R / MAD R Major | 25 | 25 | 25 | 0 |
| ATK F1 V3 Ultimate | 14 | 14 | 14 | 7 |
| ATK ZERO | 14 | 14 | 14 | 7 |
| ATK GHOST Ultimate | 14 | 14 | 14 | 0 |
| ATK Phantom Ultimate | 14 | 14 | 14 | 0 |
| ATK Z1 V2 Ultra | 14 | 14 | 14 | 0 |
| Pulsar X2 v3 Mini | 6 | 6 | 6 | 24 |
| Scyrox V6 | 7 | 7 | 7 | 21 |
| Scyrox V8 / V8S | 9 | 9 | 9 | 6 |
| ATK A9 Ultimate | 5 | 5 | 5 | 13 |
| Pulsar Xlite v4 Mini | 4 | 4 | 4 | 0 |
| ATK Y9 Ultimate | 3 | 3 | 3 | 0 |
| VXE Dragonfly R1 / R1 Pro | 3 | 3 | 3 | 0 |
| ATK GHOST Extreme | 1 | 1 | 1 | 0 |
| ATK U2 V2 Mini | 1 | 1 | 1 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar X2A v3 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar X2H v3 Mini | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 27.5/40 | 40/40 | 15/40 | 330 |
| ATK A9 Mini | 29.8/40 | 35/40 | 25/40 | 420 |
| ATK Blazing Sky F1 V2 | 33.8/40 | 40/40 | 25/40 | 240 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 21.7/40 | 30/40 | 15/40 | 360 |
| ATK A9 Plus 2.0 | 24.7/40 | 35/40 | 15/40 | 420 |
| ATK X1 V2 Ultra Max | 23.3/40 | 30/40 | 15/40 | 270 |
| VXE MAD R / MAD R Major | 24.2/40 | 35/40 | 15/40 | 360 |
| ATK F1 V3 Ultimate | 33.8/40 | 40/40 | 25/40 | 240 |
| ATK ZERO | 27.4/40 | 40/40 | 15/40 | 336 |
| ATK GHOST Ultimate | 27.4/40 | 35/40 | 20/40 | 336 |
| ATK Phantom Ultimate | 27.7/40 | 35/40 | 15/40 | 336 |
| ATK Z1 V2 Ultra | 20.0/40 | 30/40 | 10/40 | 240 |
| Pulsar X2 v3 Mini | 36.0/40 | 40/40 | 30/40 | 156 |
| Scyrox V6 | 28.9/40 | 40/40 | 20/40 | 336 |
| Scyrox V8 / V8S | 32.1/40 | 40/40 | 25/40 | 192 |
| ATK A9 Ultimate | 25.4/40 | 35/40 | 15/40 | 420 |
| Pulsar Xlite v4 Mini | 21.4/40 | 35/40 | 10/40 | 264 |
| ATK Y9 Ultimate | 20.0/40 | 25/40 | 15/40 | 240 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 30/40 | 10/40 | 420 |
| ATK GHOST Extreme | 27.4/40 | 35/40 | 20/40 | 336 |
| ATK U2 V2 Mini | 24.3/40 | 35/40 | 10/40 | 240 |
| ATK A9 Air | 25.4/40 | 35/40 | 15/40 | 420 |
| ATK Blazing Sky U2 Mini | 24.3/40 | 35/40 | 10/40 | 192 |
| ATK Dragonfly A9 NB Ultra | 25.4/40 | 35/40 | 15/40 | 336 |
| ATK Duckbill | 18.1/40 | 25/40 | 10/40 | 336 |
| ATK Fierce X | 29.3/40 | 35/40 | 20/40 | 192 |
| ATK U2 V2 Ultimate | 19.2/40 | 30/40 | 10/40 | 360 |
| Pulsar X2 CrazyLight Medium | 31.8/40 | 40/40 | 25/40 | 192 |
| Pulsar X2 CrazyLight Mini | 36.0/40 | 40/40 | 30/40 | 156 |
| Pulsar X2A v3 | 31.8/40 | 40/40 | 25/40 | 192 |
| Pulsar X2H CrazyLight Mini | 27.8/40 | 35/40 | 20/40 | 156 |
| Pulsar X2H v3 Mini | 27.8/40 | 35/40 | 20/40 | 156 |
| Pulsar Xlite CrazyLight Medium | 20.0/40 | 25/40 | 15/40 | 288 |
| Pulsar Xlite v4 Large | — | — | — | 0 |
| Pulsar Xlite v4 Medium | 20.0/40 | 25/40 | 15/40 | 288 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 16.7/40 | 25/40 | 10/40 | 45 |

## Ce qui manque, souris par souris (à trouver, jamais à inventer)

- **Sans aucune compatibilité de prise publiée (0 souris)** : jamais classables, donc jamais proposées, quel que soit le profil. Seule une publication du fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.
- **Sans position de bosse publiée (1 souris)** : « à vérifier » dès que la prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`)
- **Sans hauteur de boutons documentée (18 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée. Depuis le 2026-10-12, les sources tierces sont autorisées pour les données que le fabricant ne publie pas.

