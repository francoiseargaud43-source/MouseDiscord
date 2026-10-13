# Vérification des liens sponsorisés — 2026-10-11

> **Instantané daté.** Ce rapport décrit l'état des liens **au 2026-10-11** (26 souris, 26 liens).
> Les ajouts postérieurs sont datés dans les addenda (§6 pour l'affiliation, et les résolutions
> « Tranché le 2026-10-12 » dans §3). État courant : **36 souris, 36 liens, 36 affiliés**.
> Depuis le 2026-10-12, les dix souris Pulsar sont entrées au catalogue et leurs liens affiliés
> (`?ref=AZE`) ont été ajoutés : le fichier compte aujourd'hui **36 liens pour 36 souris**. Le contrôle
> automatique à jour est `python tools/check_deployment.py` ; l'état courant est décrit dans
> `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` §2.5 et `docs/audit/PULSAR_CATALOGUE_2026-10-12.md`.

Tes 37 URL ont été vérifiées **une par une** sur les boutiques officielles (le jour même), puis
rangées dans `data/commercial_links.json` (clés = identifiants de `data/mouse_db.json`).
Les deux liens d'exemple `https://url.com/...` ont été supprimés, et le **lien A9 NB fourni en dernier**
(2026-10-11) a été ajouté : le bot affiche de vrais boutons « 🛒 Acheter … » pour **26 souris sur 26**
(§2). Le lien A9 NB a été vérifié sur la page FR : ATK Dragonfly A9 NB Ultra, **72,95 €** (122,95 € barré),
en stock, modèle « Ultra » par défaut — donc aucune variante figée dans l'URL.

## 1. Comment chaque lien a été vérifié

| Contrôle | Moyen utilisé |
| --- | --- |
| Le produit existe | page produit ATK rendue en euros (`?country=FR`) + `sitemap`/`search/suggest.json` |
| C'est la bonne souris | `search/suggest.json` (titre + handle + variante) et page produit (« All Models ») |
| La bonne variante est cochée | `https://www.atk.store/variants/<id>.json` → renvoie le libellé exact de la variante (ex. `Extreme / Black`) |
| Le prix est le bon | relevé EUR officiel du 2026-10-11 (`?country=FR`) et prix USD de la variante pour identifier le modèle |
| Le prix est celui de **la variante figée** | `https://www.atk.store/products/<handle>.js?country=FR` → `variants[]` donne, pour chaque variante, son identifiant, son libellé **et son prix**. C'est le contrôle ajouté le 2026-10-13 (§7) : un relevé « à partir de » ne dit rien du prix de la variante que le lien ouvre. |

Rappel : sans `?country=FR`, atk.store affiche des **dollars**. Tous les liens du fichier portent
donc `country=FR` (prix en euros) et ton code d'affiliation (`ref=aze` chez atk.store,
`bg_ref=Q0rHhhBRNv` chez scyrox.com).

## 2. Les 26 liens validés

Prix = relevé officiel du 2026-10-11, prix normal entre parenthèses. **Instantané historique** : ces
prix sont ceux du relevé du 2026-10-11. Le prix *de la variante figée par chaque lien* a été
recontrôlé le 2026-10-13 ; c'est ce contrôle qui fait foi aujourd'hui (§7).

