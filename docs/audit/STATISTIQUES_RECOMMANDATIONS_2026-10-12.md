# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 1422** sur 18522 (7.7 %).
  - aucune souris classable avec ces critères : 1422
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **1170**
- **Profils où DEUX places montrent la même coque : 3109** (16.8 %).
  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de disparaître. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 1461 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 1051 profils
  - `atk_a9_nb` + `atk_a9_plus` : 309 profils
  - `pulsar_x2_crazylight_medium` + `pulsar_x2a_v3_medium` : 252 profils
  - `atk_ghost_extreme` + `atk_ghost_ultimate` : 36 profils
  Élargir la recherche à une autre coque (au-delà de la zone du mode) est une décision du propriétaire : elle changerait la deuxième place de ces profils.

## Nombre de fois où chaque souris est recommandée

| Souris | Idéal | Alternative | Économie | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| ATK A9 Ultimate | 3501 | 1482 | 0 | 4983 | 26.9 % |
| ATK X1 V2 Ultra Max | 2163 | 1758 | 0 | 3921 | 21.2 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 3156 | 126 | 0 | 3282 | 17.7 % |
| ATK A9 Plus 2.0 | 1296 | 1707 | 63 | 3066 | 16.6 % |
| Scyrox V6 | 1441 | 1525 | 0 | 2966 | 16.0 % |
| ATK F1 V3 Ultimate | 1800 | 591 | 0 | 2391 | 12.9 % |
| ATK GHOST Ultimate | 1335 | 759 | 0 | 2094 | 11.3 % |
| Pulsar X2 v3 Mini | 1075 | 727 | 0 | 1802 | 9.7 % |
| Scyrox V8 / V8S | 229 | 1009 | 0 | 1238 | 6.7 % |
| Pulsar X2 CrazyLight Mini | 0 | 1051 | 0 | 1051 | 5.7 % |
| Pulsar X2A v3 | 270 | 231 | 0 | 501 | 2.7 % |
| ATK GHOST Extreme | 360 | 75 | 0 | 435 | 2.3 % |
| ATK Z1 V2 Ultra | 195 | 186 | 0 | 381 | 2.1 % |
| ATK Dragonfly A9 NB Ultra | 159 | 150 | 0 | 309 | 1.7 % |
| Pulsar X2 CrazyLight Medium | 0 | 252 | 0 | 252 | 1.4 % |
| ATK Y9 Ultimate | 120 | 0 | 0 | 120 | 0.6 % |
| Pulsar X2H v3 Mini | 0 | 24 | 0 | 24 | 0.1 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK A9 Mini | 0 | 0 | 0 | 0 | 0.0 % |
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
| Pulsar Xlite v4 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |
| VXE MAD R / MAD R Major | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**19 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK A9 Mini** (`atk_a9_mini`)
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
- **Pulsar Xlite v4 Mini** (`pulsar_xlite_v4_mini`)
- **VXE Dragonfly R1 / R1 Pro** (`vxe_r1`)
- **VXE Dragonfly V3 / V3 Pro** (`vxe_v3`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)
- **VXE MAD R / MAD R Major** (`vxe_mad_r`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 9576 | 0 | 8946 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK A9 Mini | 2646 | 12642 | 5292 | aucun prix EUR (les modes à prix l'écartent d'office) · donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky F1 V2 | 0 | 11760 | 6762 | donnée absente : compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky U2 Mini | 3780 | 5544 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Duckbill | 0 | 12348 | 6174 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Fierce X | 0 | 9324 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Phantom Ultimate | 0 | 7770 | 10752 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK U2 V2 Mini | 0 | 9324 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK U2 V2 Ultimate | 0 | 11004 | 7518 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK ZERO | 0 | 9828 | 8694 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar X2H CrazyLight Mini | 2520 | 3990 | 12012 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite CrazyLight Medium | 0 | 6660 | 11862 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Large | 0 | 1440 | 17082 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Medium | 0 | 6660 | 11862 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Mini | 0 | 6510 | 12012 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly R1 / R1 Pro | 0 | 14742 | 3780 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly V3 / V3 Pro | 0 | 12474 | 6048 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 12544 | 5978 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE MAD R / MAD R Major | 0 | 14742 | 3780 | aucun prix EUR (les modes à prix l'écartent d'office) · donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| ATK A9 Ultimate | 735 | 411 | 396 | 396 | 3045 |
| ATK X1 V2 Ultra Max | 582 | 669 | 663 | 663 | 1344 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 498 | 63 | 63 | 63 | 2595 |
| ATK A9 Plus 2.0 | 111 | 138 | 138 | 138 | 2541 |
| Scyrox V6 | 393 | 492 | 564 | 492 | 1025 |
| ATK F1 V3 Ultimate | 566 | 320 | 278 | 338 | 889 |
| ATK GHOST Ultimate | 483 | 405 | 330 | 3 | 873 |
| Pulsar X2 v3 Mini | 266 | 384 | 384 | 384 | 384 |
| Scyrox V8 / V8S | 109 | 187 | 229 | 187 | 526 |
| Pulsar X2 CrazyLight Mini | 43 | 252 | 252 | 252 | 252 |
| Pulsar X2A v3 | 69 | 108 | 108 | 108 | 108 |
| ATK GHOST Extreme | 0 | 3 | 3 | 402 | 27 |
| ATK Z1 V2 Ultra | 36 | 63 | 87 | 69 | 126 |
| ATK Dragonfly A9 NB Ultra | 0 | 48 | 78 | 81 | 102 |
| Pulsar X2 CrazyLight Medium | 0 | 63 | 63 | 63 | 63 |
| ATK Y9 Ultimate | 36 | 0 | 0 | 0 | 84 |
| Pulsar X2H v3 Mini | 24 | 0 | 0 | 0 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK A9 Mini | 0 | 0 | 0 | 0 | 0 |
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
| Pulsar Xlite v4 Mini | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |
| VXE MAD R / MAD R Major | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| ATK A9 Ultimate | 2943 | 2040 | 0 |
| ATK X1 V2 Ultra Max | 2292 | 1629 | 0 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1089 | 2193 | 0 |
| ATK A9 Plus 2.0 | 1677 | 849 | 540 |
| Scyrox V6 | 1812 | 240 | 914 |
| ATK F1 V3 Ultimate | 0 | 1488 | 903 |
| ATK GHOST Ultimate | 1377 | 717 | 0 |
| Pulsar X2 v3 Mini | 0 | 1029 | 773 |
| Scyrox V8 / V8S | 0 | 732 | 506 |
| Pulsar X2 CrazyLight Mini | 0 | 792 | 259 |
| Pulsar X2A v3 | 0 | 501 | 0 |
| ATK GHOST Extreme | 297 | 138 | 0 |
| ATK Z1 V2 Ultra | 381 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 183 | 126 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 252 | 0 |
| ATK Y9 Ultimate | 120 | 0 | 0 |
| Pulsar X2H v3 Mini | 0 | 24 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK A9 Mini | 0 | 0 | 0 |
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
| Pulsar Xlite v4 Mini | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |
| VXE MAD R / MAD R Major | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| ATK A9 Ultimate | 1661 | 1661 | 1661 | 0 |
| ATK X1 V2 Ultra Max | 1307 | 1307 | 1307 | 0 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1094 | 1094 | 1094 | 0 |
| ATK A9 Plus 2.0 | 842 | 842 | 842 | 540 |
| Scyrox V6 | 684 | 684 | 684 | 914 |
| ATK F1 V3 Ultimate | 496 | 496 | 496 | 903 |
| ATK GHOST Ultimate | 698 | 698 | 698 | 0 |
| Pulsar X2 v3 Mini | 343 | 343 | 343 | 773 |
| Scyrox V8 / V8S | 244 | 244 | 244 | 506 |
| Pulsar X2 CrazyLight Mini | 264 | 264 | 264 | 259 |
| Pulsar X2A v3 | 167 | 167 | 167 | 0 |
| ATK GHOST Extreme | 145 | 145 | 145 | 0 |
| ATK Z1 V2 Ultra | 127 | 127 | 127 | 0 |
| ATK Dragonfly A9 NB Ultra | 103 | 103 | 103 | 0 |
| Pulsar X2 CrazyLight Medium | 84 | 84 | 84 | 0 |
| ATK Y9 Ultimate | 40 | 40 | 40 | 0 |
| Pulsar X2H v3 Mini | 8 | 8 | 8 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK A9 Mini | 0 | 0 | 0 | 0 |
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
| Pulsar Xlite v4 Mini | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |
| VXE MAD R / MAD R Major | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| ATK A9 Ultimate | 22.8/40 | 35/40 | 10/40 | 12768 |
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 8064 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 20.1/40 | 35/40 | 10/40 | 12096 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 5292 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 5760 |
| ATK Dragonfly A9 NB Ultra | 23.5/40 | 35/40 | 10/40 | 9576 |
| Pulsar X2 CrazyLight Medium | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 3072 |
| Pulsar X2H v3 Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| ATK A9 Air | 22.8/40 | 35/40 | 10/40 | 9576 |
| ATK A9 Mini | 26.1/40 | 30/40 | 10/40 | 588 |
| ATK Blazing Sky F1 V2 | — | — | — | 0 |
| ATK Blazing Sky U2 Mini | 25.4/40 | 35/40 | 15/40 | 3780 |
| ATK Duckbill | — | — | — | 0 |
| ATK Fierce X | — | — | — | 0 |
| ATK Phantom Ultimate | — | — | — | 0 |
| ATK U2 V2 Mini | — | — | — | 0 |
| ATK U2 V2 Ultimate | — | — | — | 0 |
| ATK ZERO | — | — | — | 0 |
| Pulsar X2H CrazyLight Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| Pulsar Xlite CrazyLight Medium | — | — | — | 0 |
| Pulsar Xlite v4 Large | — | — | — | 0 |
| Pulsar Xlite v4 Medium | — | — | — | 0 |
| Pulsar Xlite v4 Mini | — | — | — | 0 |
| VXE Dragonfly R1 / R1 Pro | — | — | — | 0 |
| VXE Dragonfly V3 / V3 Pro | — | — | — | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | — | — | — | 0 |
| VXE MAD R / MAD R Major | — | — | — | 0 |
