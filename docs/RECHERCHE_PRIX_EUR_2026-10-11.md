# Prix en euros et produits encore vendus — relevé du 2026-10-11

## 0. Correction : les prix en euros existent bien

Tu avais raison. Le store ATK **affiche bien des prix en euros** — mais seulement quand le **marché
France** est actif. Mon premier contrôle ne l'était pas (le store servait le marché par défaut, en USD).
La preuve : la même page, avec le pays forcé sur la France.

| URL | Devise affichée |
|---|---|
| `https://www.atk.store/fr-fr/collections/souris` | USD (marché par défaut) |
| `https://www.atk.store/fr-fr/collections/souris?country=FR` | **EUR** : « Souris • 23 produits • En stock (21) » |

Exemples lus le 2026-10-11 en euros : VXE Dragonfly X3 « à partir de **27,95 €** », ATK Blazing Sky
Phantom **91,95 €**, F1 V3 « à partir de **59,95 €** », A9 Ultimate « à partir de **41,95 €** »,
VXE R1 « à partir de **13,95 €** », ZERO « à partir de **63,95 €** »…

**Aucune conversion n'a été faite** : ce sont les prix que la boutique affiche elle-même en euros
(TVA et prix barrés inclus dans la page).

## 1. Ce qui est écrit dans la base

24 souris sur 26 ont désormais un prix EUR **daté et sourcé** (source : la boutique officielle FR,
`?country=FR`, relevé du 2026-10-11). Les « à partir de » correspondent à la variante la moins chère
en stock ; le prix normal barré est conservé dans la note.

| Souris | Prix EUR officiel | Remarque |
|---|---|---|
| VXE Dragonfly X3 | dès 27,95 € | prix normal 31,95 € |
| ATK Blazing Sky Phantom | 91,95 € | prix normal 109,95 € |
| ATK A9 Ultimate | dès 41,95 € | prix normal 63,95 € |
| ATK Blazing Sky ZERO | dès 63,95 € | prix normal 81,95 € |
| ATK Blazing Sky F1 V2 | dès 41,95 € | prix normal 63,95 € |
| ATK Blazing Sky U2 V2 | 59,95 € | prix normal 72,95 € |
| VXE Dragonfly R1 | dès 13,95 € | prix normal 17,95 € |
| VXE Dragonfly V3 | dès 13,95 € | prix normal 17,95 € |
| ATK Blazing Sky GHOST | dès 68,95 € | Ultimate et Extreme, prix normal 100,95 € |
| ATK Blazing Sky Duckbill | 81,95 € | prix normal 118,95 € |
| ATK Blazing Sky Y9 | dès 41,95 € | prix normal 63,95 € |
| ATK Blazing Sky U2 Mini | 77,95 € | — |
| ATK Blazing Sky U2 | dès 22,95 € | prix normal 28,95 € |
| ATK Dragonfly A9 NB | 72,95 € | prix normal 122,95 € |
| ATK FIERCE X | 69,95 € | prix normal 81,95 € |
| ATK A9 Air | 89,90 € | Maxesport (pas de prix officiel distinct pour cette variante) — **changé le 2026-10-12** : 59,95 € à la boutique officielle, voir l'addendum en fin de document |
| Scyrox V8 / V8S | 74,90 € | Maxesport — confirmé en euros, non vendu sur le store ATK |

Les 6 souris de ton cahier des charges **gardent leur prix** : j'ai seulement consigné l'observation
officielle dans leurs notes (ex. F1 V3 « à partir de » 59,95 € contre 70 € chez toi).

Sans prix EUR distinct à ce jour : **A9 Mini** (vendue dans la famille A9 « à partir de » 18,95 €)
et **U2 V2 Mini** (le store ne liste qu'un « U2 Mini », 77,95 €, qui partage la coque).

**Suite du 2026-10-12 (16e passe)** : les deux cas sont réglés. L'**A9 Mini** (variante « Mini » de la
fiche A9 Ultimate, 59,95 €, prix normal 72,95 €) et l'**U2 V2 Mini** (variante « U2 V2 Mini / White »,
59,95 €, prix normal 72,95 €) ont un prix EUR officiel distinct, relevé sur la boutique ATK en France et
inscrit au catalogue avec sa source datée. L'ancienne valeur de 77,95 € de l'U2 V2 Mini venait du
produit « U2 Mini », qui n'est pas la V2 : elle a été corrigée.

## 2. Autres sources EUR (pour comparaison, non utilisées dans la base)

- **Maxesport** (revendeur FR, expédition depuis la France) : F1 V3 Ultimate+ 89,90 €,
  F1 V3 Extreme+ 134,90 €, X1 V2 Ultimate 84,90 €, A9 Air 8K 89,90 €, A9 Plus 2.0 44,90 €,
  X3 44,90 € / X3 Pro 49,90 €, R1 de 29,90 à 64,90 €, V3 22,90 €, MAD R 59,90 €, Scyrox V8 74,90 €.
