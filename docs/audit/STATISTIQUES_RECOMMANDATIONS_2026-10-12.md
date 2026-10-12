# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 1044** sur 18522 (5.6 %).
  - budget inférieur à la souris qui convient la moins chère : 1044
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **792**
- **Profils où DEUX places montrent la même coque : 1304** (7.0 %).
  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de disparaître. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 867 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 215 profils
  - `atk_a9_nb` + `atk_a9_plus` : 180 profils
  - `atk_a9_nb` + `atk_a9_ultimate` : 42 profils
  Élargir la recherche à une autre coque (au-delà de la zone du mode) est une décision du propriétaire : elle changerait la deuxième place de ces profils.

## Nombre de fois où chaque souris est recommandée

| Souris | Idéal | Alternative | Économie | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2529 | 1536 | 1620 | 5685 | 30.7 % |
| ATK A9 Ultimate | 2829 | 1821 | 861 | 5511 | 29.8 % |
| ATK A9 Mini | 2775 | 1140 | 351 | 4266 | 23.0 % |
| ATK X1 V2 Ultra Max | 2148 | 1734 | 0 | 3882 | 21.0 % |
| ATK F1 V3 Ultimate | 1632 | 1245 | 448 | 3325 | 18.0 % |
| VXE MAD R / MAD R Major | 1098 | 843 | 669 | 2610 | 14.1 % |
| Pulsar X2 v3 Mini | 1075 | 715 | 0 | 1790 | 9.7 % |
| ATK A9 Plus 2.0 | 1014 | 582 | 192 | 1788 | 9.7 % |
| Scyrox V6 | 811 | 625 | 0 | 1436 | 7.8 % |
| Scyrox V8 / V8S | 229 | 910 | 0 | 1139 | 6.1 % |
| Pulsar Xlite v4 Mini | 321 | 615 | 0 | 936 | 5.1 % |
| ATK GHOST Ultimate | 303 | 483 | 6 | 792 | 4.3 % |
| Pulsar X2A v3 | 270 | 225 | 0 | 495 | 2.7 % |
| ATK Y9 Ultimate | 108 | 219 | 15 | 342 | 1.8 % |
| ATK Dragonfly A9 NB Ultra | 156 | 126 | 0 | 282 | 1.5 % |
| ATK Z1 V2 Ultra | 99 | 144 | 0 | 243 | 1.3 % |
| Pulsar X2 CrazyLight Mini | 0 | 215 | 0 | 215 | 1.2 % |
| ATK GHOST Extreme | 81 | 66 | 0 | 147 | 0.8 % |
| Pulsar X2H v3 Mini | 0 | 120 | 0 | 120 | 0.6 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Fierce X | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Phantom Ultimate | 0 | 0 | 0 | 0 | 0.0 % |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 | 0.0 % |
| ATK ZERO | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

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
- **Pulsar X2 CrazyLight Medium** (`pulsar_x2_crazylight_medium`)
- **Pulsar X2H CrazyLight Mini** (`pulsar_x2h_crazylight_mini`)
- **Pulsar Xlite CrazyLight Medium** (`pulsar_xlite_crazylight_medium`)
- **Pulsar Xlite v4 Large** (`pulsar_xlite_v4_large`)
- **Pulsar Xlite v4 Medium** (`pulsar_xlite_v4_medium`)
- **VXE Dragonfly R1 / R1 Pro** (`vxe_r1`)
- **VXE Dragonfly V3 / V3 Pro** (`vxe_v3`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 11172 | 0 | 7350 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky F1 V2 | 0 | 11760 | 6762 | donnée absente : compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky U2 Mini | 3780 | 5544 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Duckbill | 0 | 12348 | 6174 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Fierce X | 0 | 9324 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Phantom Ultimate | 0 | 7770 | 10752 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK U2 V2 Mini | 0 | 10878 | 7644 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK U2 V2 Ultimate | 0 | 11004 | 7518 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK ZERO | 0 | 9828 | 8694 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : compatibilité de prise (statut non vérifié) |
| Pulsar X2H CrazyLight Mini | 2520 | 3990 | 12012 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite CrazyLight Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Large | 720 | 720 | 17082 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly R1 / R1 Pro | 0 | 14742 | 3780 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly V3 / V3 Pro | 0 | 12474 | 6048 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 12544 | 5978 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 441 | 441 | 441 | 441 | 3921 |
| ATK A9 Ultimate | 594 | 600 | 579 | 579 | 3159 |
| ATK A9 Mini | 504 | 522 | 489 | 546 | 2205 |
| ATK X1 V2 Ultra Max | 570 | 663 | 660 | 660 | 1329 |
| ATK F1 V3 Ultimate | 515 | 542 | 530 | 557 | 1181 |
| VXE MAD R / MAD R Major | 183 | 183 | 180 | 180 | 1884 |
| Pulsar X2 v3 Mini | 254 | 384 | 384 | 384 | 384 |
| ATK A9 Plus 2.0 | 87 | 159 | 105 | 105 | 1332 |
| Scyrox V6 | 222 | 225 | 294 | 225 | 470 |
| Scyrox V8 / V8S | 58 | 187 | 229 | 187 | 478 |
| Pulsar Xlite v4 Mini | 204 | 183 | 183 | 183 | 183 |
| ATK GHOST Ultimate | 135 | 162 | 111 | 18 | 366 |
| Pulsar X2A v3 | 63 | 108 | 108 | 108 | 108 |
| ATK Y9 Ultimate | 30 | 30 | 30 | 30 | 222 |
| ATK Dragonfly A9 NB Ultra | 0 | 42 | 78 | 78 | 84 |
| ATK Z1 V2 Ultra | 21 | 36 | 66 | 39 | 81 |
| Pulsar X2 CrazyLight Mini | 43 | 43 | 43 | 43 | 43 |
| ATK GHOST Extreme | 0 | 0 | 0 | 147 | 0 |
| Pulsar X2H v3 Mini | 24 | 24 | 24 | 24 | 24 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 | 0 | 0 |
| ATK Phantom Ultimate | 0 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 2163 | 3522 | 0 |
| ATK A9 Ultimate | 3309 | 1848 | 354 |
| ATK A9 Mini | 2733 | 1263 | 270 |
| ATK X1 V2 Ultra Max | 2256 | 1626 | 0 |
| ATK F1 V3 Ultimate | 0 | 1701 | 1624 |
| VXE MAD R / MAD R Major | 1032 | 1578 | 0 |
| Pulsar X2 v3 Mini | 0 | 1017 | 773 |
| ATK A9 Plus 2.0 | 633 | 471 | 684 |
| Scyrox V6 | 207 | 231 | 998 |
| Scyrox V8 / V8S | 0 | 633 | 506 |
| Pulsar Xlite v4 Mini | 936 | 0 | 0 |
| ATK GHOST Ultimate | 162 | 630 | 0 |
| Pulsar X2A v3 | 0 | 495 | 0 |
| ATK Y9 Ultimate | 342 | 0 | 0 |
| ATK Dragonfly A9 NB Ultra | 180 | 102 | 0 |
| ATK Z1 V2 Ultra | 243 | 0 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 180 | 35 |
| ATK GHOST Extreme | 30 | 117 | 0 |
| Pulsar X2H v3 Mini | 0 | 120 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 |
| ATK Phantom Ultimate | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 |

## Par taille de thénar (nombre de sorties)

Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.

| Souris | Petite | Moyenne | Grande | — (Fingertip) |
|---|---|---|---|---|
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1895 | 1895 | 1895 | 0 |
| ATK A9 Ultimate | 1719 | 1719 | 1719 | 354 |
| ATK A9 Mini | 1332 | 1332 | 1332 | 270 |
| ATK X1 V2 Ultra Max | 1294 | 1294 | 1294 | 0 |
| ATK F1 V3 Ultimate | 567 | 567 | 567 | 1624 |
| VXE MAD R / MAD R Major | 870 | 870 | 870 | 0 |
| Pulsar X2 v3 Mini | 339 | 339 | 339 | 773 |
| ATK A9 Plus 2.0 | 368 | 368 | 368 | 684 |
| Scyrox V6 | 146 | 146 | 146 | 998 |
| Scyrox V8 / V8S | 211 | 211 | 211 | 506 |
| Pulsar Xlite v4 Mini | 312 | 312 | 312 | 0 |
| ATK GHOST Ultimate | 264 | 264 | 264 | 0 |
| Pulsar X2A v3 | 165 | 165 | 165 | 0 |
| ATK Y9 Ultimate | 114 | 114 | 114 | 0 |
| ATK Dragonfly A9 NB Ultra | 94 | 94 | 94 | 0 |
| ATK Z1 V2 Ultra | 81 | 81 | 81 | 0 |
| Pulsar X2 CrazyLight Mini | 60 | 60 | 60 | 35 |
| ATK GHOST Extreme | 49 | 49 | 49 | 0 |
| Pulsar X2H v3 Mini | 40 | 40 | 40 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 |
| ATK Fierce X | 0 | 0 | 0 | 0 |
| ATK Phantom Ultimate | 0 | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly R1 / R1 Pro | 0 | 0 | 0 | 0 |
| VXE Dragonfly V3 / V3 Pro | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 20.1/40 | 35/40 | 10/40 | 12096 |
| ATK A9 Ultimate | 22.8/40 | 35/40 | 10/40 | 12768 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 8064 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 5292 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| Pulsar Xlite v4 Mini | 25.7/40 | 35/40 | 15/40 | 2520 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 3072 |
| ATK Dragonfly A9 NB Ultra | 23.5/40 | 35/40 | 10/40 | 9576 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 5760 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| Pulsar X2H v3 Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| ATK A9 Air | 22.8/40 | 35/40 | 10/40 | 11172 |
| ATK Blazing Sky F1 V2 | — | — | — | 0 |
| ATK Blazing Sky U2 Mini | 25.4/40 | 35/40 | 15/40 | 3780 |
| ATK Duckbill | — | — | — | 0 |
| ATK Fierce X | — | — | — | 0 |
| ATK Phantom Ultimate | — | — | — | 0 |
| ATK U2 V2 Mini | — | — | — | 0 |
| ATK U2 V2 Ultimate | — | — | — | 0 |
| ATK ZERO | — | — | — | 0 |
| Pulsar X2 CrazyLight Medium | 30.7/40 | 40/40 | 20/40 | 4830 |
| Pulsar X2H CrazyLight Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| Pulsar Xlite CrazyLight Medium | 20.4/40 | 30/40 | 15/40 | 2880 |
| Pulsar Xlite v4 Large | 18.8/40 | 25/40 | 15/40 | 720 |
| Pulsar Xlite v4 Medium | 20.4/40 | 30/40 | 15/40 | 2880 |
| VXE Dragonfly R1 / R1 Pro | — | — | — | 0 |
| VXE Dragonfly V3 / V3 Pro | — | — | — | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | — | — | — | 0 |

## Ce qui manque, souris par souris (à trouver, jamais à inventer)

- **Sans aucune compatibilité de prise publiée (10 souris)** : jamais classables, donc jamais proposées, quel que soit le profil. Seule une publication du fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.
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
- **Sans position de bosse publiée (1 souris)** : « à vérifier » dès que la prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`)
- **Sans hauteur de boutons documentée (25 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée (règle du propriétaire : jamais d'invention).

