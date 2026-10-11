# Mesure de la largeur de prise — campagne du 2026-10-11

Objet : répondre à la demande « mesure effectivement les souris, fais tout bien, estime tout ».
L'utilisateur proposait de mesurer sur les images (EloShapes) avec `imageonline.io/measure-image` ;
ici la mesure est faite **en local**, sans envoi de données, sur le même principe que la méthode Oblivity
(critère utile = largeur **au niveau du capteur**, voir `tools/measure_grip_width.py`).

## 1. Méthode reproductible

1. vues de dessus nettes (fond clair, souris entière) récupérées dans `image-search/` (gitignoré) ;
2. silhouette extraite par `tools/measure_grip_width.py` → `silhouette_rows()` ;
3. échelle = `length_mm` publiée dans `data/mouse_db.json` ÷ hauteur de la silhouette en pixels ;
4. filtres qualité **durs** : `|ratio − W/L| ≤ 0,04` **et** `|largeur_max − W publiée| ≤ 1,2 mm`
   (élimine vues de biais, de 3/4, planches produits multiples) ;
5. attribution image → souris : titre + URL source de l'image, recoupée par hachage MD5 (§3) ;
6. relevé : largeur maximale + profil tous les 10 % de la hauteur de silhouette.

Contrôle de reproductibilité : deux photos indépendantes donnent la même largeur à ±0,1–0,7 mm
(Scyrox V8, F1 V2, X1 V2, ZÉRO, Fierce X, Y9).

## 2. Mesures retenues (11 souris / 11 photos)

| souris (id base) | photo retenue | largeur max | Δ vs fiche | profil 10 → 90 % (mm) |
|---|---|---|---|---|
| `scyrox_v8` | `scyrox-v8-wireless-mouse-top-view-white--3.jpg` | 62.33 | -0.67 | 54.64 / 59.77 / 60.28 / 61.57 / 62.08 / 62.33 / 62.33 / 59.77 / 47.46 |
| `scyrox_v6` | `scyrox-v6-wireless-mouse-top-view-white--3.jpg` | 61.49 | +0.49 | 50.52 / 57.2 / 58.94 / 57.83 / 56.24 / 58.31 / 60.85 / 59.1 / 47.66 |
| `atk_f1_v2` | `atk-blazing-sky-f1-v2-wireless-mouse-top-2.jpg` | 62.35 | -0.05 | 56.75 / 59.55 / 59.55 / 59.88 / 59.21 / 58.99 / 62.12 / 60.78 / 49.92 |
| `atk_x1_ultra_max` | `atk-blazing-sky-x1-v2-wireless-mouse-top-1.jpg` | 63.97 | -0.03 | 61.87 / 62.18 / 62.18 / 61.13 / 61.55 / 62.18 / 63.87 / 62.18 / 51.35 |
| `atk_z1_ultra` | `atk-blazing-sky-z1-v2-wireless-mouse-top-2.jpg` | 66.05 | -0.75 | 60.74 / 62.78 / 61.66 / 62.78 / 63.39 / 64.52 / 65.95 / 63.6 / 51.45 |
| `atk_zero` | `atk-blazing-sky-zero-wireless-mouse-top--3.jpg` | 62.81 | -0.39 | 56.37 / 60.25 / 60.46 / 61.69 / 61.99 / 60.87 / 62.71 / 60.77 / 50.54 |
| `atk_ghost_ultimate` | `atk-blazing-sky-ghost-carbon-fiber-wirel-3.jpg` | 61.26 | -0.04 | 59.23 / 59.03 / 58.32 / 59.03 / 59.44 / 60.04 / 61.16 / 59.13 / 49.21 |
| `atk_y9_ultimate` | `atk-dragonfly-y9-wireless-mouse-top-view-3.jpg` | 67.26 | -0.24 | 54.81 / 60.31 / 60.31 / 60.0 / 60.2 / 64.15 / 67.16 / 63.73 / 50.76 |
| `atk_fierce_x` | `atk-fierce-x-magnesium-wireless-mouse-to-1.jpg` | 61.15 | +0.16 | 33.14 / 60.47 / 59.27 / 58.93 / 58.42 / 59.1 / 60.98 / 59.27 / 48.34 |
| `atk_u2_v2_ultimate` | `atk-blazing-sky-u2-v2-wireless-mouse-top-1.jpg` | 64.55 | -0.05 | 52.82 / 59.66 / 59.86 / 59.56 / 58.43 / 59.15 / 63.53 / 63.53 / 51.6 |
| `vxe_mad_r` | `vxe-mad-r-wireless-mouse-top-view-white--2.jpg` | 63.26 | +0.16 | 55.96 / 60.11 / 60.62 / 61.75 / 61.62 / 61.62 / 63.26 / 61.24 / 50.56 |

Profil exprimé en **% de la hauteur de silhouette depuis le haut de l'image** (orientation avant/arrière non vérifiée, §4).
Les extrémités (0–10 % et 90–100 %) sont polluées par les ombres : ne pas les lire.

## 3. Doublons et pièges détectés (MD5)

