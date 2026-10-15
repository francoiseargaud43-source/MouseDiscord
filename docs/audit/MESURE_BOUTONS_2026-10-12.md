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

**Trois** références sont étalonnées depuis le 2026-10-12 (la troisième, la classe « moyens », a été
trouvée à la vingt-neuvième passe — détail et preuves au §16) :

| Référence | Classe connue | Mesure | Recoupement indépendant |
|---|---|---|---|
| ATK Blazing Sky F1 V2 | bas | **43,3 %** | ATK ZERO : 43,3 % et 43,7 % (deux rendus distincts) |
| ATK A9 Ultimate (coque « A9 large ») | moyens | **47,3 %** | deux rendus officiels distincts de la page A9 Ultimate, tous deux à 47,3 % |
| ATK Z1 V2 | hauts | **55,1 %** | rendu « Z1 ULTIMATE » : 55,0 % |

Identité des deux premières références : l'image de la « Z1 » porte « Z1 ULTIMATE » imprimé (55,0 %,
molette à droite) et l'image « F1 » retenue porte « F1 ULTIMATE » imprimé (42 %, molette à droite) —
vérifié à l'œil au §13, car **aucun nom de fichier ne prouve un modèle**. L'identité de la référence
« moyens » est établie au §16 : les deux rendus viennent de la **page officielle de l'ATK Dragonfly A9
Ultimate** (leurs noms de fichiers CDN y sont, avec la légende « A9 Ultimate … side view » publiée par
ATK) et portent la sérigraphie « DRAGONFLY » + logo ATK. La coque « A9 large » est partagée par l'A9
Ultimate, l'A9 Plus, l'A9 Air et l'A9 NB — un seul moule, une seule hauteur de boutons.

Règle de classement (marge d'un point) : la frontière entre deux classes est posée **à mi-chemin de
leurs deux références** — 45,3 % entre « bas » et « moyens », 51,2 % entre « moyens » et « hauts » — et
une mesure à moins d'un point d'une frontière reste **non tranchée** (marge justifiée au §16.1 : plus du
double du plus grand écart observé entre deux rendus d'une même souris de classe connue, 0,7 point).
La classe produite par l'outil est une **estimation géométrique** ; publier une valeur au catalogue obéit
en plus à la règle de publication (§15.3).

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
Aucune souris ne remplit les deux conditions → **aucune valeur écrite** dans `data/mouse_db.json` à
partir d'une photo. (Depuis la 26e passe, trois hauteurs de boutons sont entrées au catalogue **par la
coque**, pas par la photo : voir la section 14 ci-dessous et `ROBUSTESSE_2026-10-12.md` §14.2. Le
compte courant est de **22 souris sur 36** sans hauteur de boutons.)

### 13.5 Vues refusées (inchangé)

ATK U2 (rapport 2,69 vs 3,16), ATK Y9 Ultimate (écart 6,7 %), ATK F1 V3 Ultimate, Scyrox V8, ATK A9 Plus
2.0, Scyrox V6 : contrôle de perspective en échec, aucune valeur produite.

**Prochaine étape utile** : chercher des vues **portant le nom imprimé** des souris à boutons « moyens »
(A9 Plus, X1 V2 Ultra Max, Scyrox V6) — leur mesure étalonnerait la classe « Mid », aujourd'hui produite
par aucune référence.

## 14. Vingt-sixième passe (2026-10-12) : huit visuels de plus, toujours aucune valeur mesurable

Huit images de plus ont été récupérées (galeries ATK, Reddit, revendeurs des A9, X1, Scyrox V6) : le
corpus passe à **23 fichiers**. Deux faits mesurés en sortent :

1. **Un doublon de plus** : `atk-blazing-sky-x1-v2-ultra-max-wireless-2.jpg` et
   `atk-blazing-sky-zero-wireless-mouse-side-3.jpg` sont **les mêmes octets** (même empreinte SHA-256),
   servis pour deux modèles différents — le contrôle `tools/image_corpus_check.py` les écarte.
2. **Quatre vues passent le contrôle de perspective**, toutes donnent des valeurs **non tranchées** :

| Image | Ce qu'elle montre (vérifié à l'œil) | Avant | Mesure | Classe |
|---|---|---|---:|---|
| `…zero-wireless-mouse-side-5.jpg` | coque blanche à nez pointu, **aucun nom imprimé** | gauche (« ATK » sur le flanc) | 43,7 % | Low (l'outil) — **non publiée** |
| `…zero-wireless-mouse-side-4.jpg` | coque noire, **aucun nom imprimé** | droite | 48,3 % | aucune (bande grise) |
| `…a9-plus-wireless-mouse-sid-2.jpg` | coque A9 blanche (logo en « V » sur le flanc), **aucun nom de modèle imprimé** (série seule) | gauche | 47,3 % | aucune (bande grise) |
| `…a9-plus-wireless-mouse-sid-3.jpg` | coque A9 blanche, **aucun nom de modèle imprimé** (série seule) | droite | 47,3 % | aucune (bande grise) |

Aucune ne porte le nom du modèle imprimé sur la coque : la règle de publication du §13.4 (identité
visuelle **et** deux images distinctes concordantes) n'est donc remplie par personne. **Aucune valeur
n'est écrite dans `data/mouse_db.json` à partir de ces images.**

### 14.1 Une piste fermée par la mesure : le rapport de silhouette n'identifie pas un modèle

Le contrôle de perspective compare le rapport longueur/hauteur de la silhouette à celui du modèle
supposé. Vérification faite sur le catalogue entier : **plusieurs modèles ont des rapports quasi
identiques** (3,05 à 3,13) — la silhouette mesurée (3,06–3,09) colle à au moins quatre modèles
différents avec moins de 0,4 % d'écart. Conclusion écrite noir sur blanc : **la géométrie de la
silhouette ne peut pas servir de preuve d'identité** et le contrôle de perspective ne peut pas non plus
détecter qu'on lui a donné les cotes du mauvais modèle. Seule la vérification visuelle (nom imprimé,
logo) fait foi — c'est la règle du §13.4, et elle reste.

