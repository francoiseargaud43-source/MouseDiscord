# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, troisième place — intitulée « 💸 L'économie » quand elle est moins chère que les deux autres, « ➕ L'autre option » sinon). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 252** sur 18522 (1.4 %).
  - budget inférieur à la souris qui convient la moins chère : 252
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **0**
- **Profils où DEUX places montrent la même coque : 1095** (5.9 %).
  C'est le repli documenté de `result_slots()` : quand la zone ne contient rien d'autre, une place reprend la même coque plutôt que de disparaître — mesuré, jamais supposé. Depuis la décision du 2026-10-12, la préférence « jamais deux fois la même coque » vaut pour les TROIS places : la troisième ne prend une variante déjà affichée que si aucune autre coque n'existe dans sa fenêtre. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 609 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 335 profils
  - `atk_f1_ultimate` + `atk_f1_v2` : 121 profils
  - `atk_a9_nb` + `atk_a9_ultimate` : 30 profils
  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas d'autre coque à prix égal ou inférieur.

## Nombre de fois où chaque souris est recommandée

- **Places remplies** : 0 place(s) : 252 · 1 place(s) : 2242 · 2 place(s) : 2295 · 3 place(s) : 13733 — dont **13733 profils à trois places** (74.14 % de la grille). Troisième place : « 💸 L'économie » 4233 fois, « ➕ L'autre option » 10505 fois. Le libellé suit le prix réel (décision du propriétaire du 2026-10-12) : la place reste remplie même quand plus rien n'est moins cher, et elle ne ment pas sur son rôle.