- `45ba7159…` : `…f1-v3…whi-1.jpg` = `…x1-v2…top-1.jpg` = `…z1-v2…top-3.jpg` → **une seule photo** (X1 V2) ;
  les fichiers `…f1-v3…whi-*` viennent d'une recherche « F1 V3 » dont les résultats étaient d'autres modèles.
- `b0122183…` = ZÉRO ; `9127cf17…` = F1 V2 (`whi-2`, `whi-3`).
- Conséquence : **`atk_f1_ultimate` n'est pas mesuré** ; la valeur « 61,82 » du lot 2 n'est **pas reproduite** ⇒ à refaire
  avec une vraie vue de dessus de F1 V3.
- `atk_u2` et `atk_u2_v2_ultimate` ont les mêmes cotes en base (123,7 × 64,6 × 39,1) : une photo « U2 V2 » (64,55) ne
  permet pas de distinguer les deux ⇒ à traiter comme une même coque tant que non confirmé.

## 4. Limites

- ombres/anti-aliasing aux deux extrémités : les coupes 0–10 % et 90–100 % ne sont pas exploitables ;
- **orientation de chaque photo non vérifiée** visuellement → profil donné depuis le haut de l'image ;
- 14 souris sur 26 encore sans mesure exploitable (§6) ;
- **aucune valeur inscrite en base à ce stade**.

## 5. Champ cible et branchement (déjà prêt)

`grip_width_mm` est le champ prévu pour une largeur **mesurée** : `utils/catalog.py` le lit déjà et
`utils/matcher.py` → `grip_width_for_scoring()` l'utilise **en priorité** (source `measured`) avant l'estimation
`width_max_mm − 3 mm`. Il suffit donc d'ajouter le champ (+ source datée) à `data/mouse_db.json`,
sans modification de code. Définition à figer avant inscription : largeur **au capteur** ⇒ relever la position
du capteur par souris (vue de dessous) et choisir la coupe correspondante dans le profil.

## 6. Reste à mesurer (14) et lacunes de la base repérées

- sans mesure exploitable : `atk_f1_ultimate`, `atk_a9_plus`, `atk_a9_nb`, `atk_a9_ultimate`, `atk_a9_air`,
  `atk_a9_mini`, `atk_phantom_ultimate`, `atk_ghost_extreme`, `atk_duckbill`, `atk_u2_mini`, `atk_u2_v2_mini`,
  `vxe_v3`, `vxe_r1`, `vxe_x3` ;
- lacunes constatées au passage : `length_mm` nul (`atk_duckbill`) ; `height_mm` absent (`scyrox_v8`, `scyrox_v6`) ;
  `hump_position` absent (`atk_a9_mini`, `vxe_x3`) ; `price_eur` absent (`atk_a9_mini`, `vxe_mad_r`) ;
  `button_height` « Inconnu » sur 19 souris ; aucun `*_grip_fit` documenté sur 20/26.

Données brutes : `docs/audit/mesures_largeur_2026-10-11.json` (profil complet 10–90 %, MD5, fiche utilisée).

## 7. Mise à jour 2026-10-11 (soir) — doublons tranchés par empreinte MD5

Les fichiers posant problème ont été comparés octet par octet : trois photos circulaient sous
plusieurs noms, ce qui explique les attributions douteuses du lot 2.

| Empreinte MD5 (préfixe) | Fichiers identiques | Souris retenue (largeur max mesurée) |
| --- | --- | --- |
| `45ba7159…` | `f1-v3-mouse-top-view-whi-1` = `z1-v2-wireless-mouse-top-3` = `x1-v2-wireless-mouse-top-1` | **X1 V2** (63,97 mm ; écart −2,8 mm avec la Z1 V2 ⇒ rejeté) |
| `b0122183…` | `f1-v3-mouse-top-view-whi-2` = `zero-wireless-mouse-top--3` | **ZERO** (62,81 mm ; écart −0,39 mm) |
| `9127cf17…` | `f1-v3-mouse-top-view-whi-3` = `f1-v2-wireless-mouse-top-2` | **F1 V2** (62,35 mm ; écart −0,05 mm) |

Conséquences :

- **`atk_f1_ultimate` reste non mesuré** : aucune photo propre à la F1 V3 n'existe dans le lot
  (les fichiers `…whi-*` sont des doublons de X1 V2 / ZERO / F1 V2). La coque F1 V2/V3 est la même
  (118,2 × 62,4 × 38,8 mm), donc la largeur de la F1 V3 sera identique — mais la valeur ne sera
  inscrite qu'avec une photo de F1 V3 ;
- **l'orientation ne change pas la largeur maximale** : la valeur retenue par souris est le maximum
  du profil, indépendant du sens nez/arrière. Seul le profil 10→90 % (et le choix de la coupe
  « capteur ») dépend de l'orientation, d'où l'examen visuel encore en attente ;
- l'audit JSON `docs/audit/mesures_largeur_2026-10-11.json` reste la source des valeurs (11 souris
  + la coque U2/U2 V2, mesures non inscrites en base à ce stade).