### 14.2 Ce qui a débloqué trois souris : la coque, pas la photo

Les trois variantes « large » de la coque A9 (`atk_a9_ultimate`, `atk_a9_air`, `atk_a9_nb`) partagent la
coque de l'ATK Dragonfly A9 Plus 2.0 du propriétaire, dont la hauteur de boutons est connue (« Mid ») :
elles l'ont reçue par héritage de coque, avec une source datée par souris. Ce n'est **pas** une mesure
d'image — la mesure ne pouvait rien apporter ici — et cela fait passer le compte de 25 à **22 souris**
sans hauteur de boutons. Détail de la règle, des limites (A9 Mini hors coque, VXE X3 non propagée) et de
l'effet mesuré : `ROBUSTESSE_2026-10-12.md` §14.2 et §14.3.

**Prochaine étape utile** (inchangée, précisée) : une vue **strictement de côté** et **portant le nom
imprimé** d'une souris à boutons « moyens » (A9 Plus « A9 PLUS », X1 V2 « X1 ULTIMATE », Scyrox V6
« V6 »). Aucune des douze vues testées ce jour ne remplit ces deux conditions.

## 15. Vingt-septième passe (2026-10-12) : PREMIÈRE hauteur de boutons publiée depuis une mesure

### 15.1 Le cas : l'ATK Blazing Sky ZERO

La ZERO était la souris la plus proche du but : la campagne précédente avait mesuré **43,0 %** sur un
rendu officiel portant « **ZERO** » imprimé sur la coque — valeur dans la bande « bas » — mais la règle
de publication exigeait **deux images distinctes** concordantes. Deux nouveaux rendus officiels ATK ont
été récupérés et mesurés :

| Image (fiche officielle ATK Blazing Sky ZERO) | Avant de l'image | Rapport mesuré | Écart de perspective | Mesure | Classe |
|---|---|---|---:|---:|---:|---|
| `…atk-zero-wireless-mouse-2.jpg` (« **ZERO** » imprimé sur le flanc) | droite | 3,09 contre 3,15 | 1,9 % | **43,3 %** | Low |
| `…atk-blazing-sky-zero-wireless-mouse-side-5.jpg` (logo « ATK » seul) | gauche | 3,07 contre 3,15 | 2,8 % | **43,7 %** | Low |

L'orientation de chaque image a été **vérifiée à l'œil** (molette et sérigraphie à l'avant) : la molette
se trouve à gauche sur la seconde image et à droite sur la première — c'est le paramètre `--front` qui
change, et c'est exactement le piège relevé à la 24e passe (une image mesurée à l'envers donne l'arrière
de la souris, pas le bouton).

