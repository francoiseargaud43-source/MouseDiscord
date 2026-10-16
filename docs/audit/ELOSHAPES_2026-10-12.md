# EloShapes : ce qui est accessible, ce qui bloque (2026-10-12)

Demande du propriétaire : aller mesurer modèle par modèle **sur EloShapes**, qui affiche le contour
de chaque souris en vue de côté — et utiliser les souris « similaires » quand une forme est une copie
d'une marque connue (ATK Y9 ≈ Logitech, ATK X1 ≈ Razer Viper…).

## 1. Ce que le site expose réellement

| Élément | État | Détail |
|---|---|---|
| Nombre de souris | ✅ | « more than 1700 gaming mice » (page Compare) |
| Fiches texte (dimensions, capteur, poids, prix) | ✅ | lisible en HTML, déjà utilisée pour le catalogue |
| Vue de côté / dessous (contours) | ❌ | **dessinée côté navigateur** : le HTML ne contient ni SVG ni URL d'image de contour |
| Images produits | ⚠️ | bucket public Supabase (`/storage/v1/render/.../images/products/<slug>.png`) : **téléchargement binaire refusé** par l'outil (HTTP 500) |
| « Find similar mice » | ⚠️ | liste chargée côté navigateur, texte non lisible sans exécuter le JavaScript |

## 2. Ce qui bloque, précisément

1. **Les contours ne sont pas dans la page.** Le HTML servi ne contient que des publicités et la liste
   « Select mice to compare » : aucun chemin de fichier de contour. Les contours (vue de côté, vue du
   dessous) sont produits par le JavaScript du site.
2. **Le bucket d'images refuse les requêtes binaires** depuis cet environnement (`HTTP 500`), et les
   images passent par un rendu `render/image/...` paramétré côté serveur.
3. **Aucune API publique documentée** n'est trouvée pour les contours.

Conclusion honnête : **avec les outils disponibles ici, je ne peux pas récupérer automatiquement les
contours d'EloShapes.** Je ne peux donc pas mesurer « moi-même » sur cette base depuis cet
environnement — c'est un blocage technique, pas un manque de recherche.

## 3. Ce que l'essai a quand même apporté

- **Le sous-produit est utile pour le catalogue** : EloShapes est une base de formes **et** de
  spécifications, dont les données recoupent celles déjà relevées (dimensions ATK/Scyrox/Pulsar).
- **Le constat de copie de formes est confirmé** par la page Compare : elle propose côte à côte des
  souris de même famille de forme (ATK F1 V3 avec Razer Viper V4 Pro, Logitech G Pro X Superlight 2C,
  WLMOUSE Huan…). C'est bien ainsi que le propriétaire l'a décrit, et c'est ce qui rend l'idée
  d'**équivalence de coque** pertinente pour le moteur (voir §4).

## 4. Ce que j'ai déjà mis en place côté moteur (sans EloShapes)

1. **Deux places ≠ même coque** (2026-10-12) : le match idéal et l'alternative ne montrent jamais deux
   variantes de la même forme (ATK GHOST Ultimate / Extreme, X2 v3 Mini / X2 CrazyLight Mini…).
   Le regroupement se fait par `shell_id`, vérifié sur les cotes officielles.
2. **Score partiel** : une souris dont seule la hauteur des boutons manque est désormais proposée,
   notée sur les critères documentés, avec la mention en clair dans le bloc bas.

## 5. Comment débloquer la mesure de masse (le plus court chemin)

Le contour EloShapes est parfaitement exploitable **une fois capturé** : c'est une vue de côté
vectorielle, sans perspective — exactement ce que `tools/measure_button_height.py` sait mesurer
(le contrôle qualité vérifie d'ailleurs les cotes officielles avant d'accepter).

Deux options concrètes :

1. **Captures d'écran** : sur la page Compare d'EloShapes, vue de côté, faire une capture de la souris
   voulue (fond uni, souris entière), la déposer dans le dépôt (par exemple `image-search/`), et je la
   mesure : le script donne la classe (bas / hauts) ou refuse la vue si elle est en perspective.
2. **Passer par un navigateur local** : si le site est ouvert dans le navigateur du PC, l'enregistrement
   de l'image de contour (clic droit ▸ enregistrer l'image) produit un fichier mesurable immédiatement.

Dans les deux cas, **aucune valeur n'est inventée** : un fichier par souris, mesuré, avec la classe et
le verdict affichés — et un refus explicite si la vue ne permet pas de conclure.
