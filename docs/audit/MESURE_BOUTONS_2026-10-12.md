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

Identité des deux références : l'image de la « Z1 » porte « Z1 ULTIMATE » imprimé (55,0 %, molette à
droite) et l'image « F1 » retenue porte « F1 ULTIMATE » imprimé (42 %, molette à droite) — vérifié à
l'œil au §13, car **aucun nom de fichier ne prouve un modèle**.

Règle de classement (marge de 2 points) : ≤ 45,3 % → **bas** ; ≥ 53,1 % → **hauts** ; entre les deux →
**non tranché**. Aucune classe « moyens » n'est produite tant qu'une référence de ce type n'est pas
mesurée : une classe inventée serait pire qu'une classe absente.

## 4. Mesures obtenues (vues acceptées par le contrôle qualité)

| Souris | Mesure | Qualité du profil | Résultat |
|---|---|---|---|
| ATK F1 V2 (référence) | 43,3 % | 99 % | **bas** ✔ (cohérent avec la valeur connue) |
| ATK Z1 V2 (référence) | 55,1 % | 97 % | **hauts** ✔ (cohérent) |
| ATK A9 Air (photo portant « A9 AIR » imprimé) | 47,3 % | 95 % | non tranché (intervalle gris) —
ré-attribuée au §13 : la photo était rangée sous le nom « A9 Ultimate » |
| ATK ZERO (photo portant « ZERO » imprimé, molette à droite) | 43,0 % | 100 % | **bas** —
une seule image à identité vérifiée, donc non publiable (§13) |

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
Les valeurs « non tranchées » (A9 Air 47,3 %) ne sont pas inscrites : elles ne permettent pas de
choisir entre « moyens » et « hauts ». **Le relevé reste donc à faire**, modèle par modèle, à mesure
que des vues **identifiées** et exploitables sont trouvées (§13).

## 13. Campagne du 2026-10-12 (24e passe) : le contrôle d'identité change la conclusion

### 13.1 Fait mesuré : une même photo circule sous plusieurs noms de modèles

Nouveau `tools/image_corpus_check.py` (testé) : les fichiers sont regroupés par **empreinte SHA-256**.
Sur le corpus de recherche (92 fichiers) : **70 images distinctes et 10 groupes de doublons**, dont une
image qui circule sous **huit noms de modèles** (Z1 V2, F1 Ultimate, ZERO, Phantom Ultimate, U2 Mini, U2,
X1 series, X1 V2 Ultra Max). Une image qui porte plusieurs noms ne peut être attribuée à aucun : elle est
écartée des mesures. L'identité se vérifie donc **à l'œil sur l'image** (nom imprimé sur la coque, logo),
jamais sur le nom du fichier.

### 13.2 Ré-attribution des mesures de la campagne (vérifiée visuellement)

| Image (tel qu'elle circule) | Ce qu'elle montre réellement | Avant de l'image | Mesure à l'endroit | Classe |
|---|---|---|---|---:|---|
| `…z1-v2-gaming-mouse-side--1.jpg` (8 noms) | « **Z1 ULTIMATE** » imprimé, molette à droite | droite | **55,0 %** | High (= valeur propriétaire ✔) |
| `…f1-ultimate-white-mouse--3.jpg` | « **F1 ULTIMATE** » imprimé, molette à droite | droite | **42,0 %** | Low (= valeur propriétaire ✔) |
| `…zero-gaming-mouse-side-p-1.jpg` (= ultralight-3) | « **ZERO** » imprimé, molette à droite | droite | **43,0 %** | Low (une seule image vérifiée) |
| `…a9-ultimate-wireless-mouse-side-view-1.jpg` (= a9-plus-1, y9-1) | « **A9 AIR** » imprimé, molette à droite | droite | **47,3 %** | aucune (bande grise) |
| `…x1-v2-mouse-side-view-wh-1.jpg` (= zero-p-2, zero-ultralight-2) | souris ATK blanche, **aucun nom imprimé** | gauche (molette + logo) | **44,0 %** | image **inexploitable** : identité non établie |

### 13.3 Corrections apportées à la première rédaction de cette passe

1. « Deux photos du même modèle donnent 43,0 % et 48,0 % » — **faux**. La lecture 48,0 % mesurait
   l'**arrière** d'une image dont l'avant est à gauche (molette et logo) ; à l'endroit elle lit 44,0 %.
2. « Une souris « Mid » (X1 V2 Ultra Max) se fait classer « Low » » — **non établi**. L'image invoquée ne
   porte aucun nom de modèle et ne peut donc ni confirmer ni contredire la valeur du propriétaire.
3. « ATK A9 Ultimate 47,3 % » — la photo porte « **A9 AIR** » imprimé : la mesure concerne l'A9 Air (dont
   la classe est inconnue), pas l'A9 Ultimate.

### 13.4 Règle de publication (inchangée sur le fond, durcie sur la preuve d'identité)

Une hauteur de boutons n'est écrite que si :

1. l'**identité** du modèle est vérifiée visuellement sur l'image (nom imprimé sur la coque) ;
2. **deux images distinctes** (empreintes SHA-256 différentes) de ce modèle passent le contrôle de
   perspective et donnent la **même classe**, avec **au moins 3 points de marge** sur les seuils.

Aujourd'hui la ZERO a **une** image à identité vérifiée (43,0 % → Low) : il lui en manque une seconde.
Aucune souris ne remplit les deux conditions → **aucune valeur écrite** dans `data/mouse_db.json`, les
25 souris restent `Inconnu`, et le catalogue ne gagne aucune valeur inventée.

### 13.5 Vues refusées (inchangé)

ATK U2 (rapport 2,69 vs 3,16), ATK Y9 Ultimate (écart 6,7 %), ATK F1 V3 Ultimate, Scyrox V8, ATK A9 Plus
2.0, Scyrox V6 : contrôle de perspective en échec, aucune valeur produite.

**Prochaine étape utile** : chercher des vues **portant le nom imprimé** des souris à boutons « moyens »
(A9 Plus, X1 V2 Ultra Max, Scyrox V6) — leur mesure étalonnerait la classe « Mid », aujourd'hui produite
par aucune référence.
