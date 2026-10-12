# Mesure de la hauteur des boutons sur vues de profil (2026-10-12)

Réponse à la demande du propriétaire : « comment remplir la hauteur des boutons ? » — la voie choisie
est la **mesure sur les visuels officiels**, calibrée sur les souris dont la valeur est déjà connue.

## 1. Méthode (`tools/measure_button_height.py`)

1. Nettoyage du fond (couleur des bords) → silhouette de la souris.
2. Boîte englobante → longueur et hauteur en pixels.
3. **Contrôle qualité automatique** : le rapport longueur/hauteur mesuré est comparé aux cotes
   officielles. Au-delà de **6 %** d'écart, la vue est **refusée** : c'est une vue en perspective, la
   hauteur y est fausse. Aucune valeur n'est alors produite.
4. Échelle déduite de la hauteur officielle, puis relevé de la hauteur du dessus de la coque au
   **bord d'attaque des boutons** (5 % de la longueur depuis l'avant).
5. Classification à partir des références étalonnées, ou refus de trancher.

Le rapport mesuré est **sans dimension** : il ne dépend ni de la taille de la souris ni de
l'incertitude sur l'échelle de l'image — seule compte la qualité du profil.

## 2. Où se mesure la hauteur des boutons : la mesure l'a tranché

Balayage de plusieurs points de mesure sur deux souris dont la classe est **connue** :

| Point de mesure (depuis l'avant) | ATK F1 V2 (« bas » connu) | ATK Z1 V2 (« hauts » connu) | Écart |
|---|---|---|---|
| 5 % de la longueur | **43,3 %** | **55,1 %** | **+11,8 points** |
| 15 % | 71,0 % | 82,3 % | +11,3 points |
| 22 % | 83,9 % | 87,0 % | +3,1 points |
| 40 % | 99,3 % | 97,7 % | **inversé** |

Conclusion : la hauteur des boutons se lit **au bord d'attaque**, pas au tiers de la souris, où
l'écart devient négligeable puis s'inverse. L'outil relève donc à 5 % de la longueur.

## 3. Références et intervalle gris

Deux références seulement sont mesurables aujourd'hui (ce sont les deux souris dont la classe est
connue **et** dont une vue exploitable existe) :

| Référence | Classe connue | Mesure |
|---|---|---|
| ATK Blazing Sky F1 V2 | bas | **43,3 %** |
| ATK Z1 V2 | hauts | **55,1 %** |

Règle de classement (marge de 2 points) : ≤ 45,3 % → **bas** ; ≥ 53,1 % → **hauts** ; entre les deux →
**non tranché**. Aucune classe « moyens » n'est produite tant qu'une référence de ce type n'est pas
mesurée : une classe inventée serait pire qu'une classe absente.

## 4. Mesures obtenues (vues acceptées par le contrôle qualité)

| Souris | Mesure | Qualité du profil | Résultat |
|---|---|---|---|
| ATK F1 V2 (référence) | 43,3 % | 99 % | **bas** ✔ (cohérent avec la valeur connue) |
| ATK Z1 V2 (référence) | 55,1 % | 97 % | **hauts** ✔ (cohérent) |
| ATK A9 Ultimate | 47,3 % | 95 % | non tranché (intervalle gris) |
| ATK ZERO | 48,0 % | 100 % | non tranché (intervalle gris) |

## 5. Limite mesurée : les vues exploitables sont rares

Sur les vues officielles testées (ATK Store, Pulsar EU, revendeurs), **4 sur 11** passent le contrôle
qualité. Les autres sont refusées avec leur écart chiffré :

| Vue | Écart au rapport officiel | Motif |
|---|---|---|
| Pulsar Xlite v4 « Side_1 » (rendu officiel) | 86 % | rendu en perspective/portrait |
| Pulsar X2 v3 « side » (rendu officiel) | 90 % | idem |
| Scyrox V8 (revendeur) | 90 % | planche multi-vues |
| ATK F1 V3 « side » (test) | 15 % | vue plongeante |
| ATK X1 series « side profile » | 52 % | vue plongeante |