| Souris | Idéal | Alternative | 3e place | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 3693 | 2034 | 2037 | 7764 | 41.9 % |
| ATK X1 V2 Ultra Max | 4503 | 1668 | 720 | 6891 | 37.2 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2097 | 2142 | 1902 | 6141 | 33.2 % |
| ATK A9 Ultimate | 621 | 1350 | 3055 | 5026 | 27.1 % |
| ATK Blazing Sky F1 V2 | 1254 | 2283 | 1350 | 4887 | 26.4 % |
| ATK A9 Mini | 1515 | 855 | 621 | 2991 | 16.1 % |
| VXE Dragonfly R1 / R1 Pro | 456 | 1002 | 1419 | 2877 | 15.5 % |
| Pulsar X2 v3 Mini | 1017 | 675 | 0 | 1692 | 9.1 % |
| Scyrox V6 | 673 | 287 | 353 | 1313 | 7.1 % |
| ATK A9 Plus 2.0 | 330 | 303 | 534 | 1167 | 6.3 % |
| ATK ZERO | 276 | 465 | 271 | 1012 | 5.5 % |
| VXE MAD R / MAD R Major | 54 | 129 | 801 | 984 | 5.3 % |
| ATK Phantom Ultimate | 246 | 306 | 150 | 702 | 3.8 % |
| Pulsar Xlite v4 Mini | 303 | 330 | 45 | 678 | 3.7 % |
| ATK GHOST Ultimate | 93 | 186 | 363 | 642 | 3.5 % |
| Scyrox V8 / V8S | 229 | 228 | 130 | 587 | 3.2 % |
| ATK Z1 V2 Ultra | 96 | 153 | 252 | 501 | 2.7 % |
| ATK F1 V3 Ultimate | 388 | 30 | 73 | 491 | 2.7 % |
| Pulsar X2A v3 | 135 | 210 | 0 | 345 | 1.9 % |
| Pulsar X2 CrazyLight Mini | 0 | 210 | 125 | 335 | 1.8 % |
| ATK Y9 Ultimate | 0 | 24 | 270 | 294 | 1.6 % |
| Pulsar X2H v3 Mini | 0 | 90 | 90 | 180 | 1.0 % |
| ATK Dragonfly A9 NB Ultra | 138 | 0 | 0 | 138 | 0.7 % |
| ATK U2 V2 Mini | 0 | 6 | 102 | 108 | 0.6 % |
| ATK Fierce X | 27 | 54 | 15 | 96 | 0.5 % |
| ATK GHOST Extreme | 81 | 0 | 0 | 81 | 0.4 % |
| ATK Duckbill | 0 | 3 | 60 | 63 | 0.3 % |
| ATK U2 V2 Ultimate | 45 | 0 | 0 | 45 | 0.2 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**8 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **Pulsar X2 CrazyLight Medium** (`pulsar_x2_crazylight_medium`)
- **Pulsar X2H CrazyLight Mini** (`pulsar_x2h_crazylight_mini`)
- **Pulsar Xlite CrazyLight Medium** (`pulsar_xlite_crazylight_medium`)
- **Pulsar Xlite v4 Large** (`pulsar_xlite_v4_large`)
- **Pulsar Xlite v4 Medium** (`pulsar_xlite_v4_medium`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 11172 | 0 | 7350 | notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 2643 des 11172 profils où elle reste éligible · **une variante de sa coque (ATK A9 Ultimate) est classée devant elle sur 11172 des 11172 profils où elle est notée**, dont 9732 avec ATK A9 Ultimate — coque identique, prix différent |
| ATK Blazing Sky U2 Mini | 5544 | 3780 | 9198 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1131 des 5544 profils où elle reste éligible · **une variante de sa coque (ATK U2 V2 Mini) est classée devant elle sur 5544 des 5544 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **Pulsar X2 v3 Mini** sur 1017 des 4830 profils où elle reste éligible · **une variante de sa coque (Pulsar X2A v3) est classée devant elle sur 4830 des 4830 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2H CrazyLight Mini | 3990 | 2520 | 12012 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **Pulsar X2 v3 Mini** sur 1017 des 3990 profils où elle reste éligible · **une variante de sa coque (Pulsar X2H v3 Mini) est classée devant elle sur 3990 des 3990 profils où elle est notée** — coque identique, prix différent |
| Pulsar Xlite CrazyLight Medium | 5760 | 900 | 11862 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 1161 des 5760 profils où elle reste éligible |
| Pulsar Xlite v4 Large | 1440 | 0 | 17082 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 540 des 1440 profils où elle reste éligible |
| Pulsar Xlite v4 Medium | 5760 | 900 | 11862 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 1161 des 5760 profils où elle reste éligible |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 1792 | 10752 | 5978 | donnée absente : position de la bosse, hauteur des boutons · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1056 des 1792 profils où elle reste éligible |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 717 | 717 | 717 | 717 | 4896 |
| ATK X1 V2 Ultra Max | 909 | 858 | 813 | 843 | 3468 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 660 | 588 | 588 | 588 | 3717 |
| ATK A9 Ultimate | 610 | 631 | 456 | 604 | 2725 |
| ATK Blazing Sky F1 V2 | 674 | 566 | 516 | 243 | 2888 |
| ATK A9 Mini | 402 | 390 | 360 | 423 | 1416 |
| VXE Dragonfly R1 / R1 Pro | 243 | 183 | 183 | 183 | 2085 |
| Pulsar X2 v3 Mini | 252 | 360 | 360 | 360 | 360 |
| Scyrox V6 | 231 | 189 | 294 | 189 | 410 |
| ATK A9 Plus 2.0 | 156 | 162 | 78 | 78 | 693 |
| ATK ZERO | 133 | 196 | 105 | 172 | 406 |
| VXE MAD R / MAD R Major | 159 | 48 | 39 | 42 | 696 |
| ATK Phantom Ultimate | 93 | 141 | 165 | 162 | 141 |
| Pulsar Xlite v4 Mini | 102 | 144 | 144 | 144 | 144 |
| ATK GHOST Ultimate | 99 | 111 | 114 | 72 | 246 |
| Scyrox V8 / V8S | 28 | 76 | 252 | 76 | 155 |
| ATK Z1 V2 Ultra | 75 | 66 | 93 | 51 | 216 |
| ATK F1 V3 Ultimate | 3 | 9 | 53 | 341 | 85 |
| Pulsar X2A v3 | 33 | 78 | 78 | 78 | 78 |
| Pulsar X2 CrazyLight Mini | 67 | 67 | 67 | 67 | 67 |
| ATK Y9 Ultimate | 42 | 42 | 42 | 42 | 126 |
| Pulsar X2H v3 Mini | 36 | 36 | 36 | 36 | 36 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 69 | 69 | 0 |
| ATK U2 V2 Mini | 30 | 6 | 6 | 3 | 63 |
| ATK Fierce X | 12 | 18 | 9 | 18 | 39 |
| ATK GHOST Extreme | 0 | 0 | 0 | 81 | 0 |
| ATK Duckbill | 15 | 9 | 9 | 9 | 21 |
| ATK U2 V2 Ultimate | 0 | 0 | 45 | 0 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 2409 | 2769 | 2586 |
| ATK X1 V2 Ultra Max | 3639 | 3252 | 0 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 3648 | 2493 | 0 |
| ATK A9 Ultimate | 2763 | 1491 | 772 |
| ATK Blazing Sky F1 V2 | 0 | 3186 | 1701 |
| ATK A9 Mini | 2376 | 576 | 39 |
| VXE Dragonfly R1 / R1 Pro | 1140 | 1737 | 0 |
| Pulsar X2 v3 Mini | 0 | 993 | 699 |
| Scyrox V6 | 381 | 90 | 842 |
| ATK A9 Plus 2.0 | 633 | 534 | 0 |
| ATK ZERO | 6 | 870 | 136 |
| VXE MAD R / MAD R Major | 429 | 555 | 0 |
| ATK Phantom Ultimate | 702 | 0 | 0 |
| Pulsar Xlite v4 Mini | 678 | 0 | 0 |
| ATK GHOST Ultimate | 417 | 225 | 0 |
| Scyrox V8 / V8S | 0 | 477 | 110 |
| ATK Z1 V2 Ultra | 501 | 0 | 0 |
| ATK F1 V3 Ultimate | 0 | 318 | 173 |
| Pulsar X2A v3 | 0 | 345 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 270 | 65 |
| ATK Y9 Ultimate | 147 | 147 | 0 |
| Pulsar X2H v3 Mini | 0 | 180 | 0 |
| ATK Dragonfly A9 NB Ultra | 90 | 48 | 0 |
| ATK U2 V2 Mini | 0 | 108 | 0 |
| ATK Fierce X | 0 | 96 | 0 |
| ATK GHOST Extreme | 6 | 75 | 0 |
| ATK Duckbill | 63 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 45 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 1726 | 1726 | 1726 | 2586 |
| ATK X1 V2 Ultra Max | 2297 | 2297 | 2297 | 0 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2047 | 2047 | 2047 | 0 |
| ATK A9 Ultimate | 1418 | 1418 | 1418 | 772 |
| ATK Blazing Sky F1 V2 | 1062 | 1062 | 1062 | 1701 |
| ATK A9 Mini | 984 | 984 | 984 | 39 |
| VXE Dragonfly R1 / R1 Pro | 959 | 959 | 959 | 0 |
| Pulsar X2 v3 Mini | 331 | 331 | 331 | 699 |
| Scyrox V6 | 157 | 157 | 157 | 842 |
| ATK A9 Plus 2.0 | 389 | 389 | 389 | 0 |
| ATK ZERO | 292 | 292 | 292 | 136 |
| VXE MAD R / MAD R Major | 328 | 328 | 328 | 0 |
| ATK Phantom Ultimate | 234 | 234 | 234 | 0 |
| Pulsar Xlite v4 Mini | 226 | 226 | 226 | 0 |
| ATK GHOST Ultimate | 214 | 214 | 214 | 0 |
| Scyrox V8 / V8S | 159 | 159 | 159 | 110 |
| ATK Z1 V2 Ultra | 167 | 167 | 167 | 0 |
| ATK F1 V3 Ultimate | 106 | 106 | 106 | 173 |
| Pulsar X2A v3 | 115 | 115 | 115 | 0 |
| Pulsar X2 CrazyLight Mini | 90 | 90 | 90 | 65 |
| ATK Y9 Ultimate | 98 | 98 | 98 | 0 |
| Pulsar X2H v3 Mini | 60 | 60 | 60 | 0 |
| ATK Dragonfly A9 NB Ultra | 46 | 46 | 46 | 0 |
| ATK U2 V2 Mini | 36 | 36 | 36 | 0 |
| ATK Fierce X | 32 | 32 | 32 | 0 |
| ATK GHOST Extreme | 27 | 27 | 27 | 0 |
| ATK Duckbill | 21 | 21 | 21 | 0 |
| ATK U2 V2 Ultimate | 15 | 15 | 15 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 27.0/40 | 40/40 | 10/40 | 12474 |
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 10752 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 22.6/40 | 35/40 | 15/40 | 12096 |
| ATK A9 Ultimate | 24.4/40 | 40/40 | 15/40 | 12768 |
| ATK Blazing Sky F1 V2 | 32.5/40 | 40/40 | 20/40 | 7056 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 35/40 | 10/40 | 14742 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| ATK ZERO | 26.1/40 | 40/40 | 10/40 | 9828 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| ATK Phantom Ultimate | 25.9/40 | 35/40 | 10/40 | 7770 |
| Pulsar Xlite v4 Mini | 22.1/40 | 35/40 | 10/40 | 6510 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 6720 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 6174 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 5376 |
| Pulsar X2H v3 Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| ATK Dragonfly A9 NB Ultra | 25.1/40 | 40/40 | 15/40 | 9576 |
| ATK U2 V2 Mini | 22.9/40 | 35/40 | 5/40 | 6468 |
| ATK Fierce X | 27.2/40 | 35/40 | 15/40 | 5544 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Duckbill | 18.5/40 | 30/40 | 10/40 | 6678 |
| ATK U2 V2 Ultimate | 20.1/40 | 35/40 | 10/40 | 9408 |
| ATK A9 Air | 24.4/40 | 40/40 | 15/40 | 11172 |
| ATK Blazing Sky U2 Mini | 22.9/40 | 35/40 | 5/40 | 5544 |
| Pulsar X2 CrazyLight Medium | 30.7/40 | 40/40 | 20/40 | 4830 |
| Pulsar X2H CrazyLight Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| Pulsar Xlite CrazyLight Medium | 20.4/40 | 30/40 | 15/40 | 5760 |
| Pulsar Xlite v4 Large | 18.8/40 | 25/40 | 15/40 | 1440 |
| Pulsar Xlite v4 Medium | 20.4/40 | 30/40 | 15/40 | 5760 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 19.4/40 | 30/40 | 10/40 | 1792 |

## Ce qui manque, souris par souris (à trouver, jamais à inventer)

- **Sans aucune compatibilité de prise publiée (0 souris)** : jamais classables, donc jamais proposées, quel que soit le profil. Seule une publication du fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.
- **Sans position de bosse publiée (1 souris)** : « à vérifier » dès que la prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`)
- **Sans hauteur de boutons documentée (18 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée. Depuis le 2026-10-12, les sources tierces sont autorisées pour les données que le fabricant ne publie pas.

