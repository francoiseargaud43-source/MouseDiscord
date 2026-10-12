# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 540** sur 18522 (2.9 %).
  - budget inférieur à la souris qui convient la moins chère : 540
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **288**
- **Profils où DEUX places montrent la même coque : 983** (5.3 %).
  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de disparaître. Les paires concernées, par fréquence :
  - `atk_a9_plus` + `atk_a9_ultimate` : 552 profils
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 215 profils
  - `atk_a9_nb` + `atk_a9_plus` : 174 profils
  - `atk_a9_nb` + `atk_a9_ultimate` : 42 profils
  Élargir la recherche à une autre coque (au-delà de la zone du mode) est une décision du propriétaire : elle changerait la deuxième place de ces profils.

## Nombre de fois où chaque souris est recommandée

| Souris | Idéal | Alternative | Économie | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 3130 | 1471 | 1480 | 6081 | 32.8 % |
| ATK A9 Ultimate | 2769 | 1653 | 489 | 4911 | 26.5 % |
| ATK X1 V2 Ultra Max | 2136 | 1716 | 0 | 3852 | 20.8 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1233 | 1353 | 846 | 3432 | 18.5 % |
| VXE Dragonfly R1 / R1 Pro | 708 | 1682 | 885 | 3275 | 17.7 % |
| ATK A9 Mini | 1844 | 1197 | 49 | 3090 | 16.7 % |
| ATK F1 V3 Ultimate | 1467 | 1051 | 448 | 2966 | 16.0 % |
| Pulsar X2 v3 Mini | 1069 | 709 | 0 | 1778 | 9.6 % |
| ATK A9 Plus 2.0 | 765 | 684 | 192 | 1641 | 8.9 % |
| Scyrox V6 | 751 | 475 | 0 | 1226 | 6.6 % |
| Scyrox V8 / V8S | 229 | 841 | 0 | 1070 | 5.8 % |
| VXE MAD R / MAD R Major | 192 | 318 | 219 | 729 | 3.9 % |
| ATK GHOST Ultimate | 294 | 393 | 15 | 702 | 3.8 % |
| Pulsar Xlite v4 Mini | 303 | 333 | 0 | 636 | 3.4 % |
| ATK Phantom Ultimate | 252 | 327 | 0 | 579 | 3.1 % |
| ATK Z1 V2 Ultra | 129 | 411 | 18 | 558 | 3.0 % |
| Pulsar X2A v3 | 270 | 225 | 0 | 495 | 2.7 % |
| ATK Dragonfly A9 NB Ultra | 156 | 126 | 0 | 282 | 1.5 % |
| ATK Fierce X | 72 | 180 | 0 | 252 | 1.4 % |
| Pulsar X2 CrazyLight Mini | 0 | 215 | 0 | 215 | 1.2 % |
| ATK Y9 Ultimate | 72 | 123 | 0 | 195 | 1.1 % |
| ATK U2 V2 Mini | 15 | 63 | 15 | 93 | 0.5 % |
| Pulsar X2H v3 Mini | 0 | 90 | 0 | 90 | 0.5 % |
| ATK GHOST Extreme | 81 | 0 | 0 | 81 | 0.4 % |
| ATK U2 V2 Ultimate | 45 | 0 | 0 | 45 | 0.2 % |
| ATK ZERO | 0 | 3 | 0 | 3 | 0.0 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**10 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK Blazing Sky F1 V2** (`atk_f1_v2`)
- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **ATK Duckbill** (`atk_duckbill`)
- **Pulsar X2 CrazyLight Medium** (`pulsar_x2_crazylight_medium`)
- **Pulsar X2H CrazyLight Mini** (`pulsar_x2h_crazylight_mini`)
- **Pulsar Xlite CrazyLight Medium** (`pulsar_xlite_crazylight_medium`)
- **Pulsar Xlite v4 Large** (`pulsar_xlite_v4_large`)
- **Pulsar Xlite v4 Medium** (`pulsar_xlite_v4_medium`)
- **VXE Dragonfly X3 / X3 Pro / X3 Turbo** (`vxe_x3`)

### Pourquoi elles ne sortent pas

| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |
|---|---:|---:|---:|---|
| ATK A9 Air | 11172 | 0 | 7350 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky F1 V2 | 0 | 11760 | 6762 | donnée absente : compatibilité de prise (statut non vérifié) |
| ATK Blazing Sky U2 Mini | 3780 | 5544 | 9198 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| ATK Duckbill | 0 | 12348 | 6174 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : compatibilité de prise (statut non vérifié) |
| Pulsar X2H CrazyLight Mini | 2520 | 3990 | 12012 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite CrazyLight Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Large | 720 | 720 | 17082 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 1792 | 10752 | 5978 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 435 | 435 | 435 | 435 | 4341 |
| ATK A9 Ultimate | 573 | 603 | 537 | 582 | 2616 |
| ATK X1 V2 Ultra Max | 564 | 657 | 657 | 657 | 1317 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 300 | 300 | 300 | 300 | 2232 |
| VXE Dragonfly R1 / R1 Pro | 174 | 174 | 174 | 174 | 2579 |
| ATK A9 Mini | 363 | 387 | 336 | 408 | 1596 |
| ATK F1 V3 Ultimate | 452 | 479 | 464 | 506 | 1065 |
| Pulsar X2 v3 Mini | 254 | 381 | 381 | 381 | 381 |
| ATK A9 Plus 2.0 | 84 | 153 | 99 | 99 | 1206 |
| Scyrox V6 | 180 | 192 | 273 | 189 | 392 |
| Scyrox V8 / V8S | 49 | 181 | 229 | 181 | 430 |
| VXE MAD R / MAD R Major | 66 | 66 | 66 | 66 | 465 |
| ATK GHOST Ultimate | 108 | 138 | 102 | 60 | 294 |
| Pulsar Xlite v4 Mini | 96 | 135 | 135 | 135 | 135 |
| ATK Phantom Ultimate | 42 | 126 | 147 | 138 | 126 |
| ATK Z1 V2 Ultra | 51 | 69 | 90 | 60 | 288 |
| Pulsar X2A v3 | 63 | 108 | 108 | 108 | 108 |
| ATK Dragonfly A9 NB Ultra | 0 | 42 | 78 | 78 | 84 |
| ATK Fierce X | 21 | 51 | 21 | 39 | 120 |
| Pulsar X2 CrazyLight Mini | 43 | 43 | 43 | 43 | 43 |
| ATK Y9 Ultimate | 24 | 24 | 24 | 24 | 99 |
| ATK U2 V2 Mini | 6 | 6 | 6 | 6 | 69 |
| Pulsar X2H v3 Mini | 18 | 18 | 18 | 18 | 18 |
| ATK GHOST Extreme | 0 | 0 | 0 | 81 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 45 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 | 3 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 2433 | 2748 | 900 |
| ATK A9 Ultimate | 3258 | 1653 | 0 |
| ATK X1 V2 Ultra Max | 2244 | 1608 | 0 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1176 | 2256 | 0 |
| VXE Dragonfly R1 / R1 Pro | 1167 | 1782 | 326 |
| ATK A9 Mini | 2301 | 621 | 168 |
| ATK F1 V3 Ultimate | 0 | 1344 | 1622 |
| Pulsar X2 v3 Mini | 0 | 1005 | 773 |
| ATK A9 Plus 2.0 | 636 | 459 | 546 |
| Scyrox V6 | 126 | 102 | 998 |
| Scyrox V8 / V8S | 0 | 564 | 506 |
| VXE MAD R / MAD R Major | 300 | 429 | 0 |
| ATK GHOST Ultimate | 87 | 615 | 0 |
| Pulsar Xlite v4 Mini | 636 | 0 | 0 |
| ATK Phantom Ultimate | 579 | 0 | 0 |
| ATK Z1 V2 Ultra | 558 | 0 | 0 |
| Pulsar X2A v3 | 0 | 495 | 0 |
| ATK Dragonfly A9 NB Ultra | 180 | 102 | 0 |
| ATK Fierce X | 0 | 252 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 180 | 35 |
| ATK Y9 Ultimate | 96 | 99 | 0 |
| ATK U2 V2 Mini | 0 | 93 | 0 |
| Pulsar X2H v3 Mini | 0 | 90 | 0 |
| ATK GHOST Extreme | 6 | 75 | 0 |
| ATK U2 V2 Ultimate | 0 | 45 | 0 |
| ATK ZERO | 0 | 3 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 |
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
| VXE Dragonfly V3 / V3 Pro | 1727 | 1727 | 1727 | 900 |
| ATK A9 Ultimate | 1637 | 1637 | 1637 | 0 |
| ATK X1 V2 Ultra Max | 1284 | 1284 | 1284 | 0 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1144 | 1144 | 1144 | 0 |
| VXE Dragonfly R1 / R1 Pro | 983 | 983 | 983 | 326 |
| ATK A9 Mini | 974 | 974 | 974 | 168 |
| ATK F1 V3 Ultimate | 448 | 448 | 448 | 1622 |
| Pulsar X2 v3 Mini | 335 | 335 | 335 | 773 |
| ATK A9 Plus 2.0 | 365 | 365 | 365 | 546 |
| Scyrox V6 | 76 | 76 | 76 | 998 |
| Scyrox V8 / V8S | 188 | 188 | 188 | 506 |
| VXE MAD R / MAD R Major | 243 | 243 | 243 | 0 |
| ATK GHOST Ultimate | 234 | 234 | 234 | 0 |
| Pulsar Xlite v4 Mini | 212 | 212 | 212 | 0 |
| ATK Phantom Ultimate | 193 | 193 | 193 | 0 |
| ATK Z1 V2 Ultra | 186 | 186 | 186 | 0 |
| Pulsar X2A v3 | 165 | 165 | 165 | 0 |
| ATK Dragonfly A9 NB Ultra | 94 | 94 | 94 | 0 |
| ATK Fierce X | 84 | 84 | 84 | 0 |
| Pulsar X2 CrazyLight Mini | 60 | 60 | 60 | 35 |
| ATK Y9 Ultimate | 65 | 65 | 65 | 0 |
| ATK U2 V2 Mini | 31 | 31 | 31 | 0 |
| Pulsar X2H v3 Mini | 30 | 30 | 30 | 0 |
| ATK GHOST Extreme | 27 | 27 | 27 | 0 |
| ATK U2 V2 Ultimate | 15 | 15 | 15 | 0 |
| ATK ZERO | 1 | 1 | 1 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 24.9/40 | 35/40 | 10/40 | 12474 |
| ATK A9 Ultimate | 22.8/40 | 35/40 | 10/40 | 12768 |
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 8064 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 20.1/40 | 35/40 | 10/40 | 12096 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 35/40 | 10/40 | 14742 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 5292 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| Pulsar Xlite v4 Mini | 25.7/40 | 35/40 | 15/40 | 2520 |
| ATK Phantom Ultimate | 25.9/40 | 35/40 | 10/40 | 7770 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 6720 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK Dragonfly A9 NB Ultra | 23.5/40 | 35/40 | 10/40 | 9576 |
| ATK Fierce X | 27.6/40 | 35/40 | 20/40 | 3780 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 5376 |
| ATK U2 V2 Mini | 25.4/40 | 35/40 | 15/40 | 4410 |
| Pulsar X2H v3 Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK U2 V2 Ultimate | 22.6/40 | 35/40 | 15/40 | 4704 |
| ATK ZERO | 22.2/40 | 35/40 | 10/40 | 9828 |
| ATK A9 Air | 22.8/40 | 35/40 | 10/40 | 11172 |
| ATK Blazing Sky F1 V2 | — | — | — | 0 |
| ATK Blazing Sky U2 Mini | 25.4/40 | 35/40 | 15/40 | 3780 |
| ATK Duckbill | — | — | — | 0 |
| Pulsar X2 CrazyLight Medium | 30.7/40 | 40/40 | 20/40 | 4830 |
| Pulsar X2H CrazyLight Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| Pulsar Xlite CrazyLight Medium | 20.4/40 | 30/40 | 15/40 | 2880 |
| Pulsar Xlite v4 Large | 18.8/40 | 25/40 | 15/40 | 720 |
| Pulsar Xlite v4 Medium | 20.4/40 | 30/40 | 15/40 | 2880 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 19.4/40 | 30/40 | 10/40 | 1792 |

## Ce qui manque, souris par souris (à trouver, jamais à inventer)

- **Sans aucune compatibilité de prise publiée (1 souris)** : jamais classables, donc jamais proposées, quel que soit le profil. Seule une publication du fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.
  - ATK Blazing Sky F1 V2 (`atk_f1_v2`) — 41,95 €
- **Sans position de bosse publiée (1 souris)** : « à vérifier » dès que la prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.
  - VXE Dragonfly X3 / X3 Pro / X3 Turbo (`vxe_x3`)
- **Sans hauteur de boutons documentée (25 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée (règle du propriétaire : jamais d'invention).

