# Reverse engineering de l'outil Oblivity (dossier `Reverse/`, 2026-10-11)

Les 10 sorties fournies (3 prises × gabarits, thénar variable) ont été comparées ligne à ligne à notre
moteur. Conclusion courte : **notre moteur reproduit leur outil à l'identique sur les longueurs et les
largeurs** (écart 0,0 mm sur les 9 profils testés), les règles de bosse et de boutons concordent, et la
seule vraie divergence de fond est le **rôle du thénar** (eux : une contrainte de forme d'arrière ;
nous : rien avant le 2026-10-11).

## 1. Longueurs et largeurs : concordance exacte

Leur outil affiche « Optimal Mouse Length » (du talon à la pointe) et « Optimal Mouse Width »
(**souris retournée, à la position du capteur**).

| Profil (main) | Leur longueur | Notre longueur | Leur largeur | Notre largeur |
|---|---|---|---|---|
| Palm 150 × 90 | 110,9 – 115,9 mm | 110,9 – 115,9 mm | 55,6 – 59,6 mm | 55,6 – 59,6 mm |
| Palm 180 × 90 | 118,8 – 123,8 mm | 118,8 – 123,8 mm | 55,6 – 59,6 mm | 55,6 – 59,6 mm |
| Palm 210 × 90 | 126,7 – 131,7 mm | 126,7 – 131,7 mm | 55,6 – 59,6 mm | 55,6 – 59,6 mm |
| Claw 150 × 75 | 110,9 – 115,9 mm | 110,9 – 115,9 mm | 54,4 – 58,4 mm | 54,4 – 58,4 mm |
| Claw 180 × 90 | 118,8 – 123,8 mm | 118,8 – 123,8 mm | 55,6 – 59,6 mm | 55,6 – 59,6 mm |
| Claw 210 × 110 | 126,7 – 131,7 mm | 126,7 – 131,7 mm | 57,2 – 61,2 mm | 57,2 – 61,2 mm |
| Fingertip 150 × 75 | max. 115,9 mm | max. 115,9 mm | 53,3 – 57,2 mm | 53,3 – 57,2 mm |
| Fingertip 180 × 90 | max. 123,8 mm | max. 123,8 mm | 54,5 – 58,4 mm | 54,5 – 58,4 mm |
| Fingertip 210 × 110 | max. 131,7 mm | max. 131,7 mm | 56,1 – 60,0 mm | 56,1 – 60,0 mm |

Trois enseignements :

1. **Écart nul** partout : nos équations (`71,4 + 0,2633 × main`, +5 mm ; largeur `48,4 + 0,08 × main`
   en Palm/Claw, `47,3` en Fingertip) sont *les leurs*.
2. La longueur **ne dépend pas de la prise** (sauf Fingertip, sans minimum) et la largeur non plus —
   seule la base change entre Fingertip et les deux autres.
3. Ils précisent la méthode de mesure de largeur : **souris retournée, au niveau du capteur**.
   C'est exactement ce que notre outil `tools/measure_grip_width.py` permet de faire sur une image,
   et ce que la règle provisoire « coque − 3 mm » approxime.

## 2. Règles de forme : ce que dit leur outil

| Critère | Palm | Claw | Fingertip |
|---|---|---|---|
| Bosse | « Mid-to-Front » | « Mid-to-Back » (+ variantes : Relaxed Claw → bosse arrière marquée ; Aggressive Claw → bosse centrale ; Pincer Claw → bosse arrière + flancs **peu courbés**) | **non mentionnée** |
| Boutons | « Elevated » (hauts) | « Low » (bas) | « Mid-to-Low » (jamais hauts) |
| Forme | ergonomique ou symétrique, ergonomique conseillée | **symétrique** généralement supérieure | — |
| Thénar | posé, puis : arrière étroit en pilule si Petite **ou** Moyenne ; **rien** si Grande | idem | **question non posée** |

Notre moteur applique déjà : `HUMP_IDEAL` Palm {Front, Mid} / Claw {Mid, Rear} / Fingertip (ignorée),
`BUTTON_IDEAL` Palm {High} / Claw {Low, Mid} / Fingertip {Low}. Les deux premières lignes sont
identiques ; les écarts sont traités au §4.

## 3. Le thénar : leur logique, la tienne, la nôtre

**Leur outil ne donne aucun point au thénar.** Il s'en sert pour trancher **une seule chose : la forme
de l'arrière**, et il le fait par un texte, pas par un score :

