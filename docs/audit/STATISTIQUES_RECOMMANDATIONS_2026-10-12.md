# Statistiques de recommandation — 2026-10-12

Rapport **régénéré le 2026-10-14** sur le catalogue `data/mouse_db.json` du même jour : chaque régénération remplace les chiffres ci-dessous, la date du titre reste celle de la définition de la grille.

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, troisième place — intitulée « 💸 L'économie » quand elle est moins chère que les deux autres, « ➕ L'autre option » sinon). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 252** sur 18522 (1.4 %).
  - budget inférieur à la souris qui convient la moins chère : 252
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **0**
- **Profils où DEUX places montrent la même coque : 1367** (7.4 %).
  C'est le repli documenté de `result_slots()` : quand la zone ne contient rien d'autre, une place reprend la même coque plutôt que de disparaître — mesuré, jamais supposé. Depuis la décision du 2026-10-12, la préférence « jamais deux fois la même coque » vaut pour les TROIS places : la troisième ne prend une variante déjà affichée que si aucune autre coque n'existe dans sa fenêtre. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 786 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 210 profils
  - `atk_f1_ultimate` + `atk_f1_v2` : 164 profils
  - `atk_u2` + `atk_u2_v2_ultimate` : 105 profils
  - `pulsar_x2h_crazylight_mini` + `pulsar_x2h_v3_mini` : 96 profils
  - `atk_ghost_extreme` + `atk_ghost_ultimate` : 6 profils
  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas d'autre coque à prix égal ou inférieur.

## Nombre de fois où chaque souris est recommandée

- **Places remplies** : 0 place(s) : 252 · 1 place(s) : 1086 · 2 place(s) : 1134 · 3 place(s) : 16050 — dont **16050 profils à trois places** (86.65 % de la grille). Troisième place : « ➕ L'autre option » 9509 fois · « 💸 L'économie » 4962 fois · « 🔎 Autre piste » 1579 fois. Le libellé suit le prix réel (décision du propriétaire du 2026-10-12) : la place reste remplie même quand plus rien n'est moins cher, et elle ne ment pas sur son rôle. Deuxième place : « 🥈 L'alternative » 15337 fois, « 🔎 Autre piste » 1847 fois (dernier palier : la zone du mode ne contenait rien de comparable, la ligne le dit).

| Souris | Idéal | Alternative | 3e place | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 3693 | 2226 | 2469 | 8388 | 45.3 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2097 | 2190 | 2241 | 6528 | 35.2 % |
| ATK X1 V2 Ultra Max 2.0 | 3204 | 1854 | 1086 | 6144 | 33.2 % |
| ATK A9 Plus | 1794 | 1989 | 2209 | 5992 | 32.4 % |
| ATK Blazing Sky F1 V2 | 1218 | 2249 | 964 | 4431 | 23.9 % |
| VXE Dragonfly R1 / R1 Pro | 456 | 1752 | 1931 | 4139 | 22.3 % |
| ATK A9 Mini | 1515 | 807 | 623 | 2945 | 15.9 % |
| ATK A9 Ultimate | 588 | 120 | 903 | 1611 | 8.7 % |
| Pulsar X2 v3 Mini | 1017 | 500 | 3 | 1520 | 8.2 % |
| Scyrox V6 | 673 | 290 | 444 | 1407 | 7.6 % |
| ATK ZERO | 267 | 459 | 426 | 1152 | 6.2 % |
| VXE MAD R / MAD R Major | 45 | 210 | 765 | 1020 | 5.5 % |
| ATK Phantom Ultimate | 246 | 330 | 219 | 795 | 4.3 % |
| ATK GHOST Ultimate | 93 | 354 | 291 | 738 | 4.0 % |
| ATK Z1 V2 Ultimate | 111 | 219 | 369 | 699 | 3.8 % |
| Scyrox V8 / V8S | 229 | 249 | 169 | 647 | 3.5 % |
| Pulsar Xlite v4 Mini | 303 | 288 | 39 | 630 | 3.4 % |
| ATK F1 V3 Ultimate+ | 388 | 33 | 125 | 546 | 2.9 % |
| ATK Y9 Ultimate | 0 | 351 | 159 | 510 | 2.8 % |
| Pulsar X2A v3 | 135 | 177 | 6 | 318 | 1.7 % |
| Pulsar X2H v3 Mini | 0 | 108 | 108 | 216 | 1.2 % |
| Pulsar X2 CrazyLight Mini | 0 | 210 | 0 | 210 | 1.1 % |
| Pulsar Xlite v4 Large | 0 | 90 | 90 | 180 | 1.0 % |
| ATK U2 V2 Mini | 0 | 33 | 126 | 159 | 0.9 % |
| ATK U2 V2 Ultimate | 90 | 12 | 57 | 159 | 0.9 % |
| ATK Fierce X | 27 | 51 | 27 | 105 | 0.6 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 96 | 96 | 0.5 % |
| ATK GHOST Extreme | 81 | 0 | 6 | 87 | 0.5 % |
| ATK Duckbill | 0 | 27 | 57 | 84 | 0.5 % |
| ATK A9 Air | 0 | 0 | 24 | 24 | 0.1 % |
| Pulsar Xlite v4 Medium | 0 | 6 | 12 | 18 | 0.1 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 6 | 6 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**4 souris sur 36** ne sortent jamais sur cette grille :

- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **ATK Dragonfly A9 NB Ultra** (`atk_a9_nb`)
- **Pulsar X2 CrazyLight Medium** (`pulsar_x2_crazylight_medium`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK Blazing Sky U2 Mini | 5544 | 3780 | 9198 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1131 des 5544 profils où elle reste éligible · **une variante de sa coque (ATK U2 V2 Mini) est classée devant elle sur 5544 des 5544 profils où elle est notée** — coque identique, prix différent |
| ATK Dragonfly A9 NB Ultra | 9576 | 0 | 8946 | notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max 2.0** sur 1284 des 9576 profils où elle reste éligible · **une variante de sa coque (ATK A9 Plus) est classée devant elle sur 9576 des 9576 profils où elle est notée**, dont 7146 avec ATK A9 Plus — coque identique, prix différent |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **Pulsar X2 v3 Mini** sur 1017 des 4830 profils où elle reste éligible · **une variante de sa coque (Pulsar X2A v3) est classée devant elle sur 4830 des 4830 profils où elle est notée** — coque identique, prix différent |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 1792 | 10752 | 5978 | donnée absente : position de la bosse, hauteur des boutons · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1056 des 1792 profils où elle reste éligible |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 798 | 780 | 780 | 780 | 5250 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 639 | 591 | 576 | 576 | 4146 |
| ATK X1 V2 Ultra Max 2.0 | 495 | 831 | 720 | 735 | 3363 |
| ATK A9 Plus | 645 | 762 | 531 | 519 | 3535 |
| ATK Blazing Sky F1 V2 | 571 | 528 | 448 | 232 | 2652 |
| VXE Dragonfly R1 / R1 Pro | 267 | 183 | 183 | 183 | 3323 |
| ATK A9 Mini | 345 | 390 | 360 | 423 | 1427 |
| ATK A9 Ultimate | 225 | 159 | 312 | 378 | 537 |
| Pulsar X2 v3 Mini | 80 | 360 | 360 | 360 | 360 |
| Scyrox V6 | 186 | 213 | 318 | 213 | 477 |
| ATK ZERO | 219 | 203 | 120 | 182 | 428 |
| VXE MAD R / MAD R Major | 267 | 33 | 30 | 33 | 657 |
| ATK Phantom Ultimate | 150 | 150 | 174 | 171 | 150 |
| ATK GHOST Ultimate | 165 | 114 | 117 | 75 | 267 |
| ATK Z1 V2 Ultimate | 147 | 81 | 105 | 75 | 291 |
| Scyrox V8 / V8S | 84 | 76 | 252 | 76 | 159 |
| Pulsar Xlite v4 Mini | 42 | 147 | 147 | 147 | 147 |
| ATK F1 V3 Ultimate+ | 33 | 9 | 53 | 341 | 110 |
| ATK Y9 Ultimate | 138 | 66 | 54 | 54 | 198 |
| Pulsar X2A v3 | 6 | 78 | 78 | 78 | 78 |
| Pulsar X2H v3 Mini | 72 | 36 | 36 | 36 | 36 |
| Pulsar X2 CrazyLight Mini | 42 | 42 | 42 | 42 | 42 |
| Pulsar Xlite v4 Large | 36 | 36 | 36 | 36 | 36 |
| ATK U2 V2 Mini | 81 | 6 | 6 | 3 | 63 |
| ATK U2 V2 Ultimate | 69 | 0 | 45 | 45 | 0 |
| ATK Fierce X | 21 | 18 | 9 | 18 | 39 |
| Pulsar X2H CrazyLight Mini | 24 | 18 | 18 | 18 | 18 |
| ATK GHOST Extreme | 6 | 0 | 0 | 81 | 0 |
| ATK Duckbill | 21 | 12 | 12 | 12 | 27 |
| ATK A9 Air | 24 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 18 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 6 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 2817 | 2925 | 2646 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 3882 | 2646 | 0 |
| ATK X1 V2 Ultra Max 2.0 | 3369 | 2775 | 0 |
| ATK A9 Plus | 3060 | 2442 | 490 |
| ATK Blazing Sky F1 V2 | 0 | 2736 | 1695 |
| VXE Dragonfly R1 / R1 Pro | 1695 | 2046 | 398 |
| ATK A9 Mini | 2259 | 648 | 38 |
| ATK A9 Ultimate | 747 | 447 | 417 |
| Pulsar X2 v3 Mini | 0 | 861 | 659 |
| Scyrox V6 | 561 | 93 | 753 |
| ATK ZERO | 21 | 966 | 165 |
| VXE MAD R / MAD R Major | 381 | 639 | 0 |
| ATK Phantom Ultimate | 795 | 0 | 0 |
| ATK GHOST Ultimate | 507 | 231 | 0 |
| ATK Z1 V2 Ultimate | 699 | 0 | 0 |
| Scyrox V8 / V8S | 0 | 516 | 131 |
| Pulsar Xlite v4 Mini | 630 | 0 | 0 |
| ATK F1 V3 Ultimate+ | 0 | 324 | 222 |
| ATK Y9 Ultimate | 264 | 246 | 0 |
| Pulsar X2A v3 | 0 | 318 | 0 |
| Pulsar X2H v3 Mini | 0 | 216 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 180 | 30 |
| Pulsar Xlite v4 Large | 90 | 90 | 0 |
| ATK U2 V2 Mini | 0 | 159 | 0 |
| ATK U2 V2 Ultimate | 30 | 129 | 0 |
| ATK Fierce X | 0 | 105 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 96 | 0 |
| ATK GHOST Extreme | 12 | 75 | 0 |
| ATK Duckbill | 84 | 0 | 0 |
| ATK A9 Air | 15 | 9 | 0 |
| Pulsar Xlite v4 Medium | 9 | 9 | 0 |
| Pulsar Xlite CrazyLight Medium | 3 | 3 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 1914 | 1914 | 1914 | 2646 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2176 | 2176 | 2176 | 0 |
| ATK X1 V2 Ultra Max 2.0 | 2048 | 2048 | 2048 | 0 |
| ATK A9 Plus | 1834 | 1834 | 1834 | 490 |
| ATK Blazing Sky F1 V2 | 912 | 912 | 912 | 1695 |
| VXE Dragonfly R1 / R1 Pro | 1247 | 1247 | 1247 | 398 |
| ATK A9 Mini | 969 | 969 | 969 | 38 |
| ATK A9 Ultimate | 398 | 398 | 398 | 417 |
| Pulsar X2 v3 Mini | 287 | 287 | 287 | 659 |
| Scyrox V6 | 218 | 218 | 218 | 753 |
| ATK ZERO | 329 | 329 | 329 | 165 |
| VXE MAD R / MAD R Major | 340 | 340 | 340 | 0 |
| ATK Phantom Ultimate | 265 | 265 | 265 | 0 |
| ATK GHOST Ultimate | 246 | 246 | 246 | 0 |
| ATK Z1 V2 Ultimate | 233 | 233 | 233 | 0 |
| Scyrox V8 / V8S | 172 | 172 | 172 | 131 |
| Pulsar Xlite v4 Mini | 210 | 210 | 210 | 0 |
| ATK F1 V3 Ultimate+ | 108 | 108 | 108 | 222 |
| ATK Y9 Ultimate | 170 | 170 | 170 | 0 |
| Pulsar X2A v3 | 106 | 106 | 106 | 0 |
| Pulsar X2H v3 Mini | 72 | 72 | 72 | 0 |
| Pulsar X2 CrazyLight Mini | 60 | 60 | 60 | 30 |
| Pulsar Xlite v4 Large | 60 | 60 | 60 | 0 |
| ATK U2 V2 Mini | 53 | 53 | 53 | 0 |
| ATK U2 V2 Ultimate | 53 | 53 | 53 | 0 |
| ATK Fierce X | 35 | 35 | 35 | 0 |
| Pulsar X2H CrazyLight Mini | 32 | 32 | 32 | 0 |
| ATK GHOST Extreme | 29 | 29 | 29 | 0 |
| ATK Duckbill | 28 | 28 | 28 | 0 |
| ATK A9 Air | 8 | 8 | 8 | 0 |
| Pulsar Xlite v4 Medium | 6 | 6 | 6 | 0 |
| Pulsar Xlite CrazyLight Medium | 2 | 2 | 2 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 27.0/40 | 40/40 | 10/40 | 12474 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 22.6/40 | 35/40 | 15/40 | 12096 |
| ATK X1 V2 Ultra Max 2.0 | 23.4/40 | 35/40 | 15/40 | 10752 |
| ATK A9 Plus | 24.3/40 | 35/40 | 15/40 | 12768 |
| ATK Blazing Sky F1 V2 | 32.5/40 | 40/40 | 20/40 | 7056 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 35/40 | 10/40 | 14742 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| ATK A9 Ultimate | 25.1/40 | 40/40 | 15/40 | 11172 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| ATK ZERO | 26.1/40 | 40/40 | 10/40 | 9828 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| ATK Phantom Ultimate | 25.9/40 | 35/40 | 10/40 | 7770 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Z1 V2 Ultimate | 19.8/40 | 35/40 | 10/40 | 6720 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| Pulsar Xlite v4 Mini | 22.1/40 | 35/40 | 10/40 | 6510 |
| ATK F1 V3 Ultimate+ | 32.5/40 | 40/40 | 20/40 | 6174 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 5376 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| Pulsar X2H v3 Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Pulsar Xlite v4 Large | 18.8/40 | 25/40 | 15/40 | 1440 |
| ATK U2 V2 Mini | 22.9/40 | 35/40 | 5/40 | 6468 |
| ATK U2 V2 Ultimate | 20.1/40 | 35/40 | 10/40 | 9408 |
| ATK Fierce X | 27.2/40 | 35/40 | 15/40 | 5544 |
| Pulsar X2H CrazyLight Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Duckbill | 18.5/40 | 30/40 | 10/40 | 6678 |
| ATK A9 Air | 25.1/40 | 40/40 | 15/40 | 11172 |
| Pulsar Xlite v4 Medium | 20.4/40 | 30/40 | 15/40 | 5760 |
| Pulsar Xlite CrazyLight Medium | 20.4/40 | 30/40 | 15/40 | 5760 |
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