- **Boutique ATK sur Amazon.fr** (« ATK Gaming Gears ») : R1 SE+ 33,99 €, Dragonfly A9 35,99 €,
  A9 Plus 45,99 € — prix **hors frais d'import** affichés séparément (≈ 3,60 €).

Ces deux sources servent de contrôle : elles encadrent les prix officiels sans les remplacer.

## 3. Effet sur le bot

Ces prix sourcés rendent les souris concernées **visibles dans les modes Économique, Qualité-Prix et
Budget personnalisé**, qui exigent un prix. Le barème géométrique n'est pas touché.

## 4. Couverture du catalogue vs produits encore vendus

Les 23 produits listés par la boutique sont tous représentés par une de nos 26 fiches (36 depuis le
2026-10-12), sauf trois
**familles historiques encore vendues** (F1 « Series » dès 36,95 €, X1 « Series » dès 18,95 €,
Z1 « Series » dès 50,95 €) : elles partagent les coques de modèles déjà présents (F1 V2/V3, X1 V2,
Z1 V2) mais ont leurs propres variantes économiques. À ajouter si tu veux une couverture exhaustive.

## 5. Candidats à ajouter (vendus aujourd'hui, absents du catalogue)

| Candidat | Prix EUR | Pourquoi il est intéressant | Ce qui manque pour l'ajouter |
|---|---|---|---|
| **ATK Dragonfly A9 2.0** | 29,90 € (Maxesport, en stock) | nouvelle génération A9, entrée de gamme | dimensions officielles + forme EloShapes |
| **ATK Blazing Sky X1 Air+ 8K** | 89,90 € (Maxesport, en stock) | variante légère de la famille X1 (grande coque) | dimensions officielles + forme EloShapes |
| **ATK Blazing Sky F1 V3 Extreme+** | 134,90 € (Maxesport) | même coque que la F1 V3 (déjà au catalogue) — doublon probable | à décider : doublon ou non ? |
| **VXE Dragonfly V3 / V3 Pro** | 22,90 / 26,90 € | déjà au catalogue (`vxe_v3`) | — |

La liste ci-dessus est volontairement courte : le catalogue couvre déjà 26 références, dont l'essentiel de
la gamme ATK/VXE vendue aujourd'hui. Ce qui manque le plus, ce ne sont pas des souris, ce sont des **données
de forme** : position de bosse, hauteur de boutons (14 souris en `Inconnu`) et **largeur de prise mesurée**
(0 souris renseignée). C'est là qu'EloShapes et les images serviront en priorité.

## 5 bis. Addendum du 2026-10-12 : le prix retenu est celui de la boutique officielle

Règle donnée par le propriétaire le 2026-10-12 : « toujours prendre le prix côté boutique
officielle ». Elle a été appliquée le jour même, relevés faits en euros sur le marché France
(`?country=FR`), sans aucune conversion de devise :

| Souris | Avant (relevé du 2026-10-11) | Après (boutique officielle, 2026-10-12) |
|---|---|---|
| ATK A9 Air | 89,90 € (revendeur Maxesport) | **59,95 €** (boutique ATK, variante « Air / Shadow White », prix normal 72,95 €) |
| VXE MAD R | aucun prix (rupture) | **40,95 €** (boutique ATK, série « à partir de » ; la rupture de la variante noire 1K est écrite dans la note) |
| ATK A9 Mini | aucun prix distinct | **59,95 €** (boutique ATK, variante « Mini », prix normal 72,95 €) — inscrit le 2026-10-12 |
| ATK U2 V2 Mini | 77,95 € (ancienne « U2 Mini ») | **59,95 €** (variante Mini de la fiche officielle) — inscrit le 2026-10-12 |

Les relevés de revendeurs (Maxesport) restent **en observation** dans les notes des fiches : ils ne sont
plus la valeur retenue quand la boutique officielle publie un prix. Restent à revérifier à la boutique
officielle, la règle étant maintenant connue : **Z1**, **Y9 Ultimate** et **GHOST Extreme**
(voir `docs/audit/ROBUSTESSE_2026-10-12.md` §9.5.4 et §10.3).

## 6. Sources consultées (2026-10-11)

- Store ATK : `/fr-fr/collections/souris` (redirection), fiche F1 V3, fiche Z1, fiche Duckbill, `products.json` de la collection « mice ».
- Maxesport : recherche « ATK », collections « ATK Gaming Gear » et « VXE », fiches A9 Plus 2.0, A9 Air, Ghost Ultimate CF,
  X1 Air+, X1 V2 Ultimate, F1 V3 Ultimate+/Extreme+, X3/X3 Pro, R1 (S/N/SE+/Pro/Pro Max), Dragonfly V3/V3 Pro, MAD R 8K, Scyrox V8.
- Amazon.fr (boutique ATK Gaming Gears) : VXE R1 SE+, Dragonfly A9, Dragonfly A9 Plus.