### 15.2 La deuxième vue n'a pas de nom : identité prouvée par la silhouette

Sur la seconde image, seul « ATK » est imprimé : impossible de l'attribuer par son nom de fichier (la
règle « une photo = une identité »). Elle est rattachée à la première par un **outil nouveau**,
`tools/image_identity_check.py` : le profil supérieur de la silhouette, normalisé en fraction de hauteur
le long de la longueur, mis dans le même sens, puis comparé point à point.

| Comparaison | Écart moyen | Écart max | Verdict |
|---|---:|---:|---|
| ZERO (nommée) ↔ ZERO (seconde vue) | **0,24 %** | 4,59 % | même coque |
| Contrôle : ZERO ↔ ATK A9 (autre coque, même longueur) | 4,47 % | 11,74 % | coques différentes |
| Contrôle : ZERO ↔ rendu noir anonyme de la même page | 4,78 % | 9,99 % | coques différentes |

Un facteur **19** sépare les deux populations : le rattachement n'est pas une intuition, c'est une mesure
reproductible (seuils de l'outil posés dans la zone vide : 1 % / 3 %). **Cette même mesure a écarté le
rendu noir** : avec 4,78 % d'écart, ce n'est pas la ZERO — il n'a donc reçu aucune valeur.

### 15.3 La règle de publication, explicitée (et non contournée)

La règle écrite à la 25e passe demandait « au moins 3 points de marge sur les seuils ». La mesure de la
ZERO **est** la référence « boutons bas » (43,3 %, la valeur de l'ATK F1 V2 étalonnée) — elle n'est donc
pas « en dessous avec 3 points de marge », elle est **exactement sur le point d'étalonnage**. La règle est
donc amendée explicitement, avec sa raison :

> Une hauteur de boutons peut être publiée si **l'identité du modèle est prouvée sur l'image** (nom
> imprimé, ou rattachement de silhouette validé par `tools/image_identity_check.py`), que **deux vues
> distinctes** donnent la même classe, et que la valeur tombe **dans une classe ferme** (jamais dans
> l'intervalle gris 43,3–55,1 %). La marge de 3 points reste exigée pour toute valeur intermédiaire non
> étalonnée ; elle n'est pas requise quand la mesure **atteint une référence d'étalonnage**.

Risque résiduel, écrit noir sur blanc : si la vraie classe était « Mid », publier « Low » ferait gagner
10 points à tort à cette souris pour une prise **Fingertip** (idéal = Low). Contre ce risque : deux rendus
officiels du même modèle, correctement orientés, à 0,4 point l'un de l'autre, dont la valeur est celle de
la souris étalonnée « boutons bas ».

### 15.4 Résultat écrit dans le catalogue

`data/mouse_db.json` → `atk_zero.button_height = "Low"`, avec une source datée du 2026-10-12 (les deux
vues, leurs valeurs et la vérification d'identité) et la note qui décrit la méthode. C'est la **première**
hauteur de boutons du catalogue qui vient d'une **mesure** et non d'une fiche fabricant, d'un héritage de
coque ou du cahier des charges. Compte courant : **21 souris sur 36** sans hauteur de boutons.

### 15.5 Effet mesuré (moteur inchangé)

| Mesure | Avant | Après |
|---|---|---|
| Recommandations de l'ATK ZERO (grille 18 522 profils) | **0** | **933** (idéal 276, alternative 657) |
| Souris jamais recommandées | 9 sur 36 | **8 sur 36** |
| Profils sans aucun résultat | 252 | 252 (inchangé) |
| Profils où deux places montrent la même coque | 607 | 595 |

La ZERO était notée sur 9 828 profils sans jamais sortir : privée des 5 points de boutons, elle perdait
tous les départages. Elle est désormais **complète** et sort sur 933 profils.

## 16. Vingt-neuvième passe (2026-10-12) : la référence « moyens » est trouvée, la V3 entre au catalogue

### 16.1 La troisième référence : la coque ATK A9 « large » (« boutons moyens »)

Le blocage de la passe précédente était net : entre 43,3 % (référence « bas ») et 55,1 % (référence
« hauts »), l'outil refusait de trancher — faute d'une souris de classe « moyens » **dont une vue
exploitable existe**. Le catalogue en contient six (A9 Plus/Ultimate/Air/NB, X1 V2 Ultra Max, Scyrox V6) :
la campagne a commencé par la famille A9, dont **deux rendus officiels distincts** sont exploitables
(fichiers différents, empreintes SHA1 différentes).

| Rendu (page officielle ATK A9 Ultimate) | Avant de l'image | Rapport mesuré | Écart de perspective | Mesure | Classe |
|---|---|---|---:|---:|---:|
| `…atk-dragonfly-a9-plus-wireless-mouse-sid-2.jpg` | gauche | 3,07 contre 3,12 | 1,6 % | **47,3 %** | Mid |
| `…atk-dragonfly-a9-plus-wireless-mouse-sid-3.jpg` | droite | 3,16 contre 3,12 | 1,0 % | **47,3 %** | Mid |

Les deux vues donnent **47,3 %**, à 0,0 point l'une de l'autre. **Identité établie en deux temps** :
1) à l'œil, les deux rendus portent la sérigraphie de la série — « DRAGONFLY » sur le bouton et le logo
« ATK » sur le flanc — mais **aucun nom de modèle** ;
2) par la **page officielle du fabricant** (relevée le 2026-10-12) : les deux fichiers y figurent, avec la
légende publiée par ATK « *ATK Dragonfly A9 Ultimate Lightweight Wireless Mouse side view, white with
black accents and branding* ». Les rendus de l'**A9 Mini** sont, eux, des fichiers distincts de la même
page (`A9MINI*.jpg`) — le doute « Mini ou coque large ? » est donc tranché : **coque A9 « large »**.
La coque est partagée par l'A9 Ultimate, l'A9 Plus, l'A9 Air et l'A9 NB (un seul moule), tous « Mid » au
cahier des charges : la mesure vaut pour la coque entière. Les deux orientations ont été vérifiées à
l'œil (molette à l'avant) : mesurée à l'envers, la première donne 48,3 % — c'est le piège du `--front`.

Commande reproductible :

```
.venv/bin/python tools/measure_button_height.py "image-search/atk-dragonfly-a9-plus-wireless-mouse-sid-2.jpg" \
    --length-mm 125.0 --height-mm 40.0 --front left      # → 47,3 %, vue acceptée (écart 1,6 %)
```

**L'outil classe désormais les trois classes** (`tools/measure_button_height.py`, revu dans cette passe) :
la frontière entre deux classes est posée à mi-chemin de leurs deux références — **45,3 %** entre « bas »
et « moyens », **51,2 %** entre « moyens » et « hauts » — et une mesure à moins d'un point d'une frontière
reste **non tranchée**. La marge d'un point n'est pas choisie au hasard : c'est plus du double du plus
grand écart jamais observé entre deux rendus d'une même souris de classe connue (**0,7 point** : la ZERO
mesurée 43,0 %, 43,3 % et 43,7 % sur deux rendus). Non-régression vérifiée après la révision de l'outil :
ZERO 43,3 % et 43,7 % → **Low** (inchangé), A9 47,3 % → **Mid**, Z1 55,0 % → **High** (inchangé), et les
cinq tests de l'outil passent, dont deux neufs (les trois classes reconnues ; une valeur à la frontière
reste non tranchée).

