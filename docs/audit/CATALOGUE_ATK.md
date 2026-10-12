# Catalogue ATK vérifié (livrable B)

Date de vérification : **2026-10-10**. Données : `data/mouse_db.json` (schéma v2).

> **Ce catalogue n'est pas exhaustif.** La collection ATK (store) listait 23 produits, mais la correspondance produit ↔ statut
> de disponibilité n'a pas été extraite, et seule la première page de la collection a été lue. Plusieurs variantes
> (Z1 originale, X1 original, F1 Pro Max, A9 SE / Pro / Ultra, Ghost Extreme sur sa propre page, Blazing Sky Phantom sur le store)
> n'ont pas été vérifiées séparément ; voir §3.

## 1. Conventions

- **Dimensions** : L × l × H en mm, tels que publiés ; `—` = non trouvé.
- **Statut dimensions** : `verified` = ≥ 2 sources concordantes (écart ≤ 0.5 mm) ; `single_source` = une seule source ; `conflicting` = sources en désaccord > 0.5 mm.
- **Prix** : le store ATK n'affiche que des USD (non convertis). Depuis le 2026-10-11, des prix **EUR** sont relevés
  chez des revendeurs français et écrits dans la base quand la variante correspond exactement
  (voir `docs/RECHERCHE_PRIX_EUR_2026-10-11.md`) ; statut `verified` = prix daté + URL en source.
- **Disponibilité** : non vérifiée par modèle.
- **Compatibilité grip / boutons** : non renseignée pour les nouvelles variantes (`Inconnu`). Les mentions marketing « claw grip » ou « palm grip » de l'éditeur ne sont **pas** assimilées à une compatibilité.
- **Relevance** : résultat du moteur. P = Palm 180×90, C = Claw 150×75, F = Fingertip 200×100 (voir `matrice_profils.md`).

## 2. Tableau

| Référence | Variante | Forme | Dimensions L×l×H (mm) | Poids | Specs clés (documentées) | Prix EUR vérifié | Disponibilité | Sources | Statut dimensions | Pertinence profils (moteur) |
|---|---|---|---|---|---|---|---|---|---|---|
| ATK F1 | F1 V3 Ultimate | Compacte, symétrique, bosse « Mid » (cahier) / « Back-minimal » (EloShapes) | 118.2 × 62.4 × 38.8 | — (39 g sur V2, non transposé) | 8000 Hz (V2) | — | non vérifiée | ATK blog F1 ; EloShapes (F1 V2) | verified | P exclue (grip Palm « Faible ») · C 30 · F 35 |
| ATK X1 | X1 V2 Ultra Max | Large, bosse « Mid » (cahier) / « Back-minimal » (EloShapes) | 127.0 × 64.0 × 40.0 | 55 g | 8000 Hz ; capteur **en conflit** (PAW3395 Ultra vs PAW3950/3955) | — | non vérifiée | EloShapes ; ATK collection X1 | verified | P 20 · C exclue (longueur 11.1 mm) · F exclue (grip Fingertip « Faible ») |
| ATK Z1 | Z1 V2 Ultra (« Blazing Sky Z1 V2 ») | Asymétrique ergonomique | 122.5 × 66.8 × 42.4 | 54 g | 8000 Hz | — | non vérifiée | ATK collection Z1 ; ATK blog Z1 ; Meckeys | verified | **P 30** (écart largeur 4.2 mm → 0 pt) · C exclue (largeur 5.4 mm) · F exclue (grip « Faible ») |
| ATK A9 | A9 Plus 2.0 | « Patate » universelle, symétrique | 125.0 × 63.5 (cahier) / 64.0 (EloShapes) × 40.0 | 57 g | 1000 Hz (EloShapes) | 45 € (cahier, non daté) | non vérifiée | EloShapes compare A9 / A9 Plus | verified (écart 0.5 mm) | **P 25** · C exclue (longueur 9.1 mm) · F 20 |
| ATK Phantom | Phantom Ultimate | Moyenne, symétrique, carbone | 119.7 × 62.5 × 37.3 | 44 g | PAW3955 Master, 8000 Hz | — | non vérifiée | EloShapes | single_source | P / C / F : à vérifier (grip et boutons non vérifiés) |
| ATK GHOST | GHOST Ultimate | Moyenne, bosse arrière | 121.0 × 61.3 × 38.0 | 48 g | PAW3950 Ultra, 8000 Hz | — | non vérifiée | EloShapes | single_source | à vérifier (P, C, F) |
| ATK GHOST | GHOST Extreme | Même coque que GHOST Ultimate (EloShapes) | 121.0 × 61.3 × 38.0 | 48 g | capteur non vérifié | — | non vérifiée | EloShapes (comparaison) | single_source | à vérifier |
| ATK Y9 | Y9 Ultimate | Grande, ergonomique, non symétrique | 125.6 × 67.5 × 43.3 | 55 g (FPSTools : 58 g) | PAW3950 Ultra ; polling **en conflit** (8000 vs 1000 Hz) | — | non vérifiée | EloShapes ; MaxGaming ; FPSTools | verified | C exclue (longueur 9.7 mm) · P à vérifier (écart largeur 4.9 mm, grip inconnu) · F exclue (écart largeur 5.3 mm) |
| ATK Fierce | Fierce X | Moyenne, symétrique, magnésium | 119.57 × 60.99 × 36.26 | 42 g | PAW3950 Ultra, 8000 Hz | — | non vérifiée | ATK Store ; EloShapes ; MouseMetric | verified | à vérifier (grip non vérifié ; marketing « claw » non assimilé) |
| ATK U2 | U2 V2 Ultimate | Moyenne, symétrique, bosse arrière | 123.7 × 64.6 × 39.1 | 45 g | PAW3950 Ultra, 8000 Hz | — | non vérifiée | EloShapes ; notice ATK ; ATK collection U2 | verified | à vérifier |
| ATK U2 | U2 V2 Mini | Petite à moyenne | 119.5 × 63.0 × 38.5 | 39 g | 8000 Hz ; capteur non vérifié | — | non vérifiée | EloShapes ; notice ATK ; ATK collection U2 | verified | à vérifier |
| ATK | ZERO | Moyenne, symétrique | 120.1 × 63.2 × 38.1 | 39 g | 8000 Hz | — | non vérifiée | EloShapes | single_source | à vérifier |
| ATK | Duckbill | Forme canard, bosse arrière | **longueur en conflit** (118.0 vs 117) × 62.5 × 37.4 | 46 g (≈49 g blog) | PAW3950 Ultra, 8000 Hz | — | non vérifiée | EloShapes ; blog ATK Duck Bill | conflicting | à vérifier (longueur non retenue) |
| ATK A9 | A9 Ultimate | Grande, symétrique | 125.0 × 64.0 (EloShapes) / 63.5 (ATK) × 40.0 | 53 g (ATK : 55 ± 3 g) | PAW3950 Ultra, 8000 Hz | — | non vérifiée | EloShapes ; ATK Store (Dragonfly A9 Ultimate) | verified (écart 0.5 mm) | à vérifier |
| ATK A9 | A9 Air | Même taille que A9 Ultimate (EloShapes) | 125.0 × 64.0 × 40.0 | 47 g | 8000 Hz | — | non vérifiée | EloShapes (comparaison) | single_source | à vérifier |
| ATK A9 | A9 Mini | Petite | 118.4 × 61.2 × 38.6 | 39 ± 3 g | PAW3955, 8 000 Hz | **59,95 €** | **vérifiée** (ATK + EloShapes) | ATK Store ; EloShapes | verified | **classable** depuis le 2026-10-12 (bosse « Center » → Mid) — hauteur des boutons non documentée |

