# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, troisième place — intitulée « 💸 L'économie » quand elle est moins chère que les deux autres, « ➕ L'autre option » sinon). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 252** sur 18522 (1.4 %).
  - budget inférieur à la souris qui convient la moins chère : 252
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **0**
- **Profils où DEUX places montrent la même coque : 1127** (6.1 %).
  C'est le repli documenté de `result_slots()` : quand la zone ne contient rien d'autre, une place reprend la même coque plutôt que de disparaître — mesuré, jamais supposé. Depuis la décision du 2026-10-12, la préférence « jamais deux fois la même coque » vaut pour les TROIS places : la troisième ne prend une variante déjà affichée que si aucune autre coque n'existe dans sa fenêtre. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 651 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 210 profils
  - `atk_f1_ultimate` + `atk_f1_v2` : 164 profils
  - `pulsar_x2h_crazylight_mini` + `pulsar_x2h_v3_mini` : 96 profils
  - `atk_ghost_extreme` + `atk_ghost_ultimate` : 6 profils
  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas d'autre coque à prix égal ou inférieur.

## Nombre de fois où chaque souris est recommandée

- **Places remplies** : 0 place(s) : 252 · 1 place(s) : 1086 · 2 place(s) : 1134 · 3 place(s) : 16050 — dont **16050 profils à trois places** (86.65 % de la grille). Troisième place : « ➕ L'autre option » 9734 fois · « 💸 L'économie » 4716 fois · « 🔎 Autre piste » 1600 fois. Le libellé suit le prix réel (décision du propriétaire du 2026-10-12) : la place reste remplie même quand plus rien n'est moins cher, et elle ne ment pas sur son rôle. Deuxième place : « 🥈 L'alternative » 14974 fois, « 🔎 Autre piste » 2210 fois (dernier palier : la zone du mode ne contenait rien de comparable, la ligne le dit).

