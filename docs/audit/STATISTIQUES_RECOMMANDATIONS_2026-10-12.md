# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 1212** sur 18522 (6.5 %).
  - budget inférieur à la souris qui convient la moins chère : 1212
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **960**
- **Profils où DEUX places montrent la même coque : 2830** (15.3 %).
  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de disparaître. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 1200 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 1051 profils
  - `atk_a9_nb` + `atk_a9_plus` : 306 profils
  - `pulsar_x2_crazylight_medium` + `pulsar_x2a_v3_medium` : 252 profils
  - `atk_ghost_extreme` + `atk_ghost_ultimate` : 21 profils
  Élargir la recherche à une autre coque (au-delà de la zone du mode) est une décision du propriétaire : elle changerait la deuxième place de ces profils.

## Nombre de fois où chaque souris est recommandée

| Souris | Idéal | Alternative | Économie | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| ATK A9 Ultimate | 3111 | 1245 | 0 | 4356 | 23.5 % |
| ATK X1 V2 Ultra Max | 2148 | 1737 | 0 | 3885 | 21.0 % |
| ATK A9 Mini | 2994 | 540 | 0 | 3534 | 19.1 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2805 | 120 | 0 | 2925 | 15.8 % |
| ATK A9 Plus 2.0 | 1113 | 1422 | 60 | 2595 | 14.0 % |
| ATK F1 V3 Ultimate | 1647 | 555 | 0 | 2202 | 11.9 % |
| Pulsar X2 v3 Mini | 1075 | 715 | 0 | 1790 | 9.7 % |
| Scyrox V6 | 811 | 541 | 0 | 1352 | 7.3 % |
| Scyrox V8 / V8S | 229 | 925 | 0 | 1154 | 6.2 % |
| Pulsar X2 CrazyLight Mini | 0 | 1051 | 0 | 1051 | 5.7 % |
| Pulsar Xlite v4 Mini | 321 | 615 | 0 | 936 | 5.1 % |
| ATK GHOST Ultimate | 330 | 471 | 0 | 801 | 4.3 % |
| Pulsar X2A v3 | 270 | 228 | 0 | 498 | 2.7 % |
| ATK Dragonfly A9 NB Ultra | 156 | 150 | 0 | 306 | 1.7 % |
| Pulsar X2 CrazyLight Medium | 0 | 252 | 0 | 252 | 1.4 % |
| ATK Z1 V2 Ultra | 99 | 144 | 0 | 243 | 1.3 % |
| ATK GHOST Extreme | 81 | 90 | 0 | 171 | 0.9 % |
| ATK Y9 Ultimate | 120 | 0 | 0 | 120 | 0.6 % |
| Pulsar X2H v3 Mini | 0 | 24 | 0 | 24 | 0.1 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Fierce X | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Phantom Ultimate | 0 | 0 | 0 | 0 | 0.0 % |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 | 0.0 % |
| ATK ZERO | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |
| VXE MAD R / MAD R Major | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**17 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK Blazing Sky F1 V2** (`atk_f1_v2`)
- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **ATK Duckbill** (`atk_duckbill`)
- **ATK Fierce X** (`atk_fierce_x`)
- **ATK Phantom Ultimate** (`atk_phantom_ultimate`)
- **ATK U2 V2 Mini** (`atk_u2_v2_mini`)
- **ATK U2 V2 Ultimate** (`atk_u2_v2_ultimate`)
- **ATK ZERO** (`atk_zero`)
- **Pulsar X2H CrazyLight Mini** (`pulsar_x2h_crazylight_mini`)
- **Pulsar Xlite CrazyLight Medium** (`pulsar_xlite_crazylight_medium`)
- **Pulsar Xlite v4 Large** (`pulsar_xlite_v4_large`)
- **Pulsar Xlite v4 Medium** (`pulsar_xlite_v4_medium`)
- **VXE Dragonfly R1 / R1 Pro** (`vxe_r1`)
- **VXE Dragonfly V3 / V3 Pro** (`vxe_v3`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)
- **VXE MAD R / MAD R Major** (`vxe_mad_r`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 9576 | 0 | 8946 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky F1 V2 | 0 | 11760 | 6762 | donnée absente : compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky U2 Mini | 3780 | 5544 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Duckbill | 0 | 12348 | 6174 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Fierce X | 0 | 9324 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Phantom Ultimate | 0 | 7770 | 10752 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK U2 V2 Mini | 0 | 10878 | 7644 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK U2 V2 Ultimate | 0 | 11004 | 7518 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK ZERO | 0 | 9828 | 8694 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar X2H CrazyLight Mini | 2520 | 3990 | 12012 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite CrazyLight Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Large | 720 | 720 | 17082 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly R1 / R1 Pro | 0 | 14742 | 3780 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly V3 / V3 Pro | 0 | 12474 | 6048 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 12544 | 5978 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE MAD R / MAD R Major | 0 | 14742 | 3780 | aucun prix EUR (les modes à prix l'écartent d'office) · donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| ATK A9 Ultimate | 633 | 378 | 363 | 363 | 2619 |
| ATK X1 V2 Ultra Max | 570 | 663 | 660 | 660 | 1332 |
| ATK A9 Mini | 552 | 363 | 315 | 366 | 1938 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 441 | 60 | 60 | 60 | 2304 |
| ATK A9 Plus 2.0 | 99 | 129 | 129 | 129 | 2109 |
| ATK F1 V3 Ultimate | 515 | 293 | 278 | 305 | 811 |
| Pulsar X2 v3 Mini | 254 | 384 | 384 | 384 | 384 |
| Scyrox V6 | 222 | 204 | 273 | 204 | 449 |
| Scyrox V8 / V8S | 73 | 187 | 229 | 187 | 478 |
| Pulsar X2 CrazyLight Mini | 43 | 252 | 252 | 252 | 252 |
| Pulsar Xlite v4 Mini | 204 | 183 | 183 | 183 | 183 |
| ATK GHOST Ultimate | 195 | 150 | 93 | 0 | 363 |
| Pulsar X2A v3 | 66 | 108 | 108 | 108 | 108 |
| ATK Dragonfly A9 NB Ultra | 0 | 48 | 78 | 78 | 102 |
| Pulsar X2 CrazyLight Medium | 0 | 63 | 63 | 63 | 63 |
| ATK Z1 V2 Ultra | 21 | 36 | 63 | 39 | 84 |
| ATK GHOST Extreme | 0 | 0 | 0 | 150 | 21 |
| ATK Y9 Ultimate | 36 | 0 | 0 | 0 | 84 |
| Pulsar X2H v3 Mini | 24 | 0 | 0 | 0 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 | 0 | 0 |
| ATK Phantom Ultimate | 0 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |
| VXE MAD R / MAD R Major | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| ATK A9 Ultimate | 2475 | 1881 | 0 |
| ATK X1 V2 Ultra Max | 2256 | 1629 | 0 |
| ATK A9 Mini | 2490 | 786 | 258 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 930 | 1995 | 0 |
| ATK A9 Plus 2.0 | 1377 | 765 | 453 |
| ATK F1 V3 Ultimate | 0 | 1299 | 903 |
| Pulsar X2 v3 Mini | 0 | 1017 | 773 |
| Scyrox V6 | 207 | 231 | 914 |
| Scyrox V8 / V8S | 0 | 648 | 506 |
| Pulsar X2 CrazyLight Mini | 0 | 792 | 259 |
| Pulsar Xlite v4 Mini | 936 | 0 | 0 |
| ATK GHOST Ultimate | 189 | 612 | 0 |
| Pulsar X2A v3 | 0 | 498 | 0 |
| ATK Dragonfly A9 NB Ultra | 180 | 126 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 252 | 0 |
| ATK Z1 V2 Ultra | 243 | 0 | 0 |
| ATK GHOST Extreme | 33 | 138 | 0 |
| ATK Y9 Ultimate | 120 | 0 | 0 |
| Pulsar X2H v3 Mini | 0 | 24 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 |
| ATK Phantom Ultimate | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |
| VXE MAD R / MAD R Major | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| ATK A9 Ultimate | 1452 | 1452 | 1452 | 0 |
| ATK X1 V2 Ultra Max | 1295 | 1295 | 1295 | 0 |
| ATK A9 Mini | 1092 | 1092 | 1092 | 258 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 975 | 975 | 975 | 0 |
| ATK A9 Plus 2.0 | 714 | 714 | 714 | 453 |
| ATK F1 V3 Ultimate | 433 | 433 | 433 | 903 |
| Pulsar X2 v3 Mini | 339 | 339 | 339 | 773 |
| Scyrox V6 | 146 | 146 | 146 | 914 |
| Scyrox V8 / V8S | 216 | 216 | 216 | 506 |
| Pulsar X2 CrazyLight Mini | 264 | 264 | 264 | 259 |
| Pulsar Xlite v4 Mini | 312 | 312 | 312 | 0 |
| ATK GHOST Ultimate | 267 | 267 | 267 | 0 |
| Pulsar X2A v3 | 166 | 166 | 166 | 0 |
| ATK Dragonfly A9 NB Ultra | 102 | 102 | 102 | 0 |
| Pulsar X2 CrazyLight Medium | 84 | 84 | 84 | 0 |
| ATK Z1 V2 Ultra | 81 | 81 | 81 | 0 |
| ATK GHOST Extreme | 57 | 57 | 57 | 0 |
| ATK Y9 Ultimate | 40 | 40 | 40 | 0 |
| Pulsar X2H v3 Mini | 8 | 8 | 8 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 | 0 |
| ATK Phantom Ultimate | 0 | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |
| VXE MAD R / MAD R Major | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| ATK A9 Ultimate | 22.8/40 | 35/40 | 10/40 | 12768 |
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 8064 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 20.1/40 | 35/40 | 10/40 | 12096 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 5292 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Pulsar Xlite v4 Mini | 25.7/40 | 35/40 | 15/40 | 2520 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK Dragonfly A9 NB Ultra | 23.5/40 | 35/40 | 10/40 | 9576 |
| Pulsar X2 CrazyLight Medium | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 5760 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 3072 |
| Pulsar X2H v3 Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| ATK A9 Air | 22.8/40 | 35/40 | 10/40 | 9576 |
| ATK Blazing Sky F1 V2 | — | — | — | 0 |
| ATK Blazing Sky U2 Mini | 25.4/40 | 35/40 | 15/40 | 3780 |
| ATK Duckbill | — | — | — | 0 |
| ATK Fierce X | — | — | — | 0 |
| ATK Phantom Ultimate | — | — | — | 0 |
| ATK U2 V2 Mini | — | — | — | 0 |
| ATK U2 V2 Ultimate | — | — | — | 0 |
| ATK ZERO | — | — | — | 0 |
| Pulsar X2H CrazyLight Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| Pulsar Xlite CrazyLight Medium | 20.4/40 | 30/40 | 15/40 | 2880 |
| Pulsar Xlite v4 Large | 18.8/40 | 25/40 | 15/40 | 720 |
| Pulsar Xlite v4 Medium | 20.4/40 | 30/40 | 15/40 | 2880 |
| VXE Dragonfly R1 / R1 Pro | — | — | — | 0 |
| VXE Dragonfly V3 / V3 Pro | — | — | — | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | — | — | — | 0 |
| VXE MAD R / MAD R Major | — | — | — | 0 |

## Ce qui manque, souris par souris (à trouver, jamais à inventer)

- **Sans aucune compatibilité de prise publiée (11 souris)** : jamais classables, donc jamais proposées, quel que soit le profil. Seule une publication du fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.
  - ATK Blazing Sky F1 V2 (`atk_f1_v2`) — 41,95 €
  - ATK Duckbill (`atk_duckbill`) — 81,95 €
  - ATK Fierce X (`atk_fierce_x`) — 69,95 €
  - ATK Phantom Ultimate (`atk_phantom_ultimate`) — 91,95 €
  - ATK U2 V2 Mini (`atk_u2_v2_mini`) — 59,95 €
  - ATK U2 V2 Ultimate (`atk_u2_v2_ultimate`) — 59,95 €
  - ATK ZERO (`atk_zero`) — 63,95 €
  - VXE Dragonfly R1 / R1 Pro (`vxe_r1`) — 13,95 €
  - VXE Dragonfly V3 / V3 Pro (`vxe_v3`) — 13,95 €
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`) — 27,95 €
  - VXE MAD R / MAD R Major (`vxe_mad_r`) — prix inconnu
- **Sans position de bosse publiée (1 souris)** : « à vérifier » dès que la prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`)
- **Sans hauteur de boutons documentée (25 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée (règle du propriétaire : jamais d'invention).

