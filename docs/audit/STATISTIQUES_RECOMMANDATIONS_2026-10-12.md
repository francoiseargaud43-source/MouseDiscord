# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 252** sur 18522 (1.4 %).
  - budget inférieur à la souris qui convient la moins chère : 252
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **0**
- **Profils où DEUX places montrent la même coque : 299** (1.6 %).
  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de disparaître. Les paires concernées, par fréquence :
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 215 profils
  - `atk_a9_plus` + `atk_a9_ultimate` : 54 profils
  - `atk_a9_nb` + `atk_a9_plus` : 18 profils
  - `atk_a9_nb` + `atk_a9_ultimate` : 12 profils
  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas d'autre coque à prix égal ou inférieur.

## Nombre de fois où chaque souris est recommandée

| Souris | Idéal | Alternative | Économie | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| ATK X1 V2 Ultra Max | 4992 | 1482 | 60 | 6534 | 35.3 % |
| VXE Dragonfly V3 / V3 Pro | 2810 | 1478 | 1528 | 5816 | 31.4 % |
| ATK F1 V3 Ultimate | 2248 | 1350 | 475 | 4073 | 22.0 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1074 | 1119 | 1008 | 3201 | 17.3 % |
| VXE Dragonfly R1 / R1 Pro | 621 | 1606 | 774 | 3001 | 16.2 % |
| ATK A9 Ultimate | 915 | 1752 | 99 | 2766 | 14.9 % |
| ATK A9 Mini | 1542 | 980 | 12 | 2534 | 13.7 % |
| Pulsar X2 v3 Mini | 1069 | 709 | 0 | 1778 | 9.6 % |
| Scyrox V6 | 751 | 463 | 0 | 1214 | 6.6 % |
| ATK A9 Plus 2.0 | 471 | 517 | 192 | 1180 | 6.4 % |
| Scyrox V8 / V8S | 229 | 820 | 0 | 1049 | 5.7 % |
| Pulsar Xlite v4 Mini | 303 | 333 | 0 | 636 | 3.4 % |
| ATK Phantom Ultimate | 252 | 327 | 0 | 579 | 3.1 % |
| VXE MAD R / MAD R Major | 120 | 246 | 153 | 519 | 2.8 % |
| Pulsar X2A v3 | 270 | 225 | 0 | 495 | 2.7 % |
| ATK GHOST Ultimate | 165 | 282 | 0 | 447 | 2.4 % |
| ATK Z1 V2 Ultra | 129 | 291 | 0 | 420 | 2.3 % |
| Pulsar X2 CrazyLight Mini | 0 | 215 | 0 | 215 | 1.2 % |
| ATK Dragonfly A9 NB Ultra | 156 | 18 | 0 | 174 | 0.9 % |
| ATK Fierce X | 27 | 114 | 0 | 141 | 0.8 % |
| Pulsar X2H v3 Mini | 0 | 90 | 0 | 90 | 0.5 % |
| ATK GHOST Extreme | 81 | 0 | 0 | 81 | 0.4 % |
| ATK U2 V2 Ultimate | 45 | 0 | 0 | 45 | 0.2 % |
| ATK Y9 Ultimate | 0 | 24 | 0 | 24 | 0.1 % |
| ATK U2 V2 Mini | 0 | 9 | 0 | 9 | 0.0 % |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0.0 % |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0.0 % |
| ATK ZERO | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0.0 % |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0.0 % |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0.0 % |

## Souris jamais recommandées

**11 souris sur 36** ne sortent jamais sur cette grille :