| Souris | Idéal | Alternative | 3e place | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 3693 | 2226 | 2469 | 8388 | 45.3 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2097 | 2283 | 2196 | 6576 | 35.5 % |
| ATK X1 V2 Ultra Max | 4503 | 1395 | 660 | 6558 | 35.4 % |
| ATK Blazing Sky F1 V2 | 1254 | 2504 | 1123 | 4881 | 26.4 % |
| ATK A9 Plus 2.0 | 450 | 2118 | 2257 | 4825 | 26.1 % |
| VXE Dragonfly R1 / R1 Pro | 456 | 1752 | 1931 | 4139 | 22.3 % |
| ATK A9 Mini | 1515 | 807 | 605 | 2927 | 15.8 % |
| ATK A9 Ultimate | 588 | 0 | 942 | 1530 | 8.3 % |
| Pulsar X2 v3 Mini | 1017 | 500 | 3 | 1520 | 8.2 % |
| Scyrox V6 | 673 | 290 | 444 | 1407 | 7.6 % |
| VXE MAD R / MAD R Major | 54 | 336 | 927 | 1317 | 7.1 % |
| ATK ZERO | 267 | 450 | 408 | 1125 | 6.1 % |
| ATK Phantom Ultimate | 246 | 327 | 222 | 795 | 4.3 % |
| ATK GHOST Ultimate | 93 | 354 | 279 | 726 | 3.9 % |
| ATK Z1 V2 Ultra | 111 | 204 | 411 | 726 | 3.9 % |
| Scyrox V8 / V8S | 229 | 249 | 169 | 647 | 3.5 % |
| Pulsar Xlite v4 Mini | 303 | 288 | 39 | 630 | 3.4 % |
| ATK Y9 Ultimate | 0 | 354 | 207 | 561 | 3.0 % |
| ATK F1 V3 Ultimate | 388 | 33 | 125 | 546 | 2.9 % |
| Pulsar X2A v3 | 135 | 177 | 3 | 315 | 1.7 % |
| ATK U2 V2 Ultimate | 90 | 15 | 120 | 225 | 1.2 % |
| Pulsar X2H v3 Mini | 0 | 108 | 108 | 216 | 1.2 % |
| Pulsar X2 CrazyLight Mini | 0 | 210 | 0 | 210 | 1.1 % |
| Pulsar Xlite v4 Large | 0 | 90 | 90 | 180 | 1.0 % |
| ATK U2 V2 Mini | 0 | 33 | 114 | 147 | 0.8 % |
| ATK Fierce X | 27 | 51 | 27 | 105 | 0.6 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 96 | 96 | 0.5 % |
| ATK GHOST Extreme | 81 | 0 | 6 | 87 | 0.5 % |
| ATK Duckbill | 0 | 27 | 57 | 84 | 0.5 % |
| Pulsar Xlite v4 Medium | 0 | 3 | 9 | 12 | 0.1 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 3 | 3 | 0.0 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**5 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **ATK Dragonfly A9 NB Ultra** (`atk_a9_nb`)
- **Pulsar X2 CrazyLight Medium** (`pulsar_x2_crazylight_medium`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 11172 | 0 | 7350 | notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 2643 des 11172 profils où elle reste éligible · **une variante de sa coque (ATK A9 Plus 2.0) est classée devant elle sur 11172 des 11172 profils où elle est notée**, dont 8490 avec ATK A9 Plus 2.0 — coque identique, prix différent |
| ATK Blazing Sky U2 Mini | 5544 | 3780 | 9198 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1131 des 5544 profils où elle reste éligible · **une variante de sa coque (ATK U2 V2 Mini) est classée devant elle sur 5544 des 5544 profils où elle est notée** — coque identique, prix différent |
| ATK Dragonfly A9 NB Ultra | 9576 | 0 | 8946 | notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 2127 des 9576 profils où elle reste éligible · **une variante de sa coque (ATK A9 Plus 2.0) est classée devant elle sur 9576 des 9576 profils où elle est notée**, dont 7146 avec ATK A9 Plus 2.0 — coque identique, prix différent |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **Pulsar X2 v3 Mini** sur 1017 des 4830 profils où elle reste éligible · **une variante de sa coque (Pulsar X2A v3) est classée devant elle sur 4830 des 4830 profils où elle est notée** — coque identique, prix différent |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 1792 | 10752 | 5978 | donnée absente : position de la bosse, hauteur des boutons · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1056 des 1792 profils où elle reste éligible |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 798 | 780 | 780 | 780 | 5250 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 639 | 594 | 594 | 594 | 4155 |
| ATK X1 V2 Ultra Max | 564 | 858 | 813 | 843 | 3480 |
| ATK Blazing Sky F1 V2 | 598 | 585 | 529 | 256 | 2913 |
| ATK A9 Plus 2.0 | 555 | 669 | 306 | 336 | 2959 |
| VXE Dragonfly R1 / R1 Pro | 267 | 183 | 183 | 183 | 3323 |
| ATK A9 Mini | 327 | 390 | 360 | 423 | 1427 |
| ATK A9 Ultimate | 216 | 141 | 312 | 378 | 483 |
| Pulsar X2 v3 Mini | 80 | 360 | 360 | 360 | 360 |
| Scyrox V6 | 186 | 213 | 318 | 213 | 477 |
| VXE MAD R / MAD R Major | 315 | 48 | 39 | 42 | 873 |
| ATK ZERO | 192 | 203 | 120 | 182 | 428 |
| ATK Phantom Ultimate | 150 | 150 | 174 | 171 | 150 |
| ATK GHOST Ultimate | 153 | 114 | 117 | 75 | 267 |
| ATK Z1 V2 Ultra | 150 | 84 | 111 | 81 | 300 |
| Scyrox V8 / V8S | 84 | 76 | 252 | 76 | 159 |
| Pulsar Xlite v4 Mini | 42 | 147 | 147 | 147 | 147 |
| ATK Y9 Ultimate | 129 | 72 | 72 | 72 | 216 |
| ATK F1 V3 Ultimate | 33 | 9 | 53 | 341 | 110 |
| Pulsar X2A v3 | 3 | 78 | 78 | 78 | 78 |
| ATK U2 V2 Ultimate | 135 | 0 | 45 | 45 | 0 |
| Pulsar X2H v3 Mini | 72 | 36 | 36 | 36 | 36 |
| Pulsar X2 CrazyLight Mini | 42 | 42 | 42 | 42 | 42 |
| Pulsar Xlite v4 Large | 36 | 36 | 36 | 36 | 36 |
| ATK U2 V2 Mini | 69 | 6 | 6 | 3 | 63 |
| ATK Fierce X | 21 | 18 | 9 | 18 | 39 |
| Pulsar X2H CrazyLight Mini | 24 | 18 | 18 | 18 | 18 |
| ATK GHOST Extreme | 6 | 0 | 0 | 81 | 0 |
| ATK Duckbill | 21 | 12 | 12 | 12 | 27 |
| Pulsar Xlite v4 Medium | 12 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 3 | 0 | 0 | 0 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 2817 | 2925 | 2646 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 3894 | 2682 | 0 |
| ATK X1 V2 Ultra Max | 3486 | 3072 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 3150 | 1731 |
| ATK A9 Plus 2.0 | 2730 | 1641 | 454 |
| VXE Dragonfly R1 / R1 Pro | 1695 | 2046 | 398 |
| ATK A9 Mini | 2259 | 630 | 38 |
| ATK A9 Ultimate | 702 | 411 | 417 |
| Pulsar X2 v3 Mini | 0 | 861 | 659 |
| Scyrox V6 | 561 | 93 | 753 |
| VXE MAD R / MAD R Major | 594 | 723 | 0 |
| ATK ZERO | 21 | 939 | 165 |
| ATK Phantom Ultimate | 795 | 0 | 0 |
| ATK GHOST Ultimate | 501 | 225 | 0 |
| ATK Z1 V2 Ultra | 726 | 0 | 0 |
| Scyrox V8 / V8S | 0 | 516 | 131 |
| Pulsar Xlite v4 Mini | 630 | 0 | 0 |
| ATK Y9 Ultimate | 288 | 273 | 0 |
| ATK F1 V3 Ultimate | 0 | 324 | 222 |
| Pulsar X2A v3 | 0 | 315 | 0 |
| ATK U2 V2 Ultimate | 33 | 192 | 0 |
| Pulsar X2H v3 Mini | 0 | 216 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 180 | 30 |
| Pulsar Xlite v4 Large | 90 | 90 | 0 |
| ATK U2 V2 Mini | 0 | 147 | 0 |
| ATK Fierce X | 0 | 105 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 96 | 0 |
| ATK GHOST Extreme | 12 | 75 | 0 |
| ATK Duckbill | 84 | 0 | 0 |
| Pulsar Xlite v4 Medium | 9 | 3 | 0 |
| Pulsar Xlite CrazyLight Medium | 3 | 0 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 1914 | 1914 | 1914 | 2646 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2192 | 2192 | 2192 | 0 |
| ATK X1 V2 Ultra Max | 2186 | 2186 | 2186 | 0 |
| ATK Blazing Sky F1 V2 | 1050 | 1050 | 1050 | 1731 |
| ATK A9 Plus 2.0 | 1457 | 1457 | 1457 | 454 |
| VXE Dragonfly R1 / R1 Pro | 1247 | 1247 | 1247 | 398 |
| ATK A9 Mini | 963 | 963 | 963 | 38 |
| ATK A9 Ultimate | 371 | 371 | 371 | 417 |
| Pulsar X2 v3 Mini | 287 | 287 | 287 | 659 |
| Scyrox V6 | 218 | 218 | 218 | 753 |
| VXE MAD R / MAD R Major | 439 | 439 | 439 | 0 |
| ATK ZERO | 320 | 320 | 320 | 165 |
| ATK Phantom Ultimate | 265 | 265 | 265 | 0 |
| ATK GHOST Ultimate | 242 | 242 | 242 | 0 |
| ATK Z1 V2 Ultra | 242 | 242 | 242 | 0 |
| Scyrox V8 / V8S | 172 | 172 | 172 | 131 |
| Pulsar Xlite v4 Mini | 210 | 210 | 210 | 0 |
| ATK Y9 Ultimate | 187 | 187 | 187 | 0 |
| ATK F1 V3 Ultimate | 108 | 108 | 108 | 222 |
| Pulsar X2A v3 | 105 | 105 | 105 | 0 |
| ATK U2 V2 Ultimate | 75 | 75 | 75 | 0 |
| Pulsar X2H v3 Mini | 72 | 72 | 72 | 0 |
| Pulsar X2 CrazyLight Mini | 60 | 60 | 60 | 30 |
| Pulsar Xlite v4 Large | 60 | 60 | 60 | 0 |
| ATK U2 V2 Mini | 49 | 49 | 49 | 0 |
| ATK Fierce X | 35 | 35 | 35 | 0 |
| Pulsar X2H CrazyLight Mini | 32 | 32 | 32 | 0 |
| ATK GHOST Extreme | 29 | 29 | 29 | 0 |
| ATK Duckbill | 28 | 28 | 28 | 0 |
| Pulsar Xlite v4 Medium | 4 | 4 | 4 | 0 |
| Pulsar Xlite CrazyLight Medium | 1 | 1 | 1 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 27.0/40 | 40/40 | 10/40 | 12474 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 22.6/40 | 35/40 | 15/40 | 12096 |
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 10752 |
| ATK Blazing Sky F1 V2 | 32.5/40 | 40/40 | 20/40 | 7056 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 35/40 | 10/40 | 14742 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| ATK A9 Ultimate | 25.1/40 | 40/40 | 15/40 | 11172 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| ATK ZERO | 26.1/40 | 40/40 | 10/40 | 9828 |
| ATK Phantom Ultimate | 25.9/40 | 35/40 | 10/40 | 7770 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 6720 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| Pulsar Xlite v4 Mini | 22.1/40 | 35/40 | 10/40 | 6510 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 5376 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 6174 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK U2 V2 Ultimate | 20.1/40 | 35/40 | 10/40 | 9408 |
| Pulsar X2H v3 Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Pulsar Xlite v4 Large | 18.8/40 | 25/40 | 15/40 | 1440 |
| ATK U2 V2 Mini | 22.9/40 | 35/40 | 5/40 | 6468 |
| ATK Fierce X | 27.2/40 | 35/40 | 15/40 | 5544 |
| Pulsar X2H CrazyLight Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Duckbill | 18.5/40 | 30/40 | 10/40 | 6678 |
| Pulsar Xlite v4 Medium | 20.4/40 | 30/40 | 15/40 | 5760 |
| Pulsar Xlite CrazyLight Medium | 20.4/40 | 30/40 | 15/40 | 5760 |
| ATK A9 Air | 25.1/40 | 40/40 | 15/40 | 11172 |
| ATK Blazing Sky U2 Mini | 22.9/40 | 35/40 | 5/40 | 5544 |
| ATK Dragonfly A9 NB Ultra | 25.1/40 | 40/40 | 15/40 | 9576 |
| Pulsar X2 CrazyLight Medium | 30.7/40 | 40/40 | 20/40 | 4830 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 19.4/40 | 30/40 | 10/40 | 1792 |

## Ce qui manque, souris par souris (à trouver, jamais à inventer)

- **Sans aucune compatibilité de prise publiée (0 souris)** : jamais classables, donc jamais proposées, quel que soit le profil. Seule une publication du fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.
- **Sans position de bosse publiée (1 souris)** : « à vérifier » dès que la prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`)
- **Sans hauteur de boutons documentée (18 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée. Depuis le 2026-10-12, les sources tierces sont autorisées pour les données que le fabricant ne publie pas.

