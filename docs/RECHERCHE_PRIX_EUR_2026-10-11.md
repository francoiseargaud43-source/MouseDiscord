# Prix en euros et produits encore vendus — relevé du 2026-10-11

Objectif : répondre à la question « le prix doit être en euros », sans conversion et sans invention,
puis rassembler ce qui est nécessaire pour choisir **ensemble** les prochaines souris à ajouter.

## 1. Ce que j'ai vérifié : le store ATK n'affiche pas d'euros

| Contrôle | Résultat |
|---|---|
| `https://www.atk.store/fr-fr/collections/souris` | **redirige** vers `https://www.atk.store/collections/mice` (page anglaise) |
| Fiche F1 V3 (`/fr-fr/products/...`) | prix rendus en **USD** : `Sale price$64.98 USD Regular price$89.98 USD` |
| Données structurées de la fiche | `"priceCurrency":"USD"` (Z1 : `"price":"54.98","priceCurrency":"USD"`) |
| Page FR « articles » de la Z1, du Duckbill | mêmes prix en **USD** |

Conclusion : le sélecteur `fr-fr` ne change que la **langue**, pas la devise ; la boutique applique une
devise USD. Aucun prix EUR ne peut donc venir du store officiel. **Je n'ai converti aucun prix USD en euros.**

## 2. Où il y a de vrais prix en euros (deux sources retenues)

1. **Maxesport** (`maxesport.gg`) — revendeur français, colis expédiés **depuis la France**, prix **TTC en €**,
   indication « en stock / rupture ». C'est la source la plus proche de ce que paierait l'utilisateur en France.
2. **Boutique ATK sur Amazon.fr** — vendeur/expéditeur « **ATK Gaming Gears** » (boutique de la marque).
   Attention : les montants s'affichent deux fois — prix article et **total avec frais d'import**
   (ex. A9 : 35,99 € + 3,60 € d'import = 39,59 €). J'ai retenu le **prix article**, en le notant.

## 3. Relevé par souris de notre catalogue

| Notre id | Modèle | Prix EUR constaté | Où / état | Écrit dans la base ? |
|---|---|---|---|---|
| scyrox_v8 | Scyrox V8 / V8S | **74,90 €** | Maxesport, noir en stock (blanc en promo 59,90 €) | oui (confirme le cahier des charges) |
| atk_a9_plus | A9 Plus 2.0 | 44,90 € | Maxesport, noir en stock | non : le prix du cahier des charges (45,00 €) reste la référence ; l'observation est notée |
| atk_a9_air | A9 Air 8K | **89,90 €** | Maxesport, Shadow White en stock | oui |
| atk_ghost_ultimate | Ghost Ultimate 8K CF | **114,90 €** | Maxesport, argent | oui |
| vxe_x3 | VXE X3 / X3 Pro / X3 Turbo | **44,90 €** (X3) / 49,90 € (X3 Pro) | Maxesport, en stock | oui, « à partir de » |
| vxe_r1 | VXE R1 S / N / SE+ / Pro / Pro Max | **29,90 €** (R1 S) → 64,90 € (Pro Max) | Maxesport, plusieurs en stock | oui, « à partir de » |
| atk_f1_ultimate | F1 V3 Ultimate | 89,90 € (Ultimate+ 8K) / 134,90 € (Extreme+) | Maxesport, blanc en stock | non : modèle « Ultimate » du cahier vs « Ultimate+ » du commerce — à trancher |
| atk_x1_ultra_max | X1 V2 Ultra Max | 84,90 € (X1 V2 **Ultimate**, pas Ultra Max) | Maxesport | non : variante différente |
| vxe_v3 | VXE Dragonfly V3 / V3 Pro | 22,90 € (V3) / 26,90 € (V3 Pro) | Maxesport, **toutes en rupture** | non : rupture de stock |
| vxe_mad_r | VXE MAD R / MAD R Major | 59,90 € (MAD R 8K) | Maxesport, **en rupture** | non : rupture de stock |
| — | autres 16 souris | aucun prix EUR trouvé | — | non |

Aucun montant n'a été converti, extrapolé ou « arrondi » : quand la variante exacte n'existait pas,
je n'ai rien écrit (voir la colonne « Écrit dans la base ? »).

## 4. Effet sur le bot

Ces prix sourcés rendent les souris concernées **visibles dans les modes Économique, Qualité-Prix et Budget**,
qui exigent un prix (avant, elles ne sortaient qu'en « haut de gamme »/classement morphologique).
Le barème géométrique n'est pas touché : les scores sont inchangés (257 tests verts).

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

## 6. Sources consultées (2026-10-11)

- Store ATK : `/fr-fr/collections/souris` (redirection), fiche F1 V3, fiche Z1, fiche Duckbill, `products.json` de la collection « mice ».
- Maxesport : recherche « ATK », collections « ATK Gaming Gear » et « VXE », fiches A9 Plus 2.0, A9 Air, Ghost Ultimate CF,
  X1 Air+, X1 V2 Ultimate, F1 V3 Ultimate+/Extreme+, X3/X3 Pro, R1 (S/N/SE+/Pro/Pro Max), Dragonfly V3/V3 Pro, MAD R 8K, Scyrox V8.
- Amazon.fr (boutique ATK Gaming Gears) : VXE R1 SE+, Dragonfly A9, Dragonfly A9 Plus.