- **ATK A9 Air** (`atk_a9_air`)
- **ATK Blazing Sky F1 V2** (`atk_f1_v2`)
- **ATK Blazing Sky U2 Mini** (`atk_u2_mini`)
- **ATK Duckbill** (`atk_duckbill`)
- **ATK ZERO** (`atk_zero`)
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
| ATK ZERO | 9828 | 0 | 8694 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : compatibilité de prise (statut non vérifié) |
| Pulsar X2H CrazyLight Mini | 2520 | 3990 | 12012 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite CrazyLight Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Large | 720 | 720 | 17082 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| Pulsar Xlite v4 Medium | 2880 | 3780 | 11862 | donnée absente : hauteur des boutons, compatibilité de prise (statut non vérifié) |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 1792 | 10752 | 5978 | donnée absente : position de la bosse, hauteur des boutons, compatibilité de prise (statut non vérifié) |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| ATK X1 V2 Ultra Max | 810 | 825 | 783 | 783 | 3333 |
| VXE Dragonfly V3 / V3 Pro | 435 | 435 | 435 | 435 | 4076 |
| ATK F1 V3 Ultimate | 521 | 539 | 527 | 572 | 1914 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 300 | 300 | 300 | 300 | 2001 |
| VXE Dragonfly R1 / R1 Pro | 174 | 174 | 174 | 174 | 2305 |
| ATK A9 Ultimate | 381 | 342 | 300 | 342 | 1401 |
| ATK A9 Mini | 306 | 345 | 282 | 369 | 1232 |
| Pulsar X2 v3 Mini | 254 | 381 | 381 | 381 | 381 |
| Scyrox V6 | 180 | 189 | 273 | 186 | 386 |
| ATK A9 Plus 2.0 | 120 | 150 | 54 | 54 | 802 |
| Scyrox V8 / V8S | 52 | 175 | 229 | 175 | 418 |
| Pulsar Xlite v4 Mini | 96 | 135 | 135 | 135 | 135 |
| ATK Phantom Ultimate | 42 | 126 | 147 | 138 | 126 |
| VXE MAD R / MAD R Major | 45 | 45 | 45 | 45 | 339 |
| Pulsar X2A v3 | 63 | 108 | 108 | 108 | 108 |
| ATK GHOST Ultimate | 63 | 90 | 78 | 24 | 192 |
| ATK Z1 V2 Ultra | 30 | 60 | 75 | 45 | 210 |
| Pulsar X2 CrazyLight Mini | 43 | 43 | 43 | 43 | 43 |
| ATK Dragonfly A9 NB Ultra | 0 | 6 | 78 | 78 | 12 |
| ATK Fierce X | 9 | 30 | 6 | 30 | 66 |
| Pulsar X2H v3 Mini | 18 | 18 | 18 | 18 | 18 |
| ATK GHOST Extreme | 0 | 0 | 0 | 81 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 45 | 0 | 0 |
| ATK Y9 Ultimate | 24 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 9 |
| ATK A9 Air | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 | 0 |

## Par prise (nombre de sorties)