Dans le tableau, « à vérifier » signifie que la souris est en attente (`pending`) : le score partiel est affiché mais jamais classé.

## 3. Variantes non ajoutées (et pourquoi)

| Variante | Raison |
|---|---|
| ATK Z1 original (« Blazing Sky Z1 ») | Dimensions ATK (119.57 × 60.99 × 36.26 mm) **identiques** à la Fierce X : donnée suspecte, non ajoutée. Les dimensions 122.5 × 66.8 × 42.4 mm sont celles de la Z1 V2. |
| ATK X1 original | Même coque que X1 V2 Ultra Max selon EloShapes (127 × 64 × 40 mm) : partage la géométrie ; capteur et poids non vérifiés. |
| ATK F1 V2 Ultimate / F1 Pro Max | Même géométrie que la F1 V3 selon EloShapes (118.2 × 62.4 × 38.8 mm) : géométrie partagée ; compatibilités non vérifiées. |
| ATK A9 SE / A9 Pro / A9 Ultra / A9 Plus (autres variantes) | Dimensions 125 × 64 × 40 mm selon EloShapes (une seule comparaison) ; poids et capteurs partiels. Non ajoutées individuellement. |
| ATK Dragonfly, Blazing Sky Phantom (store) | Non consultés en détail. Le modèle Phantom Ultimate est présent (une source). |
| Duckbill « 55 mm » | Aucune source trouvée annonçant 55 mm de largeur. |

## 4. Sources consultées

Consultées le 2026-10-10 (pages complètes ou extraits de recherche selon la source) :

- ATK Store : collection Z1, collection U2, collection X1, collection A9, collection Mice (listing), fiche Fierce X, fiche Dragonfly A9 Ultimate (`https://www.atk.store/collections/mice` — URL de redirection de `/fr-fr/collections/souris`), blog Duck Bill, blog Fierce X (taille de main), blog Z1.
- EloShapes (comparaisons) : Zero, Duckbill, Fierce X, Phantom Ultimate, GHOST Ultimate et GHOST Extreme, Y9 Ultimate, U2 V2 Ultimate, F1 V2 Ultimate / U2 V2 Mini, comparaison A9 (A9 / SE / Plus / Pro / Ultra), A9 Ultimate, A9 Air / A9 Ultimate, X1 V2 Ultra Max, X1.
- Tiers : Meckeys (Z1 Series), MaxGaming (Y9 Ultimate), FPSTools (Y9 Ultimate), MouseMetric (Fierce X), notice ATK U2 V2 Ultimate (manuals.plus).
- Non utilisé comme donnée : Reddit (anecdotique).