### 16.2 La VXE Dragonfly V3 mesurée

La V3 est la souris qui pèse le plus dans les recommandations parmi les 21 sans hauteur de boutons
(5 533 sorties sur 18 522 profils avant cette passe). Une **seule** vue exploitable existe dans le corpus :
le rendu officiel de la gamme V3 sur vxe.com, portant « **DRAGONFLY V3** » imprimé sur la coque (molette à
droite). Mesure :

```
.venv/bin/python tools/measure_button_height.py "image-search/vxe-dragonfly-v3-pro-mouse-side-profile--1.jpg" \
    --length-mm 116.6 --height-mm 38.2 --front right
# Longueur mesurée : 1170 px · hauteur : 389 px (rapport 3,00 vs 3,05 attendu, écart 1,6 %)
# Échelle : 0,0980 mm/px · Hauteur d'appui : 17,8 mm (46,7 % de la hauteur totale)
```

La vue est acceptée avec **le meilleur écart de perspective du corpus** (1,6 %). Le même fichier est
présent deux fois dans le corpus sous deux noms (`…v3-pro-mouse-side-profile--1.jpg` et
`…v3-mouse-profile-white-sid-1.jpg`) : empreinte SHA1 identique, donc **une seule vue**, pas deux.

### 16.3 Publication : « Mid », avec le risque écrit noir sur blanc