| id | Souris (base) | Ce que le lien ouvre | Variante figée | Prix EUR |
| --- | --- | --- | --- | --- |
| scyrox_v8 | Scyrox V8 | Scyrox V8 | — (coloris) | 69,99 $ |
| scyrox_v6 | Scyrox V6 | Scyrox V6 | — (coloris) | 69,99 $ |
| atk_f1_ultimate | ATK F1 V3 Ultimate | F1 V3 (Blazing Sky) | **Ultimate+ / Black** | 59,95 € (81,95) |
| atk_x1_ultra_max | ATK X1 V2 Ultra Max | X1 V2 | **Ultra Max 2.0 / Black** | dès 41,95 € (63,95) |
| atk_z1_ultra | ATK Z1 V2 Ultra | Z1 V2 | défaut (Ultimate) | dès 59,95 € (72,95) |
| atk_a9_plus | ATK A9 Plus 2.0 | A9 Series | **A9 Plus / White** | dès 18,95 € (22,95) |
| atk_phantom_ultimate | ATK Phantom Ultimate | Phantom | — (coloris) | 91,95 € (109,95) |
| atk_ghost_ultimate | ATK GHOST Ultimate | GHOST carbone | **Ultimate / Black** | dès 68,95 € (100,95) |
| atk_ghost_extreme | ATK GHOST Extreme | GHOST carbone | **Extreme / Black** | dès 68,95 € (100,95) |
| atk_y9_ultimate | ATK Y9 Ultimate | Y9 Series | **Ultimate / White** (épuisé ce jour) | dès 41,95 € (63,95) |
| atk_fierce_x | ATK Fierce X | FIERCE X | — (coloris) | 69,95 € (81,95) |
| atk_u2_v2_ultimate | ATK U2 V2 Ultimate | U2 V2 Superlight | **U2 V2 Ultimate / White** | 59,95 € (72,95) |
| atk_u2_v2_mini | ATK U2 V2 Mini | U2 V2 Superlight | **U2 V2 Mini / White** | 59,95 € (72,95) |
| atk_zero | ATK ZERO | ZERO Ultralight | défaut (ZERO) | dès 63,95 € (81,95) |
| atk_duckbill | ATK Duckbill | Duckbill | — (coloris) | 81,95 € (118,95) |
| atk_a9_ultimate | ATK A9 Ultimate | A9 Ultimate | **Ultimate / Black** | dès 41,95 € (63,95) |
| atk_a9_air | ATK A9 Air | A9 Ultimate (même page) | **Air / Black** | dès 41,95 € (63,95) |
| atk_a9_mini | ATK A9 Mini | A9 Ultimate (même page) | **Mini / Black** | 59,95 € (72,95) |
| vxe_v3 | VXE Dragonfly V3 | V3 Series | défaut (V3) | dès 13,95 € (17,95) |
| vxe_r1 | VXE Dragonfly R1 | R1 Series | défaut (R1) | dès 13,95 € (17,95) |
| vxe_mad_r | VXE MAD R | MAD R Series | défaut (1K) | dès 41,95 € |
| vxe_x3 | VXE Dragonfly X3 | X3 Series | défaut (X3) | dès 27,95 € (31,95) |
| atk_u2_mini | ATK Blazing Sky U2 Mini | U2 Mini Superlight | — (coloris) | 77,95 € |
| atk_f1_v2 | ATK Blazing Sky F1 V2 | F1 V2 Series | défaut (V2) | dès 41,95 € (63,95) |
| atk_u2 | ATK Blazing Sky U2 | U2 Series | défaut (U2) | dès 22,95 € (28,95) |
| atk_a9_nb | ATK Dragonfly A9 NB Ultra | A9 NB | défaut (Ultra) — aucune variante figée | 72,95 € (122,95) |

## 3. Ce qui doit être corrigé (écarts relevés)

1. **F1 V3** : la gamme ne comporte pas de modèle « Ultimate » (uniquement **Ultimate+** / **Extreme+**
   et l'édition Leviatan). Ton id `atk_f1_ultimate` correspond donc à l'**Ultimate+** ; la base le
   porte à 70,00 € alors que le store FR l'affiche à 59,95 € → prix à trancher.
   **Tranché le 2026-10-12 (18ᵉ passe)** : la fiche officielle, modèle « **Ultimate+** » sélectionné,
   affiche **59,95 €** en euros (`?country=FR`) ; la base porte ce prix, la source est datée. À noter :
   la variante était **en précommande** au moment du relevé (rupture temporaire), c'est écrit dans la
   note de la fiche.
2. **X1 V2** : le modèle s'appelle **« Ultra Max 2.0 »** sur le store. Variante figée dessus ✓.
   Base 75,00 € vs 41,95 € au store → prix à trancher.
   **Tranché le 2026-10-12 (18ᵉ passe)** : les données de variante de la boutique officielle donnent
   **40,95 €** (prix normal 63,95 €) pour « Ultra Max 2.0 / Black », la variante figée du lien — c'est
   le prix de la base désormais, source datée à l'appui.
3. **Z1 V2** : la gamme Z1 V2 ne propose que **Ultimate / Ultimate+**. « Ultra » est un modèle de la
   **Z1 (V1)**. Ton id porte les cotes de la Z1 V2 (122,5 × 66,8 × 42,4 mm) → lien calé sur la Z1 V2.
   Base 75,00 € vs 59,95 € au store → prix à trancher.
   **Tranché le 2026-10-12 (18ᵉ passe)** : règle du propriétaire (boutique officielle) appliquée — la
   variante « Z1 V2 **Ultimate** » est à **59,95 €** sur la boutique ATK (`?country=FR`, relevé daté) ;
   la base porte ce prix, la source officielle est inscrite dans la fiche.
4. **Y9 Ultimate** : la variante Ultimate est à 64,98 $ (~59,95 €), le 41,95 € du store correspond au
   Y9 d'entrée de gamme → le prix de l'id est probablement celui du mauvais modèle.
   **Tranché le 2026-10-12 (18ᵉ passe)** : la variante « Y9 **Ultimate** » est à **59,95 €** (boutique
   ATK, `?country=FR`, relevé daté) ; c'est désormais le prix de l'id, l'ancien 41,95 € venait bien du
   modèle d'entrée de gamme.
5. **GHOST** : ton lien `?variant=47320425627866` pointe en réalité sur **Extreme / Black** (94,98 $),
   pas sur l'Ultimate+. Il est donc attribué à `atk_ghost_extreme` (et le lien Ultimate a reçu sa
   propre variante vérifiée). Or la base met **68,95 € aux deux** (prix du modèle Ultimate) → le prix
   de l'Extreme reste à trancher.
   **Tranché le 2026-10-12 (18ᵉ passe)** : la variante **Extreme** est à **86,95 €** (boutique ATK,
   `?country=FR`, variante `47320425627866`, relevé daté) et devient le prix de `atk_ghost_extreme` ;
   `atk_ghost_ultimate` conserve son prix du 2026-10-11 tant que la variante Ultimate n'a pas été
   relevée à son tour (dette ouverte).