## 4. Ajouts du 2026-10-11 — produits encore vendus (atk.store)

Passe complète sur la collection officielle (23 produits, 22 en stock) le **2026-10-11** : les 8 souris encore vendues
absentes du catalogue ont été ajoutées. Méthode et analyse : `docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md`.
Les prix sont ceux du store **en dollars** (`price_eur` reste `null`, aucune conversion) ; `budget_tier` suit la bande
de prix du store (< 50 $ = Économique, 50–100 $ = Qualité-Prix, > 100 $ = Haut de Gamme) — règle nouvelle, à valider.

| Ajout | Dimensions L×l×H (mm) | Poids | Bosse (EloShapes → schéma) | Prix store | Évasement / flancs (EloShapes) | Statut dimensions | Sources |
|---|---|---|---|---|---|---|---|
| **VXE Dragonfly V3 / V3 Pro** (`vxe_v3`) | 116,6 × 62,2 × 38,2 | 49–54 g | Back-moderate → **Rear** | dès 14,98 $ | Front flare « Inward - moderate », flancs « Inward » | verified | ATK Store ; EloShapes (V3 / V3 Pro) |
| **VXE Dragonfly R1 / R1 Pro** (`vxe_r1`) | 120,6 × 64,0 × 37,8 | 51 g | Back-moderate → **Rear** | dès 14,98 $ | Front flare « Flat », flancs « Flat » | verified | EloShapes ; GamerGear ; ATK Store |
| **VXE MAD R / Major** (`vxe_mad_r`) | 120,1 × 63,1 × 38,1 | 36 g | Back-moderate → **Rear** | dès 44,98 $ | Front flare « Outward - slight », flancs « Flat » | verified | EloShapes ; MouseShape ; ATK Store |
| **VXE Dragonfly X3 / Pro / Turbo** (`vxe_x3`) | 127,0 × 64,0 × 40,0 | 51–54 g | *inconnue* | dès 29,98 $ | — | single_source | ATK Store |
| **ATK Blazing Sky U2 Mini** (`atk_u2_mini`) | 119,5 × 63,0 × 38,5 | 38 g | Back-minimal → **Rear** | 84,98 $ | Front flare « Outward - slight », flancs « Inward » | verified | EloShapes (fiche + annonce) ; ATK Store |
| **ATK Dragonfly A9 NB Ultra** (`atk_a9_nb`) | 125,0 × 63,5 × 40,0 | 56 g | Mid (coque A9) | 79,98 $ | — | verified | ATK Store ; Ryugear ; Standesk |
| **ATK Blazing Sky F1 V2** (`atk_f1_v2`) | 118,2 × 62,4 × 38,8 | 38–39 g | Mid (coque F1, `shell_id` = `atk_f1`) | dès 44,98 $ | — | verified | ATK Store ; Loadout |
| **ATK Blazing Sky U2** (`atk_u2`) | 123,7 × 64,6 × 39,1 | 49–55 g | **Rear** | dès 24,98 $ | — | verified | ATK Store ; EloShapes ; Meckeys |

**Mise à jour du 2026-10-12** : les compatibilités de prise de ces souris ont été complétées une par une
depuis les fiches officielles (statut `manufacturer_guide`, `ROBUSTESSE_2026-10-12.md` §11.1) — sauf l'**ATK
Blazing Sky F1 V2**, dont le fabricant ne publie aucune recommandation écrite : elle a hérité des compatibilités
de sa **coque jumelle** (`shell_id` = `atk_f1`, §11.8). Les mentions marketing génériques (« Claw / Palm ») ne
sont toujours **pas** converties en compatibilité (règle du §1). La hauteur des boutons reste `Inconnu` pour
25 souris sur 36 : elles restent classables avec un score partiel, mais ne peuvent pas dépasser une souris
complète.

**Couverture après ajouts** : 26 souris, longueurs 116,6 → 127,0 mm. La `vxe_v3` (116,6 mm) est la première souris
« Small » du catalogue : elle comble le manque de formes compactes pour les mains de moins de ~175 mm.

## 5. Ce qu'il reste à faire pour élargir le catalogue

1. Extraire les fiches produits complètes (statut de disponibilité, prix **EUR**) sur les 26 produits du catalogue
   (les prix du store sont en USD : à documenter auprès d'un revendeur européen, jamais par conversion).
2. Vérifier les compatibilités grip et hauteurs de boutons sur des mesures ou des tests documentés (aucune source actuelle ne le fait).
3. Trancher les conflits du §2 (A9 Plus, Duckbill, Y9, X1 capteur).