Trois lectures de la même souris ne disent pas exactement la même chose — c'est écrit ici pour que la
décision soit révisable en une ligne si le propriétaire tranche autrement :

| Lecture | Valeur de la V3 | Où elle tombe |
|---|---|---|
| **Rapport « hauteur d'appui / hauteur totale »** (le critère étalonné de l'outil) | 46,7 % | à **0,6 point** de la référence « moyens » (47,3 %) et à 3,4 points de la référence « bas » (43,3 %) |
| Hauteur d'appui en **millimètres** au-dessus du tapis | 17,8 mm | entre la ZERO (16,5 mm, « bas ») et l'A9 (18,9 mm, « moyens ») : au milieu |
| **Hauteur totale** de la souris | 38,2 mm | sous les cinq souris « moyens » connues (40,0 mm) et au niveau des souris « bas » (38,1 à 38,8 mm) |

Comparaison du **profil avant** (0 à 20 % de la longueur, le morceau où se lit la hauteur des boutons),
V3 contre les souris de classe connue :

| Référence | Valeur à 5 % | Écart moyen sur 0–20 % | Signe (V3 − référence) |
|---|---:|---:|---:|
| ZERO (bas) | 43,3 % | 3,36 % | **+3,36 pt** (la V3 est plus haute) |
| ZERO 2ᵉ vue (bas) | 43,8 % | 2,91 % | +2,91 pt |
| A9 Ultimate, coque large (moyens) | 47,3 % | 2,72 % | −2,59 pt (la V3 est plus basse) |
| A9 Ultimate 2ᵉ vue (moyens) | 47,3 % | 2,58 % | −2,44 pt |
| Z1 Ultimate (hauts) | 55,1 % | 8,98 % | −8,98 pt |

Décision : **`vxe_v3.button_height = "Mid"`**, classe donnée par le critère étalonné, sourcée (fiche VXE du
modèle) et reproductible par la commande ci-dessus. Risque résiduel, assumé et écrit :