Autrement dit : la méthode fonctionne et est exacte (elle retrouve les deux classes connues), mais elle
ne couvre pas les 36 souris du catalogue — chaque modèle exige de trouver **une vue de profil
réellement orthographique**, ce qui n'existe pas toujours publiquement. Les mesures se feront donc
souris par souris, au fil des vues trouvables, jamais par extrapolation.

## 6. État du fichier de données

Aucune valeur n'a été écrite dans `data/mouse_db.json` à ce stade : les deux seules mesures tranchées
concernent des souris dont la valeur était **déjà connue** (F1 V2, Z1 V2 — vérification du calibrage).
Les valeurs « non tranchées » (A9 Ultimate 47,3 %, ZERO 48,0 %) ne sont pas inscrites : elles ne
permettent pas de choisir entre « moyens » et « hauts ». **Le relevé reste donc à faire**, modèle par
modèle, à mesure que des vues exploitables sont trouvées.

## 13. Campagne du 2026-10-12 (24e passe) : ce que la méthode peut et ne peut pas dire

Nouvelles images officielles ATK (CDN `atk.store`, 1500 px) récupérées par recherche d'images, puis
mesurées avec l'outil calibré. **Quatre vues acceptées** par le contrôle de perspective, **six refusées**
(« vue en perspective ») :

| Image | Mesure `--front right` | Mesure `--front left` | Décision |
|---|---:|---:|---|
| ATK Z1 V2 Ultra (référence « High » du propriétaire) | **55,0 % → High** ✔ | 37,0 % (sens inversé) | référence validée |
| ATK ZERO, profil blanc | **43,0 % → Low** (limite) | 47,8 % → aucune | **rien** : les deux lectures encadrent le seuil |
| ATK ZERO, coque givrée | 48,0 % → aucune | **44,0 % → Low** | **rien** : l'autre photo du même modèle ne dit pas la même chose |
| ATK A9 Ultimate | 47,3 % → aucune | 48,3 % → aucune | **rien** : bande grise (l'A9 Plus, coque identique, est « Mid ») |
| ATK X1 V2 Ultra Max (référence « Mid » du propriétaire) | 48,0 % → aucune | **44,0 % → Low** | **rien** : la lecture « Low » contredirait le propriétaire |

Refus : ATK U2 (rapport 2,69 vs 3,16), ATK Y9 Ultimate (écart 6,7 %), ATK F1 V3 Ultimate, Scyrox V8,
ATK A9 Plus 2.0, Scyrox V6.

**Ce que cela établit.** (1) La méthode est juste quand l'image est une vraie vue de profil *et* que
l'orientation est vérifiée : elle redonne la valeur du propriétaire à 0,1 point près sur la Z1 V2.
(2) Sa précision sur les photos web est de l'ordre de ± 2 à 3 points — insuffisante pour trancher un cas
limite (43,0 % contre un seuil à 43,3 %). (3) Les deux souris connues « Mid » du propriétaire mesurent
44,0 – 48,0 %, c'est-à-dire **dans** la bande grise : la bande 43,3 – 55,1 % correspond bien à « Mid »,
mais elle *touche* la référence « Low » (43,3 %) — **l'outil ne sépare pas finement « Low » et « Mid »**.

**Règle de publication retenue** : au moins **deux photos distinctes** de la souris, orientation vérifiée
à l'œil, **même classe** avec **au moins 3 points de marge** sur les deux seuils. Aucune souris testée
dans cette campagne ne remplit ces conditions → **aucune valeur n'a été écrite** dans `data/mouse_db.json`.

**Ce qui débloquerait la suite** : reconnaître la bande 43,3 – 55,1 % comme la classe « Mid » (question
posée au propriétaire). Sans cela, la méthode ne peut publier que les « High » très francs (≥ 55 %) et les
« Low » très francs (≤ 40 %) ; avec cela, la campagne peut couvrir les souris de profil bas, qui sont
majoritaires au catalogue.