6. **U2 V2 Mini** : la variante Mini s'affiche à **59,95 €** sur la page FR, alors que la base porte
   77,95 € (source = l'ancienne « U2 Mini ») → prix à corriger.
   **Réglé le 2026-10-12** : corrigé à 59,95 € au catalogue, source ATK datée à l'appui.
7. **A9 Air** : variante Air / Black à 64,98 $ ; la base porte 89,90 € (relevé Maxesport « A9 Air 8K »)
   → deux marchés différents, à trancher.
   **Tranché le 2026-10-12** : la règle donnée par le propriétaire — « toujours prendre le prix côté
   boutique officielle » — s'applique, et la boutique ATK (pays France) affiche la variante
   « Air / Shadow White » à **59,95 €** (prix normal 72,95 €). La base porte désormais ce prix, la
   source officielle est datée, et le relevé Maxesport reste en observation dans la note
   (voir `docs/audit/ROBUSTESSE_2026-10-12.md` §10.3).
8. **A9 Mini** : **aucun prix en base** ; la page FR affiche 59,95 € (72,95 € barré) pour Mini / Black.
   **Réglé le 2026-10-12** : prix inscrit au catalogue (59,95 €, variante « Mini », source ATK datée),
   avec la bosse (« Center » → Mid) et les dimensions passées en « vérifié » : la souris entre dans le
   tableau des recommandations.
9. **MAD R** : **aucun prix en base** ; de retour en stock chez ATK FR, « à partir de 41,95 € ».
   **Tranché le 2026-10-12** : le prix de la boutique officielle est retenu (**40,95 €**, « à partir
   de ») et la rupture de la variante noire à dongle 1K est écrite noir sur blanc dans la note de la
   fiche. La même fiche publie la prise du fabricant (« Perfect Fit for Claw and Palm Grips ») : la
   souris devient classable en Palm et en Claw (fingertip non publié, donc « à vérifier »).
   Voir `docs/audit/ROBUSTESSE_2026-10-12.md` §10.3 et §10.4.
10. **Duckbill** : aucun produit « Barbell » n'existe chez ATK : le bon handle est
    `atk-blazing-sky-duckbill-wireless-mouse` (81,95 €).
11. **A9 Plus** : la variante A9 Plus / White est en **précommande** au moment du relevé (le lien
    reste bon, le store expédie à réapprovisionnement).
12. **A9 Series** : ton lien arrivait **sans `ref=`** ; je l'ai écrit avec `ref=aze` comme les 32
    autres — dis-moi si cette page doit rester non affiliée.

## 4. Ce qui manque

| Manque | Détail | État |
| --- | --- | --- |
| ~~**A9 NB** (`atk_a9_nb`)~~ | ATK Dragonfly A9 NB, 72,95 € | **Résolu** : lien fourni par le propriétaire et ajouté au fichier (26/26) |
| **Scyrox V6S / V8S** | tu as fourni 4 liens scyrox, mais seuls V8 et V6 existent en base (V6S/V8S = 74,99 $, Kailh Optical, publiés en 2026-09) | **Accord donné** : les deux modèles sont ajoutés à la base (dimensions, poids, prix, sources), les 2 liens servent alors d'entrée d'achat |

## 5. Règles suivies

- **Aucun lien inventé** : les grandes surfaces et boutiques tierces n'ont pas été utilisées ; seuls
  atk.store et scyrox.com (les liens que tu as fournis).
- **Aucun lien d'exemple conservé** : `data/commercial_links.json` ne contient plus de `url.com`.
- Les clés commençant par `_` du fichier sont des commentaires : `load_commercial_links()` et
  `tools/check_deployment.py` les ignorent (un test dédié couvre ce cas).
- Test adapté : `tests/test_data.py::test_commercial_links_are_official_and_verified` vérifie que
  chaque lien est une URL atk.store/scyrox.com, qu'aucun lien d'exemple ne subsiste, que `country=FR`
  est présent sur toutes les pages atk.store (prix en euros) et que l'A9 NB — dernier lien fourni —
  est bien présent.

## 6. Addendum du 2026-10-12 : affiliation des dix liens Pulsar

Les dix Pulsar (X2 v3 Mini, X2H v3 Mini, X2A v3, X2 CrazyLight Mini et Medium, X2H CrazyLight Mini,
Xlite CrazyLight Medium, Xlite v4 Mini, Medium et Large) ont reçu le lien de leur fiche officielle
`eu.pulsar.gg` le 2026-10-12 (prix en euros, jamais de conversion). Seul manquait le paramètre
d'affiliation : **le propriétaire l'a fourni le 2026-10-12**, il est ajouté tel quel (`?ref=AZE`).

- `data/commercial_links.json` : les dix URL Pulsar se terminent par `?ref=AZE` ; la clé `_affiliation`
  documente désormais les trois boutiques (atk.store `?ref=aze`, scyrox.com `?bg_ref=…`, Pulsar `?ref=AZE`).
- Test verrouillé : `tests/test_data.py::test_commercial_links_are_official_and_verified` exige le
  paramètre sur chaque lien `pulsar_*` (comme `country=FR` l'est pour atk.store).
- État complet, ligne par ligne : `docs/audit/LIENS_AFFILIES_2026-10-12.md` — **36 souris, 36 liens,
  36 affiliés** ; plus aucun lien à compléter.

## 7. Addendum du 2026-10-13 (37e passe) : le prix affiché est celui de la page ouverte par le lien

Le contrôle du 2026-10-11 avait vérifié le **libellé** de la variante ouverte par chaque lien
(`variants/<id>.json`), pas son **prix** : le prix venait d'un relevé « **dès** X € », c'est-à-dire du
modèle le moins cher de la page — pas forcément celui que le lien ouvre. Le **2026-10-13**, les **36
liens** ont été repassés un par un sur la page du marchand, avec l'outil qui donne les prix en euros et
le détail des variantes :

- **atk.store** : `products/<handle>.js?country=FR` → `variants[]` (libellé exact, prix en centimes,
  disponibilité) ;
- **eu.pulsar.gg** : `search/suggest.json?…&country=FR` (prix TTC en EUR) et `products/<handle>.js` ;
- **scyrox.com** : pas de prix en euros sur la boutique (voir plus bas).

**Résultat : six prix étaient faux** (la boutique avait relevé plusieurs tarifs d'un euro entre le 12 et
le 13), **trois liens tombaient sur une variante épuisée**, et un écart de prix reste une question posée
au propriétaire.

### 7.1 Les six prix corrigés (relevés du 2026-10-13)

| Souris | Prix annoncé | Prix réel de la page | Ce qui s'était passé |
| --- | --- | --- | --- |
| **ATK A9 Ultimate** | 41,95 € | **59,95 €** | le lien ouvre l'édition « Ultimate » ; 41,95 € était le prix d'une **autre édition** de la même page (« Ultra Max 2.0 ») |
| **ATK X1 V2 Ultra Max** | 40,95 € | **41,95 €** | même variante (`47058382782682`), prix relevé d'un euro depuis le 12 |
| **ATK F1 V2** | 40,95 € | **41,95 €** | variante « Ultra Max 2.0 / Black » (`47006581096666`), +1 € (prix normal 63,95 €) |
| **VXE MAD R** | 40,95 € | **41,95 €** | série « à partir de », +1 € (produit toujours en rupture) |
| **ATK Dragonfly A9 NB** | 72,95 € | **73,95 €** | prix du produit, +1 € (prix normal 123,95 €) |
| **ATK Blazing Sky Duckbill** | 81,95 € | **82,95 €** | modèle « Ultra » unique, +1 € (prix normal 118,95 €) |

Chaque correction est écrite dans la `price_note` de la souris (ancien prix, nouveau prix, prix normal,
date) et **tracée par une source datée du 2026-10-13** dans `data/mouse_db.json`.

### 7.2 Les onze liens qui figent une variante

| id | Variante figée | Libellé réel au 2026-10-13 | Prix | Verdict |
| --- | --- | --- | --- | --- |
| `atk_a9_ultimate` | `46878654005466` | A9 **Ultimate** / Black | **59,95 €** (annoncé 41,95 €) | ❌ **prix corrigé** |
| `atk_x1_ultra_max` | `47058382782682` | X1 V2 **Ultra Max 2.0** / Black | **41,95 €** (catalogue 40,95 €) | ⚠️ **prix corrigé** (dérive d'un jour) |
| `atk_a9_plus` | `46320046047450` | A9 **Plus** / White | 27,95 € (normal 36,95 €) | ⚠️ écart avec les 45,00 € du cahier → **prix conservé**, question posée |
| `atk_a9_air` | `47193565364442` | A9 **Air** / Black | 59,95 € | ✅ cohérent |
| `atk_a9_mini` | `47852235718874` | A9 **Mini** / Black | 59,95 € | ✅ cohérent |
| `atk_ghost_extreme` | `47320425627866` | GHOST **Extreme** / Black | 86,95 € | ✅ cohérent, en stock |
| `atk_f1_ultimate` | `48175399370970` | F1 V3 **Ultimate+** / Black | 59,95 € | ✅ cohérent (**désormais en stock**) |
| `atk_u2_v2_mini` | `47204034150618` | U2 V2 **Mini** / White | 59,95 € | ✅ cohérent, en stock |
| `atk_ghost_ultimate` | `47320425595098` | GHOST **Ultimate** / Silver | 68,95 € | ✅ recâblé (Black épuisé) |
| `atk_y9_ultimate` | `47178929897690` | Y9 **Ultimate** / Pink | 59,95 € | ✅ recâblé (White épuisé) |
| `atk_u2_v2_ultimate` | `47201864974554` | U2 V2 **Ultimate** / Lake Green | 59,95 € | ✅ recâblé (White épuisé) |

**Les trois liens recâblés** gardent le **même prix** : seul le coloris change, pour qu'un clic
n'atterrisse jamais sur une page où l'on ne peut pas acheter :
`atk_ghost_ultimate` → `47320425595098` (Silver) · `atk_u2_v2_ultimate` → `47201864974554` (Lake Green) ·
`atk_y9_ultimate` → `47178929897690` (Pink). `docs/audit/LIENS_AFFILIES_2026-10-12.md` porte les trois
nouvelles URL.

### 7.3 Les treize liens ATK sans variante figée

Pour ceux-là, le lien ouvre la page : l'annonce doit donc valoir le prix le moins cher affiché
(« à partir de »). Tous ont été relus le 2026-10-13.

| Souris | Annoncé | Page du 2026-10-13 | Verdict |
| --- | --- | --- | --- |
| ATK Blazing Sky U2 | 22,95 € | 22,95 € (normal 28,95 €) | ✅ |
| ATK Blazing Sky U2 Mini | 77,95 € | 77,95 € | ✅ (blanc en rupture, rose en stock) |
| ATK Blazing Sky ZERO | 63,95 € | 63,95 € | ✅ |
| ATK Blazing Sky Z1 V2 (« Ultimate ») | 59,95 € | 59,95 € (normal 73,95 €) | ✅ |
| ATK Blazing Sky Phantom | 91,95 € | 91,95 € (normal 109,95 €) | ✅ |
| ATK FIERCE X | 69,95 € | 69,95 € | ✅ (produit en rupture de stock) |
| VXE Dragonfly R1 | 13,95 € | 13,95 € | ✅ |
| VXE Dragonfly V3 | 13,95 € | 13,95 € | ✅ |
| VXE Dragonfly X3 | 27,95 € | 27,95 € | ✅ |
| ATK Dragonfly A9 NB | 72,95 € | **73,95 €** | ❌ **prix corrigé** |
| ATK Blazing Sky Duckbill | 81,95 € | **82,95 €** | ❌ **prix corrigé** |
| ATK Blazing Sky F1 V2 | 40,95 € | **41,95 €** | ❌ **prix corrigé** |
| VXE MAD R | 40,95 € | **41,95 €** | ❌ **prix corrigé** |

### 7.4 Les dix liens Pulsar et les deux liens Scyrox

- **Pulsar (eu.pulsar.gg)** : les **dix prix sont identiques** à ceux du relevé du 2026-10-12 —
  X2 v3 Mini **119,99 €**, X2H v3 Mini **119,99 €**, X2A v3 Medium **119,99 €**, X2 CrazyLight Mini et
  Medium **149,99 €**, X2H CrazyLight Mini **149,99 €**, Xlite CrazyLight Medium **149,90 €**,
  Xlite v4 Mini, Medium et Large **119,99 €**. Toutes ces fiches sont en stock **sauf** les deux Xlite
  v4 **Medium et Large**, dont les deux coloris sont épuisés : le lien reste le bon (aucun autre coloris
  n'existe), il n'y a rien à recâbler. C'est **noté**, pas corrigé.
- **Scyrox (scyrox.com)** : la boutique n'affiche **aucun prix en euros** (et aucune conversion n'est
  faite — règle du 2026-10-11). Les 74,90 € des V6 et V8 viennent du **cahier des charges** du
  propriétaire (V6 : `owner_spec_unverified`, affiché « prix non vérifié ») et le prix de la V8 est
  corroboré par un revendeur français (Maxesport, 74,90 €, relevé du 2026-10-11). **Rien n'a changé** le
  2026-10-13 ; la note de la V6 dit désormais explicitement pourquoi son prix n'est pas vérifiable sur
  la boutique officielle.

### 7.5 Le point ouvert : le prix de l'A9 Plus

La variante liée est l'« A9 Plus / White » à **27,95 €** (36,95 € normal). Le catalogue porte **45,00 €**
(cahier des charges) et un revendeur affiche 44,90 €. Rien ne prouve que « A9 Plus » (27,95 € à la
boutique) et « A9 Plus 2.0 » (45,00 €) soient le même produit : **le prix n'a pas été changé** ce jour-là,
une source d'observation datée a été ajoutée, la question est posée au propriétaire (point ouvert 16 de
`docs/audit/AUDIT.md`).

> **Suite le 2026-10-13 (47e passe)** : la question est **tranchée** — la série A9 de la boutique ne
> propose **aucun** modèle « 2.0 » (« A9 SE », « A9 », « A9 Plus », « A9 Pro », « A9 Pro Max », « A9
> Ultra »). Le prix publié est donc devenu **27,95 €**, celui de la variante que le bouton ouvre, et le
> nom publié « **A9 Plus** » a suivi celui de la boutique (voir §8.2).

### 7.6 Effet mesuré et verrous

- **Effet sur les résultats** (`tools/db_effect.py --avant` — catalogue d'avant la passe, grille
  complète de **27 170 profils**) : **6 058 profils (22,30 %)** changent d'une place ; **0 place gagnée,
  91 perdues** (profils à 45 € ou moins qui voyaient l'A9 Ultimate) ; 5 411 listes sans deux fois la même
  coque, 647 avec le repli documenté. Détail : §25 de `docs/audit/ROBUSTESSE_2026-10-12.md`.
- **Trois tests verrouillent la règle** dans `tests/test_data.py` :
  `test_le_prix_de_l_a9_ultimate_est_celui_de_sa_variante` (le prix d'une fiche est celui de la variante
  que son lien ouvre), `test_chaque_lien_a_variante_est_trace_par_une_source` (toute variante figée doit
  être datée par une source) et `test_chaque_prix_de_souris_est_date_par_une_source` (**aucun prix sans
  source datée** : c'est le contrôle qui manquait et qui a laissé passer les six écarts).

## 8. Inventaire du 2026-10-13 (après-midi) : les 36 liens relus, un par un

La 37e passe avait relu les 36 liens **le matin** du 2026-10-13. Le propriétaire a demandé une
vérification de **cohérence** entre les liens et les modèles du catalogue, puis la **mise à jour des
prix**. Les 36 liens ont donc été relus une seconde fois, le même jour, avec la méthode la moins
coûteuse et la plus précise pour chaque boutique :

- **atk.store** : `products/<handle>.json?country=FR` (liste complète des variantes, prix en euros) et,
  pour un lien qui fige une variante, `variants/<id>.json?country=FR` (une seule variante, quelques
  centaines d'octets : libellé exact, prix, devise) ;
- **eu.pulsar.gg** : `products/<handle>.json?country=FR` — l'étiquette `Size/...` de chaque fiche dit
  la taille, et le titre porte le modèle (« Xlite v4 **Medium** Gaming Mouse ») ;
- **scyrox.com** : `products/<handle>.json?country=FR`, `search/suggest.json` et `cart.js?country=FR`
  (la devise est **USD** — voir §8.3).

Le tableau ci-dessous est **lu par un test** (`tests/test_liens_achat.py`) : il est comparé, ligne à
ligne, à `data/commercial_links.json` (handle et variante figée) et à `data/mouse_db.json` (prix
publié). Modifier un lien ou un prix sans mettre à jour ce tableau fait **échouer la suite**.

### 8.1 Les 36 liens (handle, variante figée, prix de la boutique, prix publié)

| id | handle | variante figée | libellé de la variante (ou du produit) | prix boutique | prix publié | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `atk_a9_ultimate` | `atk-dragonfly-a9-ultimate-lightweight-wireless-mouse` | `46878654005466` | Ultimate / Black | 59,95 € | 59,95 € | ✅ |
| `atk_a9_air` | `atk-dragonfly-a9-ultimate-lightweight-wireless-mouse` | `47193565364442` | Air / Black | 59,95 € | 59,95 € | ✅ |
| `atk_a9_mini` | `atk-dragonfly-a9-ultimate-lightweight-wireless-mouse` | `47852235718874` | Mini / Black | 59,95 € | 59,95 € | ✅ |
| `atk_a9_plus` | `atk-dragonfly-a9-series-lightweight-wireless-mouse` | `46320046047450` | A9 Plus / White | 27,95 € | 27,95 € | 🔧 prix corrigé (45,00 € → 27,95 €) |
| `atk_a9_nb` | `atk-dragonfly-a9-nb-lightweight-wireless-mouse` | — | Ultra (4 coloris) | 72,95 € | 72,95 € | 🔧 prix corrigé (73,95 € → 72,95 €) |
| `atk_x1_ultra_max` | `atk-blazing-sky-x1-v2-series-esports-wireless-mouse` | `47058382782682` | Ultra Max 2.0 / Black | 41,95 € | 41,95 € | ✅ |
| `atk_z1_ultra` | `atk-blazing-sky-z1-v2-gaming-wireless-mouse` | — | Ultimate (le moins cher ; l'édition Ultimate+ est à 65,95 €) | 59,95 € | 59,95 € | ✅ |
| `atk_phantom_ultimate` | `atk-blazing-sky-phantom-hollow-carbon-fiber-composite-wireless-gaming-mouse` | — | Ultimate (modèle unique de la page, 4 coloris) | 91,95 € | 91,95 € | ✅ |
| `atk_ghost_ultimate` | `atk-blazing-sky-ghost-hollow-carbon-fiber-wireless-gaming-mouse` | `47320425595098` | Ultimate / Silver | 68,95 € | 68,95 € | ✅ |
| `atk_ghost_extreme` | `atk-blazing-sky-ghost-hollow-carbon-fiber-wireless-gaming-mouse` | `47320425627866` | Extreme / Black | 86,95 € | 86,95 € | ✅ |
| `atk_y9_ultimate` | `atk-dragonfly-y9-series-lightweight-ergonomic-wireless-mouse` | `47178929897690` | Ultimate / Pink | 59,95 € | 59,95 € | ✅ |
| `atk_f1_ultimate` | `atk-blazing-sky-f1-v3-series-esports-wireless-mouse` | `48175399370970` | Ultimate+ / Black | 59,95 € | 59,95 € | ✅ |
| `atk_f1_v2` | `atk-blazing-sky-f1-v2-series-esports-wireless-mouse` | `47006581096666` | Ultra Max 2.0 / Black | 41,95 € | 41,95 € | 🔧 variante figée (le lien ouvrait la page des trois éditions) |
| `atk_u2_v2_ultimate` | `atk-blazing-sky-u2-v2-superlight-wireless-gaming-mouse` | `47201864974554` | U2 V2 Ultimate / Lake Green | 59,95 € | 59,95 € | ✅ |
| `atk_u2_v2_mini` | `atk-blazing-sky-u2-v2-superlight-wireless-gaming-mouse` | `47204034150618` | U2 V2 Mini / White | 59,95 € | 59,95 € | ✅ |
| `atk_u2` | `atk-blazing-sky-u2-series-wireless-mouse` | — | U2 (le moins cher de la série) | 22,95 € | 22,95 € | ✅ |
| `atk_u2_mini` | `atk-blazing-sky-u2-mini-superlight-wireless-gaming-mouse` | — | U2 Mini (modèle unique) | 77,95 € | 77,95 € | ✅ |
| `atk_zero` | `atk-blazing-sky-zero-ultralight-wireless-gaming-mouse` | — | ZERO (le moins cher) | 63,95 € | 63,95 € | ✅ |
| `atk_duckbill` | `atk-blazing-sky-duckbill-wireless-mouse` | — | Duckbill (modèle unique) | 82,95 € | 82,95 € | ✅ |
| `atk_fierce_x` | `atk-fierce-x-lightweight-wireless-gaming-mouse` | — | FIERCE X (3 coloris) | 69,95 € | 69,95 € | ✅ (produit épuisé) |
| `vxe_v3` | `vxe-dragonfly-v3-series-lightweight-wireless-mouse` | — | Dragonfly V3 (le moins cher) | 13,95 € | 13,95 € | ✅ |
| `vxe_r1` | `vxe-dragonfly-r1-series-wireless-mouse` | — | Dragonfly R1 (le moins cher) | 13,95 € | 13,95 € | ✅ |
| `vxe_mad_r` | `vxe-mad-r-series-wireless-mouse` | — | MAD R (le moins cher) | 41,95 € | 41,95 € | ✅ (produit épuisé) |
| `vxe_x3` | `vxe-dragonfly-x3-series-lightweight-wireless-mouse` | — | Dragonfly X3 (le moins cher) | 27,95 € | 27,95 € | ✅ |
| `pulsar_x2_v3_mini` | `x2-v3-mini-gaming-mouse` | — | X2 v3 Mini (taille `Size/Mini`) | 119,99 € | 119,99 € | ✅ |
| `pulsar_x2h_v3_mini` | `x2h-v3-mini-gaming-mouse` | — | X2H v3 Mini (taille `Size/Mini`) | 119,99 € | 119,99 € | ✅ |
| `pulsar_x2a_v3_medium` | `x2a-v3-gaming-mouse` | — | X2A v3 Medium (taille `Size/Medium`) | 119,99 € | 119,99 € | ✅ |
| `pulsar_x2_crazylight_medium` | `x2-crazylight-medium-gaming-mouse` | — | X2 CrazyLight Medium | 149,99 € | 149,99 € | ✅ |
| `pulsar_x2_crazylight_mini` | `x2-crazylight-gaming-mouse` | — | X2 CrazyLight Mini | 149,99 € | 149,99 € | ✅ |
| `pulsar_x2h_crazylight_mini` | `x2h-crazylight-gaming-mouse` | — | X2H CrazyLight Mini | 149,99 € | 149,99 € | ✅ |
| `pulsar_xlite_crazylight_medium` | `xlite-crazylight-medium-gaming-mouse` | — | Xlite CrazyLight Medium | 149,90 € | 149,90 € | ✅ |
| `pulsar_xlite_v4_mini` | `xlite-v4-mini-gaming-mouse` | — | Xlite v4 Mini (taille `Size/Mini`) | 119,99 € | 119,99 € | ✅ |
| `pulsar_xlite_v4_medium` | `xlite-v4-gaming-mouse` | — | Xlite v4 Medium (taille `Size/Medium`) | 119,99 € | 119,99 € | ✅ |
| `pulsar_xlite_v4_large` | `xlite-v4-large-gaming-mouse` | — | Xlite v4 Large (taille `Size/Large`) | 119,99 € | 119,99 € | ✅ |
| `scyrox_v8` | `scyrox-v8` | — | Scyrox V8 (6 variantes) | 69,99 USD | 74,90 € | ⚠️ monnaie ≠ EUR (voir §8.3) |
| `scyrox_v6` | `scyrox-v6` | — | Scyrox V6 | 69,99 USD | 74,90 € | ⚠️ monnaie ≠ EUR (voir §8.3) |

### 8.2 Ce que la relecture a corrigé

1. **Deux prix** : l'**A9 Plus** (45,00 € au catalogue) est vendu **27,95 €** par la boutique
   officielle, dans la variante même que son bouton ouvre ; l'**A9 NB** (73,95 € le matin) est
   redescendu à **72,95 €** dans la journée. Les deux notes de prix gardent l'historique.
2. **Quatre noms de modèles alignés sur la boutique** — c'est la réponse à « les liens
   correspondent-ils aux modèles ? ». Trois noms ne se retrouvaient **pas** sur la page ouverte :
   - `atk_a9_plus` : « A9 Plus 2.0 » → **« A9 Plus »** (la boutique ne propose aucun modèle « 2.0 » :
     les modèles de la série A9 sont « A9 SE », « A9 », « A9 Plus », « A9 Pro », « A9 Pro Max »,
     « A9 Ultra ») ;
   - `atk_z1_ultra` : « Z1 V2 Ultra » → **« Z1 V2 Ultimate »** (les modèles de la page sont
     « Ultimate » et « Ultimate+ » : « Ultra » n'existe pas, et le prix publié est celui de
     « Ultimate ») ;
   - `atk_f1_ultimate` : « F1 V3 Ultimate » → **« F1 V3 Ultimate+ »** (la page ne propose que
     « Ultimate+ » et « Extreme+ ») ;
   - `atk_x1_ultra_max` : « X1 V2 Ultra Max » → **« X1 V2 Ultra Max 2.0 »** (l'édition vendue par le
     bouton porte « 2.0 »).
3. **Deux notes de prix ne décrivaient pas ce que le bouton ouvre** — l'inverse du premier point :
   c'est le texte qui était faux, pas le lien.
   - `atk_a9_air` : la note datait la variante « Air / Shadow White ». Le bouton, lui, fige
     « **Air / Black** » (59,95 €, prix normal 72,95 €, relevé le 2026-10-13). « Shadow White » est le
     coloris d'un **revendeur** (Maxesport), pas celui de la boutique officielle ; la note le dit
     désormais, et la source du 2026-10-13 nomme la variante réelle.
   - `atk_f1_v2` : la note affirmait que le bouton ouvre « Ultra Max 2.0 / Black » alors que le lien ne
     figeait **aucune** variante — la fiche vend trois éditions (41,95 € / 54,95 € / 77,95 €). Le lien a
     été **figé** sur la variante vendue (41,95 €) le 2026-10-13 : le prix publié et l'édition achetée sont
     désormais la même.
4. **Une source qui contredisait sa propre donnée** : la source du 2026-10-13 de l'**A9 Plus** disait
   encore « prix du catalogue NON adopté (45,00 € du cahier des charges) » une fois le prix adopté.
   Cinq libellés de source disaient aussi « relevé du 2026-10-13 … inchangé depuis le relevé du
   2026-10-13 » — un relevé comparé à lui-même ne prouve rien ; la comparaison portait sur la veille.
5. **Rien d'autre** : les 32 autres prix sont **identiques** au relevé du matin, les 12 variantes
   figées ouvrent toutes l'édition annoncée, et les 10 fiches Pulsar sont exactement celles du
   catalogue (mêmes tailles, mêmes prix).

### 8.3 Ce que ce tableau ne prouve pas

- **La disponibilité** : elle n'est pas dans ce tableau (le format `products/<handle>.json` ne la
  porte pas). Elle est notée là où elle compte — A9 Plus en stock, U2 V2 Ultimate en Lake Green,
  produit MAD R épuisé, Xlite v4 Medium et Large épuisées (voir §7.4).
- **Le montant en euros des Scyrox** : `cart.js?country=FR` répond `"currency":"USD"`, les variantes
  portent `price_currency: "USD"` et la fiche V8 affiche **69,99 USD**. Aucune conversion n'est faite
  (règle du 2026-10-11) : les 74,90 € publiés viennent du cahier des charges et d'un revendeur FR, et
  la V6 reste marquée « prix non vérifié ».
- **La stabilité des promotions** : les promotions « Halloween Specials » (5 → 31 octobre 2026)
  expliquent la plupart des écarts de prix d'un jour à l'autre. C'est pourquoi chaque relevé porte sa
  date, et pourquoi le contrôle se refait avec `tools/check_links.py` : pour chaque souris, il ouvre la
  fiche de la boutique et compare **la variante figée par le bouton** (ou, à défaut, le modèle le moins
  cher de la page) au prix publié par `data/mouse_db.json`. Il sort en code 0 si tout concorde, 1 s'il
  trouve un écart, **2 s'il n'a rien pu ouvrir** (un réseau qui bloque les boutiques n'est pas un
  catalogue faux). Le tableau §8.1 ci-dessus est, lui, relu par `tests/test_liens_achat.py` : modifier un
  prix ou un lien sans mettre à jour ce tableau fait échouer la suite.
- **Douze figées, vingt-quatre non** : douze liens figent une variante (`variant=<id>`). Les vingt-quatre
  autres ouvrent une page qui ne vend qu'un seul modèle (les dix fiches Pulsar, une par taille, et les deux
  Scyrox) ou, pour **douze** fiches ATK/VXE, une page qui vend plusieurs éditions ou plusieurs coloris. Dans
  ce dernier cas le prix publié est celui que la page affiche aujourd'hui (le moins cher de la série) et la
  note de prix dit lequel ; figer une variante n'y apporterait rien tant que la page ne vend pas d'édition
  plus chère sous le nom publié.
