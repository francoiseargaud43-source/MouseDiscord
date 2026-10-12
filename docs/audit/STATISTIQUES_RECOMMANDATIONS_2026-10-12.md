# Statistiques de recommandation — 2026-10-12

Grille : **18 522 profils** (longueurs 140–240 mm  largeurs 60–125 mm  trois prises  trois thénars (sauté en Fingertip)  cinq modes et cinq budgets personnalisés).

Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places (match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, sans aucune donnée ajoutée pour l'étude.

## Résultats vides et repli de coque (2026-10-12)

- **Profils sans aucun résultat : 252** sur 18522 (1.4 %).
  - budget inférieur à la souris qui convient la moins chère : 252
  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée (compatibilité de prise) : **0**
- **Profils où DEUX places montrent la même coque : 342** (1.8 %).
  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de disparaître. Les paires concernées, par fréquence :
  - `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` : 210 profils
  - `atk_a9_plus` + `atk_a9_ultimate` : 54 profils
  - `atk_f1_ultimate` + `atk_f1_v2` : 48 profils
  - `atk_a9_nb` + `atk_a9_plus` : 18 profils
  - `atk_a9_nb` + `atk_a9_ultimate` : 12 profils
  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas d'autre coque à prix égal ou inférieur.

## Nombre de fois où chaque souris est recommandée

| Souris | Idéal | Alternative | Économie | Total | % des profils |
|---|---:|---:|---:|---:|---:|
| VXE Dragonfly V3 / V3 Pro | 3759 | 2055 | 1899 | 7713 | 41.6 % |
| ATK X1 V2 Ultra Max | 4971 | 1440 | 90 | 6501 | 35.1 % |
| ATK Blazing Sky F1 V2 | 1254 | 2283 | 57 | 3594 | 19.4 % |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1068 | 1050 | 1059 | 3177 | 17.2 % |
| ATK A9 Ultimate | 894 | 1605 | 99 | 2598 | 14.0 % |
| VXE Dragonfly R1 / R1 Pro | 576 | 1119 | 837 | 2532 | 13.7 % |
| ATK A9 Mini | 1542 | 912 | 12 | 2466 | 13.3 % |
| Pulsar X2 v3 Mini | 1017 | 675 | 0 | 1692 | 9.1 % |
| Scyrox V6 | 673 | 296 | 0 | 969 | 5.2 % |
| ATK ZERO | 276 | 465 | 0 | 741 | 4.0 % |
| ATK A9 Plus 2.0 | 330 | 327 | 0 | 657 | 3.5 % |
| Pulsar Xlite v4 Mini | 303 | 330 | 0 | 633 | 3.4 % |
| ATK Phantom Ultimate | 252 | 327 | 0 | 579 | 3.1 % |
| Scyrox V8 / V8S | 229 | 228 | 0 | 457 | 2.5 % |
| ATK Z1 V2 Ultra | 129 | 291 | 0 | 420 | 2.3 % |
| ATK F1 V3 Ultimate | 388 | 30 | 0 | 418 | 2.3 % |
| VXE MAD R / MAD R Major | 90 | 189 | 123 | 402 | 2.2 % |
| Pulsar X2A v3 | 135 | 210 | 0 | 345 | 1.9 % |
| ATK GHOST Ultimate | 93 | 204 | 0 | 297 | 1.6 % |
| Pulsar X2 CrazyLight Mini | 0 | 210 | 0 | 210 | 1.1 % |
| ATK Dragonfly A9 NB Ultra | 138 | 18 | 0 | 156 | 0.8 % |
| Pulsar X2H v3 Mini | 0 | 90 | 0 | 90 | 0.5 % |
| ATK Fierce X | 27 | 54 | 0 | 81 | 0.4 % |
| ATK GHOST Extreme | 81 | 0 | 0 | 81 | 0.4 % |
| ATK U2 V2 Ultimate | 45 | 0 | 0 | 45 | 0.2 % |
| ATK Y9 Ultimate | 0 | 24 | 0 | 24 | 0.1 % |
| ATK U2 V2 Mini | 0 | 6 | 0 | 6 | 0.0 % |
| ATK Duckbill | 0 | 3 | 0 | 3 | 0.0 % |
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
| ATK A9 Air | 11172 | 0 | 7350 | notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 3057 des 11172 profils où elle reste éligible · **une variante de sa coque (ATK A9 Ultimate) est classée devant elle sur 11172 des 11172 profils où elle est notée**, dont 9732 avec ATK A9 Ultimate — coque identique, prix différent |
| ATK Blazing Sky U2 Mini | 5544 | 3780 | 9198 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1131 des 5544 profils où elle reste éligible · **une variante de sa coque (ATK U2 V2 Mini) est classée devant elle sur 5544 des 5544 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2 CrazyLight Medium | 4830 | 3360 | 10332 | donnée absente : prise Palm · notée, jamais affichée : la 1re place revient à **Pulsar X2 v3 Mini** sur 1017 des 4830 profils où elle reste éligible · **une variante de sa coque (Pulsar X2A v3) est classée devant elle sur 4830 des 4830 profils où elle est notée** — coque identique, prix différent |
| Pulsar X2H CrazyLight Mini | 3990 | 2520 | 12012 | donnée absente : hauteur des boutons, prise Palm · notée, jamais affichée : la 1re place revient à **Pulsar X2 v3 Mini** sur 1017 des 3990 profils où elle reste éligible · **une variante de sa coque (Pulsar X2H v3 Mini) est classée devant elle sur 3990 des 3990 profils où elle est notée** — coque identique, prix différent |
| Pulsar Xlite CrazyLight Medium | 5760 | 900 | 11862 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 1356 des 5760 profils où elle reste éligible |
| Pulsar Xlite v4 Large | 1440 | 0 | 17082 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 621 des 1440 profils où elle reste éligible |
| Pulsar Xlite v4 Medium | 5760 | 900 | 11862 | donnée absente : hauteur des boutons, prise Fingertip · notée, jamais affichée : la 1re place revient à **ATK X1 V2 Ultra Max** sur 1356 des 5760 profils où elle reste éligible |
| VXE Dragonfly X3 / X3 Pro / X3 Turbo | 1792 | 10752 | 5978 | donnée absente : position de la bosse, hauteur des boutons · notée, jamais affichée : la 1re place revient à **VXE Dragonfly V3 / V3 Pro** sur 1056 des 1792 profils où elle reste éligible |

## Par mode (nombre de sorties)

| Souris | Économique | Qualité/Prix | Haut de gamme | Peu importe le prix | Budget personnalisé |
|---|---|---|---|---|---|
| VXE Dragonfly V3 / V3 Pro | 717 | 717 | 717 | 717 | 4845 |
| ATK X1 V2 Ultra Max | 810 | 825 | 753 | 783 | 3330 |
| ATK Blazing Sky F1 V2 | 389 | 434 | 264 | 111 | 2396 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 300 | 300 | 300 | 300 | 1977 |
| ATK A9 Ultimate | 372 | 318 | 294 | 342 | 1272 |
| VXE Dragonfly R1 / R1 Pro | 174 | 174 | 174 | 174 | 1836 |
| ATK A9 Mini | 312 | 339 | 282 | 369 | 1164 |
| Pulsar X2 v3 Mini | 252 | 360 | 360 | 360 | 360 |
| Scyrox V6 | 133 | 142 | 258 | 139 | 297 |
| ATK ZERO | 60 | 150 | 84 | 126 | 321 |
| ATK A9 Plus 2.0 | 78 | 102 | 18 | 18 | 441 |
| Pulsar Xlite v4 Mini | 93 | 135 | 135 | 135 | 135 |
| ATK Phantom Ultimate | 42 | 126 | 147 | 138 | 126 |
| Scyrox V8 / V8S | 3 | 51 | 229 | 51 | 123 |
| ATK Z1 V2 Ultra | 30 | 60 | 75 | 45 | 210 |
| ATK F1 V3 Ultimate | 0 | 6 | 50 | 338 | 24 |
| VXE MAD R / MAD R Major | 33 | 33 | 33 | 45 | 258 |
| Pulsar X2A v3 | 33 | 78 | 78 | 78 | 78 |
| ATK GHOST Ultimate | 39 | 57 | 63 | 18 | 120 |
| Pulsar X2 CrazyLight Mini | 42 | 42 | 42 | 42 | 42 |
| ATK Dragonfly A9 NB Ultra | 0 | 6 | 69 | 69 | 12 |
| Pulsar X2H v3 Mini | 18 | 18 | 18 | 18 | 18 |
| ATK Fierce X | 9 | 15 | 6 | 15 | 36 |
| ATK GHOST Extreme | 0 | 0 | 0 | 81 | 0 |
| ATK U2 V2 Ultimate | 0 | 0 | 45 | 0 | 0 |
| ATK Y9 Ultimate | 24 | 0 | 0 | 0 | 0 |
| ATK U2 V2 Mini | 0 | 0 | 0 | 0 | 6 |
| ATK Duckbill | 3 | 0 | 0 | 0 | 0 |
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
| VXE Dragonfly V3 / V3 Pro | 2433 | 2694 | 2586 |
| ATK X1 V2 Ultra Max | 3432 | 3069 | 0 |
| ATK Blazing Sky F1 V2 | 0 | 2598 | 996 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1017 | 2160 | 0 |
| ATK A9 Ultimate | 1896 | 702 | 0 |
| VXE Dragonfly R1 / R1 Pro | 1095 | 1437 | 0 |
| ATK A9 Mini | 2262 | 204 | 0 |
| Pulsar X2 v3 Mini | 0 | 993 | 699 |
| Scyrox V6 | 126 | 90 | 753 |
| ATK ZERO | 0 | 741 | 0 |
| ATK A9 Plus 2.0 | 378 | 279 | 0 |
| Pulsar Xlite v4 Mini | 633 | 0 | 0 |
| ATK Phantom Ultimate | 579 | 0 | 0 |
| Scyrox V8 / V8S | 0 | 372 | 85 |
| ATK Z1 V2 Ultra | 420 | 0 | 0 |
| ATK F1 V3 Ultimate | 0 | 297 | 121 |
| VXE MAD R / MAD R Major | 234 | 168 | 0 |
| Pulsar X2A v3 | 0 | 345 | 0 |
| ATK GHOST Ultimate | 87 | 210 | 0 |
| Pulsar X2 CrazyLight Mini | 0 | 180 | 30 |
| ATK Dragonfly A9 NB Ultra | 108 | 48 | 0 |
| Pulsar X2H v3 Mini | 0 | 90 | 0 |
| ATK Fierce X | 0 | 81 | 0 |
| ATK GHOST Extreme | 6 | 75 | 0 |
| ATK U2 V2 Ultimate | 0 | 45 | 0 |
| ATK Y9 Ultimate | 12 | 12 | 0 |
| ATK U2 V2 Mini | 0 | 6 | 0 |
| ATK Duckbill | 3 | 0 | 0 |
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
| VXE Dragonfly V3 / V3 Pro | 1709 | 1709 | 1709 | 2586 |
| ATK X1 V2 Ultra Max | 2167 | 2167 | 2167 | 0 |
| ATK Blazing Sky F1 V2 | 866 | 866 | 866 | 996 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 1059 | 1059 | 1059 | 0 |
| ATK A9 Ultimate | 866 | 866 | 866 | 0 |
| VXE Dragonfly R1 / R1 Pro | 844 | 844 | 844 | 0 |
| ATK A9 Mini | 822 | 822 | 822 | 0 |
| Pulsar X2 v3 Mini | 331 | 331 | 331 | 699 |
| Scyrox V6 | 72 | 72 | 72 | 753 |
| ATK ZERO | 247 | 247 | 247 | 0 |
| ATK A9 Plus 2.0 | 219 | 219 | 219 | 0 |
| Pulsar Xlite v4 Mini | 211 | 211 | 211 | 0 |
| ATK Phantom Ultimate | 193 | 193 | 193 | 0 |
| Scyrox V8 / V8S | 124 | 124 | 124 | 85 |
| ATK Z1 V2 Ultra | 140 | 140 | 140 | 0 |
| ATK F1 V3 Ultimate | 99 | 99 | 99 | 121 |
| VXE MAD R / MAD R Major | 134 | 134 | 134 | 0 |
| Pulsar X2A v3 | 115 | 115 | 115 | 0 |
| ATK GHOST Ultimate | 99 | 99 | 99 | 0 |
| Pulsar X2 CrazyLight Mini | 60 | 60 | 60 | 30 |
| ATK Dragonfly A9 NB Ultra | 52 | 52 | 52 | 0 |
| Pulsar X2H v3 Mini | 30 | 30 | 30 | 0 |
| ATK Fierce X | 27 | 27 | 27 | 0 |
| ATK GHOST Extreme | 27 | 27 | 27 | 0 |
| ATK U2 V2 Ultimate | 15 | 15 | 15 | 0 |
| ATK Y9 Ultimate | 8 | 8 | 8 | 0 |
| ATK U2 V2 Mini | 2 | 2 | 2 | 0 |
| ATK Duckbill | 1 | 1 | 1 | 0 |
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
| ATK Blazing Sky F1 V2 | 32.5/40 | 40/40 | 20/40 | 7056 |
| ATK Blazing Sky U2 / U2 Plus / U2 Ultimate | 20.1/40 | 35/40 | 10/40 | 12096 |
| ATK A9 Ultimate | 24.4/40 | 40/40 | 15/40 | 12768 |
| VXE Dragonfly R1 / R1 Pro | 20.8/40 | 35/40 | 10/40 | 14742 |
| ATK A9 Mini | 27.5/40 | 35/40 | 10/40 | 10290 |
| Pulsar X2 v3 Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| Scyrox V6 | 27.4/40 | 40/40 | 15/40 | 9324 |
| ATK ZERO | 26.1/40 | 40/40 | 10/40 | 9828 |
| ATK A9 Plus 2.0 | 24.3/40 | 35/40 | 15/40 | 12768 |
| Pulsar Xlite v4 Mini | 22.1/40 | 35/40 | 10/40 | 6510 |
| ATK Phantom Ultimate | 25.9/40 | 35/40 | 10/40 | 7770 |
| Scyrox V8 / V8S | 31.4/40 | 40/40 | 20/40 | 5292 |
| ATK Z1 V2 Ultra | 19.8/40 | 35/40 | 10/40 | 6720 |
| ATK F1 V3 Ultimate | 32.5/40 | 40/40 | 20/40 | 6174 |
| VXE MAD R / MAD R Major | 22.3/40 | 35/40 | 10/40 | 10752 |
| Pulsar X2A v3 | 30.7/40 | 40/40 | 20/40 | 4830 |
| ATK GHOST Ultimate | 24.9/40 | 35/40 | 10/40 | 9828 |
| Pulsar X2 CrazyLight Mini | 35.2/40 | 40/40 | 25/40 | 3990 |
| ATK Dragonfly A9 NB Ultra | 25.1/40 | 40/40 | 15/40 | 9576 |
| Pulsar X2H v3 Mini | 27.2/40 | 35/40 | 15/40 | 3990 |
| ATK Fierce X | 27.2/40 | 35/40 | 15/40 | 5544 |
| ATK GHOST Extreme | 24.9/40 | 35/40 | 10/40 | 9828 |
| ATK U2 V2 Ultimate | 17.6/40 | 35/40 | 5/40 | 9408 |
| ATK Y9 Ultimate | 18.8/40 | 25/40 | 15/40 | 5376 |
| ATK U2 V2 Mini | 22.9/40 | 35/40 | 5/40 | 6468 |
| ATK Duckbill | 18.5/40 | 30/40 | 10/40 | 6678 |
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
- **Sans hauteur de boutons documentée (20 souris)** : classées partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur rapporter les points que les autres gagnent).

Compléter ces trois familles est la seule façon de faire sortir les souris listées plus haut ; aucune valeur ne peut être devinée. Depuis le 2026-10-12, les sources tierces sont autorisées pour les données que le fabricant ne publie pas.

