# Vérification des liens sponsorisés — 2026-10-11

> **Instantané daté.** Ce rapport décrit l'état des liens **au 2026-10-11** (26 souris, 26 liens).
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

Rappel : sans `?country=FR`, atk.store affiche des **dollars**. Tous les liens du fichier portent
donc `country=FR` (prix en euros) et ton code d'affiliation (`ref=aze` chez atk.store,
`bg_ref=Q0rHhhBRNv` chez scyrox.com).

## 2. Les 26 liens validés

Prix = relevé officiel du 2026-10-11, prix normal entre parenthèses.

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
2. **X1 V2** : le modèle s'appelle **« Ultra Max 2.0 »** sur le store. Variante figée dessus ✓.
   Base 75,00 € vs 41,95 € au store → prix à trancher.
3. **Z1 V2** : la gamme Z1 V2 ne propose que **Ultimate / Ultimate+**. « Ultra » est un modèle de la
   **Z1 (V1)**. Ton id porte les cotes de la Z1 V2 (122,5 × 66,8 × 42,4 mm) → lien calé sur la Z1 V2.
   Base 75,00 € vs 59,95 € au store → prix à trancher.
4. **Y9 Ultimate** : la variante Ultimate est à 64,98 $ (~59,95 €), le 41,95 € du store correspond au
   Y9 d'entrée de gamme → le prix de l'id est probablement celui du mauvais modèle.
5. **GHOST** : ton lien `?variant=47320425627866` pointe en réalité sur **Extreme / Black** (94,98 $),
   pas sur l'Ultimate+. Il est donc attribué à `atk_ghost_extreme` (et le lien Ultimate a reçu sa
   propre variante vérifiée). Or la base met **68,95 € aux deux** (prix du modèle Ultimate) → le prix
   de l'Extreme reste à trancher.
6. **U2 V2 Mini** : la variante Mini s'affiche à **59,95 €** sur la page FR, alors que la base porte
   77,95 € (source = l'ancienne « U2 Mini ») → prix à corriger.
7. **A9 Air** : variante Air / Black à 64,98 $ ; la base porte 89,90 € (relevé Maxesport « A9 Air 8K »)
   → deux marchés différents, à trancher.
8. **A9 Mini** : **aucun prix en base** ; la page FR affiche 59,95 € (72,95 € barré) pour Mini / Black.
9. **MAD R** : **aucun prix en base** ; de retour en stock chez ATK FR, « à partir de 41,95 € ».
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