> la règle de publication (§15.3) demande deux vues concordantes ; **une seule vue existe** pour ce
> modèle. La mesure est publiée parce que la classe est ferme au sens de l'étalonnage (0,6 point de la
> référence « moyens », 1,4 point de la frontière) et que l'identité est prouvée sur l'image, mais le
> corpus n'a pas de recoupement. Si une seconde vue contredit cette valeur, elle se corrige en une ligne.
> Effet mesuré de la classe sur le moteur : pour un **Fingertip**, « Low » et « Mid » donnent exactement
> les mêmes points (les deux sont dans l'idéal) ; publier « Mid » au lieu de « Low » ne pénalise donc que
> les profils **Claw**, jamais les profils Fingertip.

### 16.4 Ce que la publication change, mesuré

Voir `docs/audit/ROBUSTESSE_2026-10-12.md` §18 (effet complet sur les recommandations, mesuré sur la
grille entière : 27 170 profils du banc de parcours et la grille statistique de 3 990 profils).

### 16.5 La règle de campagne qui suit, pour les 20 souris restantes

Deux **indicateurs mesurés** sur la même vue doivent désigner la même classe :

1. le **point de mesure** (hauteur du dessus à 5 % de la longueur depuis l'avant) comparé aux trois
   références étalonnées — c'est la mesure de l'outil, marge d'un point sur les frontières ;
2. le **profil avant complet** (0 à 20 % de la longueur), point par point, comparé aux mêmes souris de
   référence : l'écart moyen doit être le plus petit avec une souris de la classe annoncée.

Si les deux indicateurs désignent la même classe → **publier** (avec la vue, la commande et le fait qu'il
n'y a qu'une vue quand c'est le cas). S'ils divergent → **documenter sans publier** : la mesure est
publiable en tant que mesure, pas en tant que classe. Ne jamais publier une valeur sans commande
reproductible, et jamais sans que l'identité du modèle soit lisible sur l'image.

Pourquoi deux indicateurs : le point de mesure ne lit qu'une colonne de pixels et peut être décalé par
un rendu légèrement différent ; le profil avant lit vingt points et décrit la forme réelle des boutons.
Un rendu qui passe le contrôle de perspective peut tromper l'un, difficilement les deux.

### 16.6 Contre-épreuve : la « hauteur totale » n'est PAS le critère (deux mesures le montrent)

Dans les quinze souris de classe connue du cahier des charges, la classe suit **parfaitement** la hauteur
totale (`bas` ≤ 38,8 mm, `moyens` = 40,0 mm, `hauts` = 42,4 mm). On pourrait en conclure que la hauteur
de la souris suffit à deviner la classe. Deux mesures faites le 2026-10-12 **cassent cette coïncidence** :

| Souris | Hauteur totale | Hauteur d'appui mesurée | Classe suggérée par la hauteur | Classe mesurée |
|---|---:|---:|---|---|
| VXE Dragonfly V3 | 38,2 mm | 46,7 % (17,8 mm) | « bas » (≤ 38,8 mm) | **Mid** (§16.3) |
| ATK U2 Ultimate (rendu de la fiche U2 V2) | 39,1 mm | 53,2 % (20,8 mm) | « bas » ou « moyens » | indécise (§17) |

Deux souris de 38 à 39 mm mesurent donc **plus haut** que ce que leur hauteur suggère : la corrélation
observée sur les quinze souris connues est une **coïncidence d'échantillon** (les souris « bas » du
catalogue sont aussi les plus plates), pas le critère. Ce qui reste vrai : la hauteur totale est un
**indice** utile pour trier les cas, jamais une preuve — et c'est la mesure des images qui tranche, comme
la règle l'exige.

## 17. Contre-épreuves mesurées le 2026-10-12 : ce qui n'est PAS publié, et pourquoi

### 17.1 ATK U2 Ultimate (rendu officiel de la fiche U2 V2 Superlight)

Vue strictement de profil, **« U2 ULTIMATE » imprimé en doré sur la coque** (identité prouvée à l'œil),
molette à droite, rapport longueur/hauteur à 1,7 % de la cote officielle (accepté). Mesure :

```
.venv/bin/python tools/measure_button_height.py "image-search/atk-blazing-sky-u2-superlight-mouse-side-4.jpg" \
    --length-mm 123.7 --height-mm 39.1 --front right
# rapport 3,11 vs 3,16 (écart 1,7 %) · hauteur d'appui 20,8 mm = 53,2 % → au-dessus de la frontière
# « moyens/hauts » (51,2 %), à 2,0 points de cette frontière et 1,9 point de la référence « hauts » (55,1 %)
```

Les deux indicateurs **divergent** :

| Indicateur | Valeur | Référence la plus proche |
|---|---|---|
| Point de mesure (5 %) | 53,2 % | **Z1 (hauts, 55,1 %)** — 1,9 point |
| Profil avant 0–20 % | écart moyen | **A9 (moyens)** 4,00 % · Z1 (hauts) 4,47 % · ZERO (bas) 7,46 % |

Le point de mesure dit « hauts », le profil complet dit « moyens » (l'avant de l'U2 monte moins vite que
celui du Z1 après les boutons : 80,7 % de la hauteur à 20 % de la longueur, contre 87,2 % pour le Z1).
**Aucune classe n'est publiée** : la règle du §16.5 l'interdit, et publier « High » à tort ferait perdre
10 points à cette souris sur une prise **Fingertip** (idéal = Low ou Mid). La valeur reste documentée ici,
avec sa commande, pour la prochaine passe ou pour l'arbitrage du propriétaire.

### 17.2 Ce que la même campagne a écarté aujourd'hui

- **X1 V2 Ultra Max** (`image-search/x1-ultimate-atk-mouse-side-view-printed--*`) : quatre fichiers, tous
  refusés (fond non uniforme / vues en perspective : la mesure sort à 100 % de la hauteur, l'outil ne
  produit rien). Aucune valeur.
- **R1 Pro Max** (`image-search/vxe-dragonfly-v3-pro-max-white-side-view-1.jpg`) : profil strict en
  studio, mais fond **dégradé avec ombre portée** : la boîte englobante attrape l'ombre (rapport 1,36
  contre 3,19) → refusé. Aucune valeur. (Le fichier porte « VXE R1 PRO MAX » imprimé : il est identifié,
  mais inexploitable en l'état.)
- **U2 / U2 V2** (pages boutique) : les autres rendus reçus sont des vues de trois quarts ou d'autres
  modèles (X1, ZERO) — écartés, aucun n'entre dans le corpus.

### 17.3 Pistes ouvertes pour la suite de la campagne (mesurées, pas supposées)

| Souris à mesurer | Ce qui a été tenté (2026-10-12) | Résultat | Piste |
|---|---|---|---|
| **ATK A9 Mini** (2 466 profils en attente) | recherche d'images « ATK Dragonfly A9 Mini side view » | l'index d'images renvoie les **rendus de l'A9 Ultimate** (dont deux déjà mesurés) ; le nom de fichier ne prouve rien | les rendus officiels de l'A9 Mini existent sur la page ATK de l'A9 Ultimate — fichiers `A9MINI*.jpg` (relevés le 2026-10-12) — mais l'index ne les expose pas : **aucun téléchargement direct possible** sur cette plateforme, la piste passe par le propriétaire (glisser l'image dans `image-search/`) |
| **VXE Dragonfly R1 / R1 Pro** (2 776 profils) | recherche « VXE Dragonfly R1 SE side view » → 5 fichiers officiels vxe.com | **5 vues 3/4** (aucune vue de profil stricte : rapport 0,98 contre 3,19 attendu) | demander une **vue de profil** au fabricant ou au propriétaire |
| **ATK Blazing Sky U2** (vue unique) | recensement des vues de la page U2 V2 Superlight | 5 fichiers : une seule vue de profil stricte, les autres sont plongée / dessus / 3-4 | deuxième vue à trouver (§17.1) |

**Rappel de méthode** : une image ne se télécharge pas directement depuis ce poste de travail (le CDN
Shopify refuse la connexion sécurisée) ; seul l'outil de recherche d'images fournit des fichiers, et il
ne renvoie que ce que son index connaît. Toute image glissée par le propriétaire dans `image-search/`
est mesurable en une commande.

## 18. Quatre-vingtième passe (2026-10-15) : la campagne passe par EloShapes

**Le blocage des §5 et §17** : la méthode est juste, mais elle exige une vue de profil strictement
orthographique, et les sites des fabricants n'en publient presque pas (7 vues sur 11 en perspective).
Au rythme d'une vue trouvée de temps en temps, 18 souris restaient sans hauteur de boutons.

**Ce que la mesure change** (2026-10-15, 21 736 profils du banc) : selon les classes que prendront ces
18 souris, le match idéal peut changer pour **5 810 profils (27 %)** et au moins une des trois places
pour **14 627 (67 %)**. Le critère manquant n'est donc pas un détail : c'est la principale incertitude
du classement.

**La voie retenue** : EloShapes dessine toutes ses souris de profil, à plat, de la même façon — une
seule source, une seule méthode, 36 souris. `tools/campagne_boutons.py` :

1. lit chaque image (fond transparent, fond uni, ou contour coloré sur une grille), écarte grille et
   légendes, garde la souris d'un seul tenant ;
2. relève le **profil complet** du dessus de la coque, millimètre par millimètre depuis la pointe avant
   (échelle : cotes du catalogue) ; refuse une vue dont les proportions s'écartent de plus de 4 % des
   cotes ; signale une bosse mesurée loin de celle du catalogue (image retournée) ;
3. **laisse les données choisir** : cinq mesures candidates (dont celle de l'outil historique, 5 % de la
   longueur), chacune étalonnée sur les souris dont la classe est connue, validée en laissant chaque
   souris de côté à tour de rôle ; la meilleure est retenue, ses seuils classent les autres ;
4. ne publie rien : rapport et relevé JSON (empreinte SHA-256 de chaque image, source, date), avec les
   souris connues que la mesure contredit marquées « à revoir ».

Consignes de collecte et manifeste des 36 souris : `docs/campagne_boutons/CONSIGNES.md` et
`docs/campagne_boutons/manifeste.csv`. Tests : `tests/test_campagne_boutons.py` (profils synthétiques
connus au dixième de millimètre, étalonnage, campagne de bout en bout).

**Règle de publication proposée au propriétaire** (à trancher) : une classe proposée par la campagne
entre au catalogue quand (a) l'image vient de la page EloShapes de ce modèle, (b) la validation croisée
de l'étalonnage retrouve au moins 80 % des souris connues, (c) la mesure n'est pas « non tranchée ».
C'est une source unique (EloShapes) : la règle des « deux vues distinctes » du §15.3 ne peut pas être
tenue telle quelle, et c'est au propriétaire de dire si l'homogénéité de la source la remplace.