| Souris | Palm | Claw | Fingertip |
|---|---:|---:|---:|
| ATK X1 V2 Ultra Max | 3432 | 3102 | 0 |
| VXE Dragonfly V3 / V3 Pro | 2433 | 2730 | 653 |
| ATK F1 V3 Ultimate | 0 | 2157 | 1916 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1017 | 2184 | 0 |
| VXE Dragonfly R1 / R1 Pro | 1095 | 1590 | 316 |
| ATK A9 Ultimate | 1896 | 870 | 0 |
| ATK A9 Mini | 2262 | 225 | 47 |
| Pulsar X2 v3 Mini | 0 | 1005 | 773 |
| Scyrox V6 | 126 | 90 | 998 |
| ATK A9 Plus 2.0 | 378 | 330 | 472 |
| Scyrox V8 / V8S | 0 | 543 | 506 |
| Pulsar Xlite v4 Mini | 636 | 0 | 0 |
| ATK Phantom Ultimate | 579 | 0 | 0 |
| VXE MAD R / MAD R Major | 234 | 285 | 0 |
| Pulsar X2A v3 | 0 | 495 | 0 |
| ATK GHOST Ultimate | 87 | 360 | 0 |
| ATK Z1 V2 Ultra | 420 | 0 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 180 | 35 |
| ATK Dragonfly A9 NB Ultra | 108 | 66 | 0 |
| ATK Fierce X | 0 | 141 | 0 |
| Pulsar X2H v3 Mini | 0 | 90 | 0 |
| ATK GHOST Extreme | 6 | 75 | 0 |
| ATK U2 V2 Ultimate | 0 | 45 | 0 |
| ATK Y9 Ultimate | 12 | 12 | 0 |
| ATK U2 V2 Mini | 0 | 9 | 0 |
| ATK A9 Air | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 |
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
| ATK X1 V2 Ultra Max | 2178 | 2178 | 2178 | 0 |
| VXE Dragonfly V3 / V3 Pro | 1721 | 1721 | 1721 | 653 |
| ATK F1 V3 Ultimate | 719 | 719 | 719 | 1916 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1067 | 1067 | 1067 | 0 |
| VXE Dragonfly R1 / R1 Pro | 895 | 895 | 895 | 316 |
| ATK A9 Ultimate | 922 | 922 | 922 | 0 |
| ATK A9 Mini | 829 | 829 | 829 | 47 |
| Pulsar X2 v3 Mini | 335 | 335 | 335 | 773 |
| Scyrox V6 | 72 | 72 | 72 | 998 |
| ATK A9 Plus 2.0 | 236 | 236 | 236 | 472 |
| Scyrox V8 / V8S | 181 | 181 | 181 | 506 |
| Pulsar Xlite v4 Mini | 212 | 212 | 212 | 0 |
| ATK Phantom Ultimate | 193 | 193 | 193 | 0 |
| VXE MAD R / MAD R Major | 173 | 173 | 173 | 0 |
| Pulsar X2A v3 | 165 | 165 | 165 | 0 |
| ATK GHOST Ultimate | 149 | 149 | 149 | 0 |
| ATK Z1 V2 Ultra | 140 | 140 | 140 | 0 |
| Pulsar X2 CrazyLight Mini | 60 | 60 | 60 | 35 |
| ATK Dragonfly A9 NB Ultra | 58 | 58 | 58 | 0 |
| ATK Fierce X | 47 | 47 | 47 | 0 |
| Pulsar X2H v3 Mini | 30 | 30 | 30 | 0 |
| ATK GHOST Extreme | 27 | 27 | 27 | 0 |
| ATK U2 V2 Ultimate | 15 | 15 | 15 | 0 |
| ATK Y9 Ultimate | 8 | 8 | 8 | 0 |
| ATK U2 V2 Mini | 3 | 3 | 3 | 0 |
| ATK A9 Air | 0 | 0 | 0 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 0 | 0 | 0 |
| ATK Blazing Sky U2 Mini | 0 | 0 | 0 | 0 |
| ATK Duckbill | 0 | 0 | 0 | 0 |
| ATK ZERO | 0 | 0 | 0 | 0 |
| Pulsar X2 CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar X2H CrazyLight Mini | 0 | 0 | 0 | 0 |
| Pulsar Xlite CrazyLight Medium | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Large | 0 | 0 | 0 | 0 |
| Pulsar Xlite v4 Medium | 0 | 0 | 0 | 0 |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 0 | 0 | 0 | 0 |

## Points obtenus quand la souris est classée

| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |
|---|---:|---:|---:|---:|
| ATK X1 V2 Ultra Max | 23.4/40 | 35/40 | 15/40 | 10752 |
| VXE Dragonfly V3 / V3 Pro | 24.9/40 | 35/40 | 10/40 | 12474 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 6174 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 20.1/40 | 35/40 | 10/40 | 12096 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 35/40 | 10/40 | 14742 |
| ATK A9 Ultimate | 22.8/40 | 35/40 | 10/40 | 12768 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| Pulsar Xlite v4 Mini | 25.7/40 | 35/40 | 15/40 | 2520 |
| ATK Phantom Ultimate | 25.9/40 | 35/40 | 10/40 | 7770 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 6720 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK Dragonfly A9 NB Ultra | 23.5/40 | 35/40 | 10/40 | 9576 |
| ATK Fierce X | 27.6/40 | 35/40 | 20/40 | 3780 |
| Pulsar X2H v3 Mini | 28.2/40 | 35/40 | 20/40 | 2520 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK U2 V2 Ultimate | 22.6/40 | 35/40 | 15/40 | 4704 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 5376 |
| ATK U2 V2 Mini | 25.4/40 | 35/40 | 15/40 | 4410 |
| ATK A9 Air | 22.8/40 | 35/40 | 10/40 | 11172 |
| ATK Blazing Sky F1 V2 | — | — | — | 0 |
| ATK Blazing Sky U2 Mini | 25.4/40 | 35/40 | 15/40 | 3780 |
| ATK Duckbill | — | — | — | 0 |
| ATK ZERO | 22.2/40 | 35/40 | 10/40 | 9828 |
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

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée. Depuis le 2026-10-12, les sources tierces sont autorisées pour les données que le fabricant ne publie pas.