- Thénar **Petite** : « Since your thenar muscles are on the smaller side, choose a mouse with a
  **narrow, pill-shaped rear**. »
- Thénar **Moyenne** : même recommandation, formulée pour une taille « average ».
- Thénar **Grande** : **aucune contrainte d'arrière** n'est affichée (la section disparaît).
- **Fingertip** : la question du thénar n'est **pas posée** — ce qui valide la correction que tu
  m'avais demandée (pas d'étape thénar en Fingertip).

Ton intuition (« petit thénar + arrière large = gêne ; grand thénar + arrière large = soutien ») va
donc **dans le bon sens**, et leur outil la confirme sur la moitié « petit thénar ». En revanche, leur
outil ne récompense jamais un arrière large : il se contente de ne plus l'interdire. C'est cohérent
avec la vidéo : un éventail arrière « couvre le thénar » et **réduit la mobilité** — il y a un
compromis, pas un bonus universel.

### Ce que j'ai implémenté (borné, réversible)

Dans `utils/matcher.py` (constante unique `THENAR_WIDTH_ADJUSTMENT`, tout est centralisé) :

- l'ajustement ne s'applique **que** si la souris a une **bosse arrière marquée** (`hump_position`
  = « Rear ») **et** que la prise est Palm ou Claw (jamais Fingertip) ;
- **Petite : −2 · Moyenne : 0 · Grande : +2**, appliqué au **sous-score de largeur (0–10)**, donc borné
  à l'intérieur de ce sous-score : impossible de dépasser les 40 points ou de descendre sous zéro ;
- sans thénar renseigné (ou thénar moyenne), **le barème historique est strictement inchangé** :
  la non-régression 180 × 90 Palm (V6 30, Z1 30, A9 25, X1 20) est préservée ;
- l'effet est **visible** : « arrière marqué qui soutient votre thénar » ou « arrière large à
  contre-emploi avec un thénar petite » dans le résumé, et la note de l'embed 2 pour un thénar petite.

Pourquoi ±2 et pas ±3 : leur outil n'ajoute aucun point, donc chaque point ajouté par nous est déjà
une hypothèse. ±2 reste du même ordre que la tolérance « proche » (5 → 0 pts sur la largeur) et ne peut
pas, à lui seul, faire gagner ou perdre un rang à une souris mal dimensionnée. La version « conforme
à leur outil » (0 point, conseil d'arrière uniquement) s'obtient en mettant les trois valeurs à 0 —
c'est le repli si tu trouves l'ajustement trop interventionniste.

### Ce qui manque pour aller plus loin

La seule façon d'objectiver « arrière large » est de **mesurer** : largeur à 60–90 % de la longueur,
rapportée à la largeur maximale. On peut alors remplacer « bosse = Rear » par un critère chiffré
(ex. largeur à 90 % ≥ 0,90 × largeur maximale) et donner à l'ajustement une base mesurable — c'est
précisément ce que les images EloShapes + `tools/measure_grip_width.py` permettent de faire.

## 4. Deux écarts assumés (non corrigés sans ton accord)

| Écart | Leur outil | Nous | Impact chiffré |
|---|---|---|---|
| Hauteur des boutons en **Claw** | « Low » seulement | Low **ou Mid** acceptés | 1 souris classable concernée (Scyrox V6, 30 → 25 en Claw 150 × 75) |
| Hauteur des boutons en **Fingertip** | « Mid-to-Low » | Low seulement | 2 souris (Scyrox V6 30 → 35 ; A9 Plus 2.0 20 → 25 en Fingertip 200 × 100) |

Ces deux alignements sont **prêts** (une ligne chacun dans `BUTTON_IDEAL`) mais non appliqués : ils
changeraient des scores déjà validés par tes tests de non-régression et par la matrice de profils.
Dis-moi si tu veux que je les applique — c'est un choix, pas une évidence.

## 5. Ce que le reverse engineering confirme aussi

- **Pas de minimum de longueur en Fingertip** (leur « max. 123,8 mm ») : nous faisons pareil.
- **Fingertip : la bosse n'est pas un critère** : pareil.
- **Leur méthode de largeur** (au capteur, souris retournée) valide notre correctif provisoire
  « coque − 3 mm » comme estimation, et notre outil de mesure d'image comme méthode de vérification.
- Leur outil **ne note ni le poids, ni le capteur, ni le polling** : comme nous (voir
  `docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md`, §5, I3).
